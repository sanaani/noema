#!/usr/bin/env python3
"""count-phase21.py -- sizing for Phase 21: counts only, no similarity, no model.

For unconnected (work, area) pairs at cutoffs 2005 and 2015, how many have a
span at or above each threshold, how many were crossed in the 10 outcome
years, and how many caught on (>= 5 area papers citing the work). Thresholds
include Phase 18/19's arrival-based percentiles (learn window: 90th 4.65 bits,
99th 5.84 bits). Span as scripts/run-phase20.py.

    scripts/count-phase21.py --out DIR [--smoke]
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CUTOFFS = (2005, 2015)
ARRIVAL_P90, ARRIVAL_P99 = 4.65, 5.84  # Phase 19 decile 10 lower bound; Phase 18 top-1% threshold
GRID = [3.5, 4.0, 4.25, 4.5, ARRIVAL_P90, 4.75, 5.0, 5.25, 5.5, ARRIVAL_P99, 6.0, 6.5, 7.0]


def main() -> int:
    import scipy.sparse as sp

    p20 = load("run-phase20")
    log = p20.load("run-phase11").log
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    out = args.out

    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        P = [json.loads(line) for line in f]
    with gzip.open(out / "refs.jsonl.gz", "rt") as f:
        for p, r in zip(P, map(json.loads, f), strict=True):
            p["refs"] = [w for w in r["refs"] if w not in p20.DROP]
            p.pop("abstract", None)
    if args.smoke:
        P = P[::4]
    areas = sorted({p["area"] for p in P})
    ai = {a: k for k, a in enumerate(areas)}
    na = len(areas)
    year = np.array([p["year"] for p in P])
    area = np.array([ai[p["area"]] for p in P])
    works = sorted({w for p in P for w in p["refs"]})
    wi = {w: k for k, w in enumerate(works)}
    cp = np.array([k for k, p in enumerate(P) for _ in p["refs"]])
    cw = np.array([wi[w] for p in P for w in p["refs"]])
    nw = len(works)
    log(f"{len(P):,} papers, {nw:,} works, {len(cp):,} citations")

    report = {"thresholds_bits": GRID, "arrival_p90": ARRIVAL_P90, "arrival_p99": ARRIVAL_P99}
    for H in CUTOFFS:
        m = year[cp] <= H
        counts = sp.csr_matrix((np.ones(m.sum()), (cw[m], area[cp[m]])), shape=(nw, na)).toarray()
        F = p20.cocitation_matrix(sp.csr_matrix(counts > 0).astype(float))
        keep = np.nonzero(counts.sum(1) >= p20.MIN_CITERS)[0]
        S = p20.span_matrix(counts[keep], F)
        kpos = -np.ones(nw, int)
        kpos[keep] = np.arange(len(keep))
        o = (year[cp] > H) & (year[cp] <= H + p20.WINDOW) & (kpos[cw] >= 0)
        outc = sp.csr_matrix(
            (np.ones(o.sum()), (kpos[cw[o]], area[cp[o]])), shape=(len(keep), na)
        ).toarray()
        cand = counts[keep] == 0
        s, y = S[cand], outc[cand]
        rows = []
        for t in GRID:
            far = s >= t
            rows.append(
                {
                    "threshold_bits": t,
                    "pairs": int(far.sum()),
                    "share_of_candidates": float(far.mean()),
                    "crossed": int((far & (y >= 1)).sum()),
                    "important_jumps": int((far & (y >= p20.TOOK_HOLD)).sum()),
                }
            )
        report[str(H)] = {"candidate_pairs": int(cand.sum()), "by_threshold": rows}
        log(f"H={H}: {report[str(H)]}")
    (out / "count21.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'count21.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
