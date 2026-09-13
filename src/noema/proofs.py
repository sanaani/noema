"""Two bounded proof searches in a constructive propositional fragment.

Search trees are audit data, not geometric features or encoder input.
"""

import hashlib
import itertools
import json
import random
from dataclasses import asdict, dataclass

Formula = int | tuple["Formula", "Formula"]


def formula_text(formula: Formula) -> str:
    if isinstance(formula, int):
        return f"p{formula}"
    return f"({formula_text(formula[0])} ∧ {formula_text(formula[1])})"


@dataclass(frozen=True)
class Rule:
    name: str
    antecedent: Formula
    consequent: int


@dataclass(frozen=True)
class Theorem:
    theorem_id: str
    atoms: int
    facts: tuple[int, ...]
    rules: tuple[Rule, ...]
    goal: Formula

    def binders(self) -> str:
        atoms = " ".join(f"p{i}" for i in range(self.atoms))
        facts = " ".join(f"(h{i} : p{atom})" for i, atom in enumerate(self.facts))
        rules = " ".join(
            f"({r.name} : {formula_text(r.antecedent)} → p{r.consequent})" for r in self.rules
        )
        return f"({atoms} : Prop) {facts} {rules}"


@dataclass(frozen=True)
class Proof:
    rule: str
    children: tuple["Proof", ...] = ()

    def identity(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()

    def term(self) -> str:
        if self.rule == "And.intro":
            return f"⟨{self.children[0].term()}, {self.children[1].term()}⟩"
        return f"({self.rule} {self.children[0].term()})" if self.children else self.rule


def theorem_population(count: int, *, seed: int = 91827) -> list[Theorem]:
    """Distinct acyclic Horn premise networks, all with the same vocabulary size."""
    if count < 1:
        raise ValueError("count must be positive")
    rng = random.Random(seed)
    population = []
    for index in range(count):
        rules = []
        for destination in range(2, 8):
            # Three distinct routes per consequent, including at least one conjunction.
            candidates: list[Formula] = list(range(destination)) + list(
                itertools.combinations(range(destination), 2)
            )
            selected = rng.sample(candidates, min(3, len(candidates)))
            for antecedent in selected:
                rules.append(Rule(f"h{len(rules) + 2}", antecedent, destination))
        population.append(Theorem(f"horn_{index:03d}", 8, (0, 1), tuple(rules), ((4, 5), (6, 7))))
    return population


def backward_search(theorem: Theorem, *, seed: int, attempts: int = 128) -> list[Proof]:
    """Goal-directed recursive search; each seed samples routes through subgoals."""
    rng = random.Random(seed)

    def solve(goal: Formula) -> Proof:
        if isinstance(goal, tuple):
            return Proof("And.intro", tuple(solve(g) for g in goal))
        options = [(f"h{i}", None) for i, atom in enumerate(theorem.facts) if atom == goal]
        options += [(r.name, r.antecedent) for r in theorem.rules if r.consequent == goal]
        if not options:
            raise ValueError("unreachable goal")
        name, antecedent = rng.choice(options)
        return Proof(name) if antecedent is None else Proof(name, (solve(antecedent),))

    unique = {}
    for _ in range(attempts):
        proof = solve(theorem.goal)
        unique.setdefault(proof.identity(), proof)
    return list(unique.values())


def forward_search(theorem: Theorem, *, seed: int, width: int = 24) -> list[Proof]:
    """Forward saturation over a layered fact frontier, retaining bounded alternatives."""
    rng = random.Random(seed)
    known: dict[int, dict[str, Proof]] = {}
    for i, atom in enumerate(theorem.facts):
        proof = Proof(f"h{i}")
        known.setdefault(atom, {})[proof.identity()] = proof

    def facts(formula: Formula, snapshot: dict[int, dict[str, Proof]]) -> list[Proof]:
        if isinstance(formula, int):
            return list(snapshot.get(formula, {}).values())
        left, right = (facts(f, snapshot) for f in formula)
        products = list(itertools.product(left, right))
        rng.shuffle(products)
        return [Proof("And.intro", pair) for pair in products[:width]]

    for _ in range(theorem.atoms):
        snapshot = {atom: dict(proofs) for atom, proofs in known.items()}
        candidates = []
        for rule in theorem.rules:
            candidates.extend(
                (rule.consequent, Proof(rule.name, (argument,)))
                for argument in facts(rule.antecedent, snapshot)
            )
        rng.shuffle(candidates)
        changed = False
        for atom, proof in candidates:
            alternatives = known.setdefault(atom, {})
            if len(alternatives) < width and proof.identity() not in alternatives:
                alternatives[proof.identity()] = proof
                changed = True
        if not changed:
            break
    return facts(theorem.goal, known)


def backward_script(proof: Proof, indent: int = 2) -> str:
    prefix = " " * indent
    if not proof.children:
        return prefix + f"exact {proof.rule}\n"
    if proof.rule != "And.intro":
        return prefix + f"apply {proof.rule}\n" + backward_script(proof.children[0], indent)
    lines = prefix + "constructor\n"
    for child in proof.children:
        rendered = backward_script(child, indent + 2).splitlines()
        lines += prefix + "· " + rendered[0].lstrip() + "\n"
        lines += "".join(line + "\n" for line in rendered[1:])
    return lines


def forward_script(proof: Proof, theorem: Theorem) -> str:
    """Topological proof replay: derive intermediate facts, then assemble the goal."""
    statements = []
    names: dict[str, str] = {}
    rule_types = {r.name: r.consequent for r in theorem.rules}

    def visit(node: Proof) -> str:
        identity = node.identity()
        if identity in names:
            return names[identity]
        if not node.children:
            return node.rule
        args = [visit(child) for child in node.children]
        if node.rule == "And.intro":
            return f"⟨{args[0]}, {args[1]}⟩"
        name = f"f{len(statements)}"
        statements.append(f"  have {name} : p{rule_types[node.rule]} := {node.rule} {args[0]}\n")
        names[identity] = name
        return name

    result = visit(proof)
    return "".join(statements) + f"  exact {result}\n"


def lean_source(theorem: Theorem, proof: Proof, generator: str) -> str:
    if generator not in ("backward", "forward"):
        raise ValueError("unknown generator")
    script = backward_script(proof) if generator == "backward" else forward_script(proof, theorem)
    return (
        "import Lean\nset_option maxHeartbeats 200000\n"
        "set_option linter.unusedVariables false\n"
        f"theorem specimen {theorem.binders()} : {formula_text(theorem.goal)} := by\n"
        f"{script}\n#print axioms specimen\n"
    )
