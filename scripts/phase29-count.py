#!/usr/bin/env python3
"""phase29-count.py -- the counts Phase 29's pre-registration quotes, from 2024 data.

Cross-area pairs of 2024 Mathlib theorems sharing a lemma used by 2..16 theorems
(Lean's generated names excluded), counted with repeats across lemmas; how many
fall inside the test corpus; and the theorems a capture must cover.

    scripts/phase29-count.py --out results/phase-29-full-mathlib-pairs/results/count.json
"""

from __future__ import annotations

import argparse
import collections
import gzip
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDGES = ROOT / "results/phase-1-recognition/link-graph-v1/edges.jsonl.gz"
NAMES = ROOT / "results/phase-3-doubled-corpus/draw/resolved-names.txt.gz"
AUTO = re.compile(r"(\.proof_\d+|\.eq_\d+|^inst|\.inst|^Mathlib\.Tactic\.|^Mathlib\.Meta\.)")
CUTOFF = 16


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--names-out", type=Path, help="write the theorems to capture, one per line")
    args = ap.parse_args()
    corpus = set(gzip.open(NAMES, "rt").read().split())
    df: collections.Counter[str] = collections.Counter()
    users: dict[str, list[str]] = collections.defaultdict(list)
    area, module = {}, {}
    for line in gzip.open(EDGES, "rt"):
        r = json.loads(line)
        module[r["theorem"]] = r["module"]
        area[r["theorem"]] = r["module"].split(".")[1] if r["module"].count(".") else ""
        for lem in {x for x in r.get("deps") or [] if not AUTO.search(x)}:
            df[lem] += 1
            users[lem].append(r["theorem"])
    pairs = in_corpus = 0
    theorems: set[str] = set()
    for lem, ts in users.items():
        if 2 <= df[lem] <= CUTOFF:
            for a, b in itertools.combinations(ts, 2):
                if area[a] != area[b]:
                    pairs += 1
                    theorems.update((a, b))
                    in_corpus += a in corpus and b in corpus
    report = {"theorems_2024": len(area), "modules": len(set(module.values())),
              "cutoff": CUTOFF, "cross_area_pairs": pairs, "pairs_in_corpus": in_corpus,
              "theorems_in_pairs": len(theorems),
              "modules_in_pairs": len({module[t] for t in theorems})}  # fmt: skip
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    if args.names_out:
        args.names_out.write_text("\n".join(sorted(theorems)) + "\n", encoding="utf-8",
                                  newline="\n")  # fmt: skip
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
