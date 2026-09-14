"""Reproduce the premeasurement structural feasibility census (no embeddings)."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from noema.associahedron import population, transfer
from noema.strategy_transfer import clades


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    records = population(8)
    index = defaultdict(set)
    for i, record in enumerate(records):
        for program in record["programs"]:
            index[program].add(i)
    spans = [(clades(r["source"]), clades(r["target"])) for r in records]

    def signature(a, b):
        return tuple(len(x & y) for x, y in zip(spans[a], spans[b], strict=True))

    rng = np.random.default_rng(914202610)
    used, used_programs, chosen = set(), set(), []
    scanned = 0
    for i in rng.permutation(len(records)).tolist():
        if i in used or records[i]["programs"] & used_programs:
            continue
        scanned += 1
        candidates = set().union(*(index[p] for p in records[i]["programs"])) - {i} - used
        positive = [
            j
            for j in sorted(candidates)
            if not records[j]["programs"] & used_programs
            and min(transfer(records[i], records[j])) >= 0.75
        ]
        rng.shuffle(positive)
        for j in positive:
            sig = signature(i, j)
            forbidden = used_programs | records[i]["programs"] | records[j]["programs"]
            negative = [
                k
                for k in range(len(records))
                if k not in used | {i, j}
                and signature(i, k) == sig
                and not records[k]["programs"] & forbidden
            ]
            if not negative:
                continue
            k = int(rng.choice(negative))
            chosen.append([i, j, k, sig])
            used.update((i, j, k))
            used_programs.update(*(records[x]["programs"] for x in (i, j, k)))
            break
        if len(chosen) >= 64:
            break
    report = {
        "records": len(records),
        "triplets": len(chosen),
        "scanned": scanned,
        "seed": 914202610,
        "selected_indices_for_feasibility_only": chosen,
        "note": "No embeddings or performance; selection uses exact source and target clade "
        "matching and disjoint program banks across triplets.",
    }
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)


if __name__ == "__main__":
    main()
