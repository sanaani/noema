#!/usr/bin/env python3
"""phase28-rare-pdf.py -- set Phase 28's rare-lemma line from 2024 data alone.

Fixed in results/phase-28-far-pair-proof-states/README.md. Reads only Lean's
2024 dependency graph and the phase 3 corpus names; no 2026 data.

    usage pdf      lemmas used by exactly k theorems, and the share of them whose
                   users span more than one area, k = 1..1000
    the line       the last k before the count stops falling monotonically
    slopes         log-log slope of the pdf in doubling bins
    pairs          cross-area corpus pairs sharing a lemma used by 2..c theorems

    scripts/phase28-rare-pdf.py \\
        --out results/phase-28-far-pair-proof-states/results/usage-pdf-2024.json
"""

from __future__ import annotations

import argparse
import collections
import gzip
import itertools
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDGES = ROOT / "results/phase-1-recognition/link-graph-v1/edges.jsonl.gz"
NAMES = ROOT / "results/phase-3-doubled-corpus/draw/resolved-names.txt.gz"
# names Lean generates itself: auxiliary proofs, equation lemmas, instances, tactic internals
AUTO = re.compile(r"(\.proof_\d+|\.eq_\d+|^inst|\.inst|^Mathlib\.Tactic\.|^Mathlib\.Meta\.)")
CUTOFFS = (4, 8, 16, 32, 64, 128, 200)
BINS = (1, 2, 3, 5, 9, 17, 33, 65, 129, 257, 513, 1001)
KMAX = 1000


def area_of(module: str) -> str:
    return module.split(".")[1] if module.count(".") else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    corpus = set(gzip.open(NAMES, "rt").read().split())
    df: collections.Counter[str] = collections.Counter()
    reach: dict[str, set[str]] = collections.defaultdict(set)
    deps: dict[str, set[str]] = {}
    area: dict[str, str] = {}
    for line in gzip.open(EDGES, "rt"):
        r = json.loads(line)
        a = area_of(r["module"])
        area[r["theorem"]] = a
        used = {lem for lem in r.get("deps") or [] if not AUTO.search(lem)}
        for lem in used:
            df[lem] += 1
            reach[lem].add(a)
        if r["theorem"] in corpus:
            deps[r["theorem"]] = used

    n = collections.Counter(df.values())
    cross = collections.Counter(c for lem, c in df.items() if len(reach[lem]) > 1)
    pdf = {
        k: {"lemmas": n[k], "cross_share": round(cross[k] / n[k], 4) if n[k] else None}
        for k in range(1, KMAX + 1)
    }
    line = next(k for k in range(1, KMAX) if n[k + 1] > n[k])
    slopes, prev = [], None
    for lo, hi in itertools.pairwise(BINS):
        dens = sum(n[k] for k in range(lo, hi)) / (hi - lo)
        mid = math.sqrt(lo * (hi - 1))
        slope = None if prev is None else math.log(dens / prev[0]) / math.log(mid / prev[1])
        slopes.append(
            {
                "bin": f"{lo}-{hi - 1}",
                "lemmas_per_k": round(dens, 2),
                "slope": None if slope is None else round(slope, 3),
            }
        )
        prev = (dens, mid)

    pairs = {}
    for c in CUTOFFS:
        users = collections.defaultdict(list)
        for t, used in deps.items():
            for lem in used:
                if 2 <= df[lem] <= c:
                    users[lem].append(t)
        found, via = set(), set()
        for lem, ts in users.items():
            for a, b in itertools.combinations(sorted(ts), 2):
                if area[a] != area[b]:
                    found.add((a, b))
                    via.add(lem)
        pairs[str(c)] = {
            "pairs": len(found),
            "lemmas": len(via),
            "theorems": len({t for p in found for t in p}),
        }

    report = {
        "edges": str(EDGES.relative_to(ROOT)),
        "corpus": len(corpus),
        "corpus_in_2024_graph": len(deps),
        "line": line,
        "pdf": pdf,
        "slopes": slopes,
        "pairs_by_cutoff": pairs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"line {line}; pairs " + ", ".join(f"{c}: {v['pairs']:,}" for c, v in pairs.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
