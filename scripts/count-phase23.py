#!/usr/bin/env python3
"""count-phase23.py -- sizing for Phase 23: counts only, no similarity, no model.

At the 2005 cutoff, unconnected (work, area) pairs that are neither
"knocking" nor "next door" (the rule in results/phase-22-within-route/hits/),
by span threshold: how many there are, how many were crossed in 2006-2015,
and how many caught on (>= 5 area papers citing the work). Also the same
counts for knocking and next-door pairs, for comparison. Span and the
build are Phase 22's.

    scripts/count-phase23.py --out DIR [--smoke]
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


CUTOFF = 2005
WINDOW = 10
GRID = [0.0, 3.0, 3.5, 4.0, 4.25, 4.5, 4.65, 5.0, 5.25, 5.5, 5.84, 6.0]


def main() -> int:
    import scipy.sparse as sp

    hits = load("phase22-hits")
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
    hold = 1 if args.smoke else p20.TOOK_HOLD
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
    log(f"{len(P):,} papers, {nw:,} works")

    H = CUTOFF
    hist = year <= H
    m = hist[cp]
    counts = sp.csr_matrix((np.ones(m.sum()), (cw[m], area[cp[m]])), shape=(nw, na)).toarray()
    n_cit = counts.sum(1)
    F = p20.cocitation_matrix(sp.csr_matrix(counts > 0).astype(float))
    keep = np.nonzero(n_cit >= p20.MIN_CITERS)[0]
    S = p20.span_matrix(counts[keep], F)
    kpos = -np.ones(nw, int)
    kpos[keep] = np.arange(len(keep))
    o = (year[cp] > H) & (year[cp] <= H + WINDOW) & (kpos[cw] >= 0)
    outc = sp.csr_matrix(
        (np.ones(o.sum()), (kpos[cw[o]], area[cp[o]])), shape=(len(keep), na)
    ).toarray()

    sr, sc = [], []
    for k in np.nonzero(hist)[0]:
        sec = {ai[x] for x in P[k]["categories"][1:] if x in ai} - {area[k]}
        for w in P[k]["refs"]:
            if kpos[wi[w]] >= 0:
                for a in sec:
                    sr.append(kpos[wi[w]])
                    sc.append(a)
    secondary = sp.csr_matrix((np.ones(len(sr)), (sr, sc)), shape=(len(keep), na)).toarray() > 0
    near = np.zeros((na, na), bool)
    for a in range(na):
        near[a, hits.nearest_areas(F, a)] = True
    next_door = (counts[keep] > 0) @ near.T > 0  # [work, A]: a nearest area of A cites it

    r, c = np.nonzero(counts[keep] == 0)
    span = S[r, c]
    lab = np.where(secondary[r, c], 0, np.where(next_door[r, c], 1, 2))
    y = outc[r, c] >= hold
    crossed = outc[r, c] >= 1
    names = ["knocking", "next door", "surprising"]
    report = {"smoke": args.smoke, "cutoff": H, "candidate_pairs": int(len(r)), "by_threshold": []}
    for t in GRID:
        f = span >= t
        row = {"span_at_least": t}
        for k, n in enumerate(names):
            g = f & (lab == k)
            row[n] = {
                "pairs": int(g.sum()),
                "crossed": int(crossed[g].sum()),
                "important_jumps": int(y[g].sum()),
                "works_with_a_jump": int(len(np.unique(keep[r[g & y]]))),
            }
        report["by_threshold"].append(row)
        log(str(row))
    (out / "count23.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'count23.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
