"""Give term-mode proofs an object, using their initial goal.

A tactic replay captures nothing for `theorem foo : P := le_antisymm ..` - there
are no tactics to observe - so roughly a quarter of the corpus ends up with no
states and therefore no object at all. Four of the six benchmark families lose at
least one member that way, which would make the betweenness test untestable for
them.

The initial goal still exists: it is the statement, in context form, and it is
exactly the kind of text the ReProver retriever encodes. `InitialGoals.lean`
prints it from the environment (forall-telescoped, so binders appear as
hypothesis lines the way an observed state shows them), which means the proof
source is never altered - no `sorry` rewriting.

Every state added here is marked `synthetic: true` and `kind: "initial_goal"`.
It is one point, not an observed trajectory, so an object built from it has zero
extent. Any geometry that depends on extent (diameter, affine dimension, hull
separation) must exclude or specially handle these.
"""
import argparse
import glob
import gzip
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", type=Path, required=True, help="replay checkpoint directory")
    ap.add_argument("--goals", type=Path, required=True, help="initial-goals.jsonl")
    ap.add_argument("--out", type=Path, required=True, help="output .jsonl.gz")
    args = ap.parse_args()

    goals = {}
    for line in args.goals.open():
        r = json.loads(line)
        if "goal" in r:
            goals[r["name"]] = r["goal"]

    observed = synthetic = missing = 0
    records = []
    for path in sorted(glob.glob(str(args.replay / "*.json"))):
        d = json.loads(Path(path).read_text())
        if "theorem_id" not in d:
            continue
        name = d["theorem_id"].split(":", 1)[1]
        states = d.get("states") or []
        if states:
            observed += 1
            kind = "observed"
        elif name in goals:
            synthetic += 1
            kind = "synthetic"
            states = [{
                "text": goals[name],
                "kind": "initial_goal",
                "synthetic": True,
                "tactic": "",
                "tactic_index": -1,
                "provenance": "InitialGoals.lean: declaration type, forall-telescoped",
            }]
        else:
            missing += 1
            continue
        records.append({
            "theorem_id": d["theorem_id"],
            "proof_id": d.get("proof_id"),
            "status": d.get("status"),
            "verified": d.get("verified"),
            "object_kind": kind,
            "states": states,
        })

    with gzip.open(args.out, "wt") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    total_states = sum(len(r["states"]) for r in records)
    print(f"records {len(records)} | observed {observed} | synthetic {synthetic} | "
          f"no goal available {missing}")
    print(f"states {total_states} -> {args.out}")


if __name__ == "__main__":
    main()
