"""Referee the trained head on held-out families: target-vs-lexical rank.

For each direction (anchor -> target) in the held-out cases, rank the target
among {target, 64 background, anchor hard lexical lookalikes} by cosine
distance, using frozen vectors and head-projected vectors. Missing (gated)
names are reported as unevaluable, mirroring rejected_for_context.
"""

import argparse
import json
from pathlib import Path

import numpy as np


def rank_of(dist_target, dist_controls):
    controls = np.asarray(dist_controls)
    return int(1 + np.sum(controls < dist_target - 1e-12))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--names", type=Path, required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--families", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("refusing to overwrite output directory")
    X = np.load(args.vectors)
    names = json.loads(args.names.read_text())
    index = {n: i for i, n in enumerate(names)}
    W = np.load(args.head)
    P = X @ W
    P /= np.linalg.norm(P, axis=1, keepdims=True) + 1e-12
    sel = json.loads(args.selection.read_text())

    out_cases = []
    for label, a, b, _bridge in sel["cases"]:
        if label not in args.families:
            continue
        case = {"label": label, "directions": []}
        for anchor, target in ((a, b), (b, a)):
            cands = [target] + sel["background"] + sel["hard_controls"].get(anchor, [])
            missing = [c for c in [anchor] + cands if c not in index]
            if missing:
                case["directions"].append({"anchor": anchor, "target": target,
                                           "unevaluable": missing})
                continue
            d = {"anchor": anchor, "target": target, "candidates": len(cands) - 1}
            for tag, M in (("frozen", X), ("head", P)):
                ai = index[anchor]
                dist = 1.0 - M[[index[c] for c in cands]] @ M[ai]
                lex = sel["hard_controls"].get(anchor, [])
                lex_d = [dist[cands.index(c)] for c in lex if c in index]
                d[tag] = {"target_rank": rank_of(dist[0], dist[1:]),
                          "best_lexical_rank": rank_of(min(lex_d), dist[1:]) if lex_d else None,
                          "beats_lexical": bool((dist[0] < min(lex_d) - 1e-12)) if lex_d else None}
            case["directions"].append(d)
        out_cases.append(case)
    args.output.mkdir()
    args.output.joinpath("referee.json").write_text(
        json.dumps({"families": args.families, "cases": out_cases}, indent=2) + "\n")
    for c in out_cases:
        for d in c["directions"]:
            if "unevaluable" in d:
                print(f"{c['label']} {d['anchor']}->{d['target']}: UNEVALUABLE {d['unevaluable']}")
                continue
            for tag in ("frozen", "head"):
                r = d[tag]
                print(f"{c['label']} {d['anchor']}->{d['target']} [{tag}]: "
                      f"target_rank={r['target_rank']}/{d['candidates']} "
                      f"best_lexical={r['best_lexical_rank']} beats_lexical={r['beats_lexical']}")
    print("REFEREE DONE", flush=True)


if __name__ == "__main__":
    main()
