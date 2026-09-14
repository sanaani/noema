"""Finite associativity rewriting; strategy transfer has an exact symbolic oracle."""

from collections import deque
from functools import lru_cache


@lru_cache(None)
def trees(leaves, offset=0):
    if leaves < 1:
        raise ValueError("at least one leaf required")
    if leaves == 1:
        return (offset,)
    return tuple(
        (left, right)
        for split in range(1, leaves)
        for left in trees(split, offset)
        for right in trees(leaves - split, offset + split)
    )


def at(tree, path):
    for side in path:
        if not isinstance(tree, tuple):
            raise ValueError("path leaves the tree")
        tree = tree[side]
    return tree


def replace_at(tree, path, value):
    if not path:
        return value
    if not isinstance(tree, tuple):
        raise ValueError("path leaves the tree")
    side = path[0]
    return (
        (replace_at(tree[0], path[1:], value), tree[1])
        if side == 0
        else (tree[0], replace_at(tree[1], path[1:], value))
    )


def apply_step(tree, step):
    path, direction = step
    node = at(tree, path)
    if not isinstance(node, tuple):
        raise ValueError("rotation needs an internal node")
    left, right = node
    if direction == 1 and isinstance(left, tuple):
        target = (left[0], (left[1], right))
    elif direction == -1 and isinstance(right, tuple):
        target = ((left, right[0]), right[1])
    else:
        raise ValueError("rotation pattern not applicable")
    return replace_at(tree, path, target)


def neighbors(tree):
    def visit(node, path=()):
        if not isinstance(node, tuple):
            return
        for direction in (1, -1):
            try:
                target = apply_step(tree, (path, direction))
                yield target, (path, direction)
            except ValueError:
                pass
        for side in (0, 1):
            yield from visit(node[side], (*path, side))

    return list(visit(tree))


def replay(tree, program):
    for step in program:
        tree = apply_step(tree, step)
    return tree


def population(leaves, *, distance=5, minimum_paths=8):
    vertices = trees(leaves)
    edges = {tree: neighbors(tree) for tree in vertices}
    records = []
    for destination in vertices:
        distances = {destination: 0}
        frontier = deque([destination])
        while frontier:
            node = frontier.popleft()
            for adjacent, _ in edges[node]:
                if adjacent not in distances:
                    distances[adjacent] = distances[node] + 1
                    frontier.append(adjacent)

        @lru_cache(None)
        def paths(node, destination=destination, distances=distances):
            if node == destination:
                return ((),)
            return tuple(
                (step, *suffix)
                for adjacent, step in edges[node]
                if distances[adjacent] == distances[node] - 1
                for suffix in paths(adjacent)
            )

        for source in vertices:
            if distances[source] != distance:
                continue
            programs = frozenset(paths(source))
            if len(programs) >= minimum_paths:
                records.append(
                    {
                        "source": source,
                        "target": destination,
                        "programs": programs,
                        "leaves": leaves,
                        "distance": distance,
                    }
                )
    return records


def transfer(a, b):
    shared = len(a["programs"] & b["programs"])
    return shared / len(a["programs"]), shared / len(b["programs"])


def term(tree, operator="f", names=None):
    if isinstance(tree, int):
        return names[tree] if names else f"x{tree}"
    if isinstance(tree, str):
        return tree
    return f"({operator} {term(tree[0], operator, names)} {term(tree[1], operator, names)})"


def step_proof(tree, step, operator="f", names=None):
    path, direction = step
    node = at(tree, path)
    a, b, c = (
        (node[0][0], node[0][1], node[1]) if direction == 1 else (node[0], node[1][0], node[1][1])
    )
    arguments = " ".join(term(t, operator, names) for t in (a, b, c))
    proof = f"h{operator} {arguments}"
    if direction == -1:
        proof = f"Eq.symm ({proof})"
    if path:
        template = term(replace_at(tree, path, "hole"), operator, names)
        proof = f"congrArg (fun hole => {template}) ({proof})"
    return proof


def context(leaves):
    return (
        "α : Type\nf g : α → α → α\n"
        "hf : ∀ a b c : α, f (f a b) c = f a (f b c)\n"
        "hg : ∀ a b c : α, g (g a b) c = g a (g b c)\n"
        f"{' '.join(f'x{i}' for i in range(leaves))} : α"
    )


def state(tree, target, leaves, operator="f", names=None):
    return context(leaves) + f"\n⊢ {term(tree, operator, names)} = {term(target, operator, names)}"


def lean_source(record, program, operator="f", names=None):
    leaves = record["leaves"]
    binders = (
        "(α : Type) (f g : α → α → α) "
        "(hf : ∀ a b c : α, f (f a b) c = f a (f b c)) "
        "(hg : ∀ a b c : α, g (g a b) c = g a (g b c)) "
        f"({' '.join(f'x{i}' for i in range(leaves))} : α)"
    )
    current = record["source"]
    script = ""
    for step in program:
        script += f"  refine Eq.trans ({step_proof(current, step, operator, names)}) ?_\n"
        current = apply_step(current, step)
    script += "  rfl\n"
    return (
        "import Lean\nset_option linter.unusedVariables false\n"
        f"theorem specimen {binders} : {term(record['source'], operator, names)} = "
        f"{term(record['target'], operator, names)} := by\n{script}#print axioms specimen\n"
    )
