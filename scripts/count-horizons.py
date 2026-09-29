#!/usr/bin/env python3
"""count-horizons.py -- how many cold jumps does a longer watch collect? (sizing, no model scores)

For each history cutoff H, builds Phase 11's cells and Phase 12's rungs, then
counts, for every watch length L (outcome years H+1 .. H+L), the cells on each
rung that reach 2 outcome papers (a jump) and 5 (took hold). Reference coverage
by outcome year is reported too, since it falls after 2020.

    scripts/count-horizons.py --out DIR   (reads papers, refs, authors .jsonl.gz)
"""

from __future__ import annotations

import argparse
import collections
import gzip
import importlib.util
import json
from pathlib import Path

import numpy as np


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


p11, p12 = load("run-phase11"), load("run-phase12")
CUTOFFS = (1998, 2000, 2002, 2004, 2006, 2008, 2010, 2012, 2015)
LAST = 2025


def main() -> int:
    import scipy.sparse as sp

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    out = ap.parse_args().out
    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        P = [json.loads(line) for line in f]
    for p in P:  # text is not needed: shape is not computed here
        p.pop("abstract"), p.pop("title")
    with (
        gzip.open(out / "refs.jsonl.gz", "rt") as f,
        gzip.open(out / "authors.jsonl.gz", "rt") as g,
    ):
        for p, r, a in zip(P, map(json.loads, f), map(json.loads, g), strict=True):
            p["refs"], p["openalex"], p["authors"] = r["refs"], r["openalex"], a["authors"]
    yr = collections.Counter(p["year"] for p in P)
    yr_refs = collections.Counter(p["year"] for p in P if p["refs"])
    report = {"coverage": {y: yr_refs[y] / yr[y] for y in sorted(yr)}, "cutoffs": {}}
    X0 = sp.csr_matrix((len(P), 1))
    for H in CUTOFFS:
        if sum(p["year"] <= H for p in P) < 2:  # a sample with no history this early
            continue
        w = p11.window_cells(P, H, H + 1, LAST, X0, p11.MIN_CITES, p11.MIN_POSITIVE)
        rung, _ = p12.ladder(P, H, w)
        ti = {t: r for r, t in enumerate(w["tools"])}
        ai = {a: c for c, a in enumerate(w["areas"])}
        cell = {
            (r, c): k for k, (r, c) in enumerate(zip(w["tool_row"], w["area_col"], strict=True))
        }
        by_year = np.zeros((LAST - H, len(rung)), np.int32)
        for p in P:
            if H < p["year"] <= LAST:
                c = ai.get(p["area"])
                for t in p["refs"]:
                    k = cell.get((ti.get(t), c))
                    if k is not None:
                        by_year[p["year"] - H - 1, k] += 1
        cum = by_year.cumsum(0)
        rep = {"tools": len(ti), "cells": int(len(rung)), "watch": {}}
        for L in range(1, LAST - H + 1):
            rep["watch"][L] = {
                str(k): {
                    "cells": int((rung == k).sum()),
                    "jumps": int((cum[L - 1][rung == k] >= 2).sum()),
                    "took_hold": int((cum[L - 1][rung == k] >= 5).sum()),
                }
                for k in range(1, 6)
            }
        c5 = rep["watch"]
        p11.log(
            f"H={H}: {len(ti):,} tools, cold cells {c5[1]['5']['cells']:,}; cold jumps / took hold "
            + ", ".join(
                f"L{L} {c5[L]['5']['jumps']}/{c5[L]['5']['took_hold']}"
                for L in (5, 10, 15, 20)
                if L in c5
            )
        )
        report["cutoffs"][H] = rep
    (out / "horizons.json").write_text(json.dumps(report, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
