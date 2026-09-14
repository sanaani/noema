"""Preregistered, premise-matched strategy-transfer headroom experiment."""

import argparse
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import beta, binom

from noema.associahedron import (
    apply_step,
    context,
    lean_source,
    population,
    state,
    transfer,
)
from noema.corpus import digest, validate_response, verify_batch
from noema.encoders import MiniLMEncoder, SyntaxEncoder
from noema.report import provenance
from noema.reprover import ReProverEncoder
from noema.statistics import wilson_interval

SEEDS = {"development": 914202601, "confirmation": 914202602}


def tuple_tree(value):
    return tuple(map(tuple_tree, value)) if isinstance(value, list) else value


def unpack_record(record):
    return {
        **record,
        "source": tuple_tree(record["source"]),
        "target": tuple_tree(record["target"]),
        "programs": frozenset(tuple_tree(record["programs"])),
    }


def assignments(split, count):
    rng = np.random.default_rng(SEEDS[split])
    records = population(7 if split == "development" else 8)
    index = defaultdict(set)
    for i, record in enumerate(records):
        for program in record["programs"]:
            index[program].add(i)
    used, blocks = set(), []
    strata = np.array([0, 1] * (count // 2))
    rng.shuffle(strata)
    for i in rng.permutation(len(records)).tolist():
        if i in used:
            continue
        a = records[i]
        candidates = set().union(*(index[p] for p in a["programs"])) - used - {i}
        positive = sorted(j for j in candidates if min(transfer(a, records[j])) >= 0.75)
        if not positive:
            continue
        j = int(rng.choice(positive))
        negative = [
            k
            for k in range(len(records))
            if k not in used | {i, j} and not a["programs"] & records[k]["programs"]
        ]
        k = int(rng.choice(negative))
        operator = str(rng.choice(["f", "g"]))
        overlap = int(strata[len(blocks)])
        other = operator if overlap else ("g" if operator == "f" else "f")
        members = []
        for identifier, op in zip((i, j, k), (operator, other, other), strict=True):
            record = records[identifier]
            programs = sorted(record["programs"])
            sampled = [programs[v] for v in rng.choice(len(programs), 4, replace=False)]
            names = [f"x{v}" for v in rng.permutation(record["leaves"]).tolist()]
            members.append(
                {
                    **record,
                    "programs": programs,
                    "sampled_programs": sampled,
                    "operator": op,
                    "names": names,
                    "population_index": identifier,
                }
            )
        blocks.append(
            {
                "members": members,
                "used_premise_overlap": overlap,
                "tie_positive": bool(rng.integers(2)),
                "positive_transfer": transfer(a, records[j]),
                "negative_transfer": transfer(a, records[k]),
            }
        )
        used.update((i, j, k))
        if len(blocks) == count:
            break
    if len(blocks) != count:
        raise ValueError(f"only {len(blocks)} disjoint eligible triplets")
    return {"split": split, "seed": SEEDS[split], "population_size": len(records), "blocks": blocks}


def member_texts(member):
    m = unpack_record(member)
    args = (m["target"], m["leaves"], m["operator"], m["names"])
    statement = state(m["source"], *args)
    points = []
    for program in member["sampled_programs"]:
        current = m["source"]
        for step_number, step in enumerate(tuple_tree(program), 1):
            current = apply_step(current, step)
            if step_number in (1, 3):
                points.append(state(current, *args))
        if current != m["target"]:
            raise ValueError("sampled strategy does not reach target")
    return statement, points


def parse_goal(goal):
    """Parse Lean's pretty-printed binary-operation equation, retaining its tree."""
    tokens = re.findall(r"x\d+|[fg()=]", goal)
    if "".join(tokens) != re.sub(r"\s+", "", goal):
        raise ValueError(f"unsupported equation: {goal}")
    position = 0

    def expression():
        nonlocal position
        token = tokens[position]
        position += 1
        if token == "(":
            result = expression()
            if tokens[position] != ")":
                raise ValueError("unbalanced expression")
            position += 1
            return result
        if token in ("f", "g"):
            return (token, expression(), expression())
        if token.startswith("x"):
            return token
        raise ValueError("invalid expression")

    left = expression()
    if tokens[position] != "=":
        raise ValueError("expected equation")
    position += 1
    right = expression()
    if position != len(tokens):
        raise ValueError("trailing equation tokens")
    return left, right


def audit_fixture(plan, root, output, *, all_blocks=False):
    audit = []
    for bi, block in enumerate(plan["blocks"] if all_blocks else plan["blocks"][:2]):
        for mi, member in enumerate(block["members"]):
            m = unpack_record(member)
            sources = [
                lean_source(m, tuple_tree(p), m["operator"], m["names"])
                for p in member["sampled_programs"]
            ]
            responses = verify_batch(sources, root=root)
            for pi, (source, response) in enumerate(zip(sources, responses, strict=True)):
                tactics = validate_response(response)
                steps = [t for t in tactics if t["tactic"].startswith("refine Eq.trans")]
                if len(steps) != 5:
                    raise ValueError("unexpected Lean state trajectory")
                current = m["source"]
                for ti, tactic in enumerate(steps):
                    raw_context, goal = tactic["goals"].split("⊢")
                    raw_context = re.sub(r"^case .*\n", "", raw_context)
                    raw_context = re.sub(r"∀\s*\(([^()]*)\)", r"∀ \1", raw_context)
                    if re.sub(r"\s+", "", raw_context) != re.sub(r"\s+", "", context(m["leaves"])):
                        raise ValueError(f"unexpected Lean context: {raw_context}")
                    expected = state(current, m["target"], m["leaves"], m["operator"], m["names"])
                    if parse_goal(goal) != parse_goal(expected.split("⊢")[1]):
                        raise ValueError("Lean and symbolic intermediate states disagree")
                    current = apply_step(current, tuple_tree(member["sampled_programs"][pi][ti]))
                audit.append(
                    {"block": bi, "member": mi, "proof": pi, "source": source, "response": response}
                )
    with gzip.open(output / "lean-audit.json.gz", "wt") as stream:
        json.dump(audit, stream)
    return {"verified_proofs": len(audit), "matched_intermediate_states": len(audit) * 5}


def clades(tree):
    found = set()

    def walk(node):
        if isinstance(node, int):
            return [node]
        leaves = walk(node[0]) + walk(node[1])
        found.add((min(leaves), max(leaves)))
        return leaves

    whole = walk(tuple_tree(tree))
    found.discard((min(whole), max(whole)))
    return found


def jaccard_distance(a, b):
    return 1 - len(a & b) / len(a | b) if a | b else 0.0


def structural_distance(a, b):
    return sum(jaccard_distance(clades(a[k]), clades(b[k])) for k in ("source", "target")) / 2


def token_distance(a, b):
    counts = [Counter(re.findall(r"\w+|[^\w\s]", t)) for t in (a, b)]
    return 1 - sum((counts[0] & counts[1]).values()) / sum((counts[0] | counts[1]).values())


def score_distances(distances, plan):
    outcomes, fractional, ties = [], [], []
    for (positive, negative), block in zip(distances, plan["blocks"], strict=True):
        tie = abs(positive - negative) <= 1e-10
        correct = block["tie_positive"] if tie else positive < negative
        outcomes.append(int(correct))
        fractional.append(0.5 if tie else float(correct))
        ties.append(tie)
    n, k = len(outcomes), sum(outcomes)
    return {
        "accuracy": k / n,
        "tie_adjusted_accuracy": float(np.mean(fractional)),
        "ties": sum(ties),
        "outcomes": outcomes,
        "distances": np.asarray(distances).tolist(),
        "upper_95": float(beta.ppf(0.95, k + 1, n - k)) if k < n else 1.0,
        "strata": {
            str(v): float(
                np.mean(
                    [
                        o
                        for o, b in zip(outcomes, plan["blocks"], strict=True)
                        if b["used_premise_overlap"] == v
                    ]
                )
            )
            for v in (0, 1)
        },
    }


def run_headroom(plan_path, root, output):
    output.mkdir(parents=True, exist_ok=False)
    plan = json.loads(plan_path.read_text())
    report = {
        "provenance": provenance(),
        "plan_sha256": digest(plan_path.read_text()),
        "source_sha256": digest(Path(__file__).read_text()),
        "fixture": audit_fixture(plan, root, output),
        "baselines": {},
        "encoders": {},
    }
    texts = [[member_texts(m) for m in b["members"]] for b in plan["blocks"]]
    baseline = report["baselines"]
    for key in ("token_bag", "used_premise", "statement_structure"):
        distances = []
        for block, rendered in zip(plan["blocks"], texts, strict=True):
            members = block["members"]
            if key == "statement_structure":
                row = [structural_distance(members[0], c) for c in members[1:]]
            elif key == "used_premise":
                row = [1 - block["used_premise_overlap"]] * 2
            else:
                row = [token_distance(rendered[0][0], c[0]) for c in rendered[1:]]
            distances.append(row)
        baseline[key] = score_distances(distances, plan)
    unique = sorted({t for row in texts for statement, points in row for t in [statement, *points]})
    for name, make in (
        ("syntax", SyntaxEncoder),
        ("minilm", lambda: MiniLMEncoder(root / ".tools/minilm")),
        ("reprover", lambda: ReProverEncoder(root / ".tools/reprover")),
    ):
        encoder = make()
        chunks = []
        for start in range(0, len(unique), 20):
            chunks.append(encoder.encode(unique[start : start + 20]))
            print(f"{name} {min(start + 20, len(unique))}/{len(unique)}", flush=True)
        vectors = np.concatenate(chunks)
        np.savez_compressed(
            output / f"{name}-embeddings.npz", texts=np.array(unique), vectors=vectors
        )
        lookup = dict(zip(unique, vectors, strict=True))
        for mode in ("statement", "centroid"):
            distances = []
            for row in texts:
                rows = [
                    lookup[s] if mode == "statement" else np.mean([lookup[t] for t in ps], axis=0)
                    for s, ps in row
                ]
                distances.append([float(np.linalg.norm(rows[0] - c)) for c in rows[1:]])
            baseline[f"{name}_{mode}"] = score_distances(distances, plan)
        report["encoders"][name] = getattr(encoder, "manifest", {"dimension": 256})
        (output / "checkpoint.json").write_text(json.dumps(report))
        del encoder
    report["unique_states_and_statements"] = len(unique)
    report["headroom_pass"] = all(b["upper_95"] < 0.90 for b in baseline.values())
    report["failing_baselines"] = [name for name, b in baseline.items() if b["upper_95"] >= 0.90]
    (output / "report.json").write_text(json.dumps(report, indent=2))
    return report


def paired_test(cloud, baseline):
    delta = np.asarray(cloud, dtype=int) - np.asarray(baseline, dtype=int)
    wins, losses = np.sum(delta > 0, axis=-1), np.sum(delta < 0, axis=-1)
    return np.mean(delta, axis=-1), binom.sf(wins - 1, wins + losses, 0.5)


def power(output):
    output.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(914202603)
    rows = []
    for n in (64, 128, 256):
        for alternative in (False, True):
            cloud_p = 0.80 if alternative else 0.65
            cloud = rng.random((10000, n)) < cloud_p
            conditional = (
                np.where(cloud, 0.55 / 0.80, 0.10 / 0.20)
                if alternative
                else np.where(cloud, 0.475 / 0.65, 0.175 / 0.35)
            )
            passed = np.ones(10000, dtype=bool)
            records = []
            for _ in range(9):
                baseline = rng.random((10000, n)) < conditional
                gain, p = paired_test(cloud, baseline)
                passed &= (gain >= 0.10 - 1e-12) & (p <= 0.05)
                records.append(np.stack([gain, p], axis=1))
            np.savez_compressed(
                output / f"n{n}-{'alternative' if alternative else 'null'}.npz",
                comparisons=np.stack(records),
                passed=passed,
            )
            k = int(passed.sum())
            rows.append(
                {
                    "n": n,
                    "alternative": alternative,
                    "successes": k,
                    "trials": 10000,
                    "rate": k / 10000,
                    "wilson_95": wilson_interval(k, 10000),
                }
            )
    qualified = [
        n
        for n in (64, 128, 256)
        if all(
            r["wilson_95"][0] > 0.80 if r["alternative"] else r["wilson_95"][1] < 0.10
            for r in rows
            if r["n"] == n
        )
    ]
    report = {
        "seed": 914202603,
        "rows": rows,
        "qualified_n": min(qualified) if qualified else None,
        "provenance": provenance(),
    }
    (output / "report.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("design", "headroom", "power"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--split", choices=tuple(SEEDS), default="development")
    parser.add_argument("--count", type=int, default=32)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.command == "design":
        plan = assignments(args.split, args.count)
        with args.output.open("x") as stream:
            json.dump(plan, stream, indent=2)
    elif args.command == "power":
        power(args.output)
    else:
        run_headroom(args.plan, root, args.output)


if __name__ == "__main__":
    main()
