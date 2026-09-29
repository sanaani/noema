#!/usr/bin/env python3
"""run-phase13.py -- a 15-year watch: does shape find cold jumps given time?

Everything is fixed in results/phase-13-long-watch/README.md. Cells, features
and rungs come from scripts/run-phase11.py and scripts/run-phase12.py.

    scripts/run-phase13.py --out DIR [--smoke]   (reads papers, refs, authors .jsonl.gz)
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


p11, p12 = load("run-phase11"), load("run-phase12")
log = p11.log

SEED = 20261004
WINDOW = (2006, 2007, 2021)
FOLDS = 5
TOOK_HOLD = 5
MIN_JUMPS, MIN_HELD = 400, 100


def oof_scores(X, y, tool, n_tools, rng):
    """Out-of-fold decision scores, BASE (all but the last column) and BASE+SHAPE."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    fold = rng.permutation(n_tools) % FOLDS
    f = fold[tool]
    scores = np.zeros((2, len(y)))
    for j, cols in enumerate((slice(0, X.shape[1] - 1), slice(0, X.shape[1]))):
        for k in range(FOLDS):
            tr, te = f != k, f == k
            if not te.any():
                continue
            m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
            m.fit(X[tr][:, cols], y[tr])
            scores[j, te] = m.decision_function(X[te][:, cols])
    return scores


def compare(scores, y, tool, n_tools, boot, rng):
    inv = [np.unique(s, return_inverse=True)[1] for s in scores]
    draws = np.empty((boot, 2))
    for d in range(boot):
        w = np.bincount(rng.integers(0, n_tools, n_tools), minlength=n_tools)[tool]
        w = w.astype(float)
        for j in range(2):
            n = inv[j].max() + 1
            draws[d, j] = p11.rank_auc(
                inv[j], np.bincount(inv[j], w * y, n), np.bincount(inv[j], w * ~y, n)
            )
    a0, a1 = p11.auc(scores[0], y), p11.auc(scores[1], y)
    return {
        "auc_BASE": a0,
        "auc_BASE+SHAPE": a1,
        "difference": a1 - a0,
        "ci95": [float(x) for x in np.percentile(draws[:, 1] - draws[:, 0], [2.5, 97.5])],
        "positives": int(y.sum()),
        "cells": int(len(y)),
        "top": {
            str(n): {
                "BASE": int(y[np.argsort(-scores[0], kind="stable")[:n]].sum()),
                "BASE+SHAPE": int(y[np.argsort(-scores[1], kind="stable")[:n]].sum()),
                "chance": n * float(y.mean()),
            }
            for n in (100, 1000)
        },
    }


def verdict(r, minimum):
    if r["positives"] < minimum:
        return "underpowered"
    lo, hi = r["ci95"]
    if lo > 0:
        return (
            "shape predicts cold jumps"
            if r["difference"] >= 0.03
            else "detectable on cold cells, small"
        )
    return "shape hurts on cold cells" if hi < 0 else "no measurable help on cold cells"


def main() -> int:
    from sklearn.feature_extraction.text import TfidfVectorizer

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    out, smoke = args.out, args.smoke

    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        P = [json.loads(line) for line in f]
    with (
        gzip.open(out / "refs.jsonl.gz", "rt") as f,
        gzip.open(out / "authors.jsonl.gz", "rt") as g,
    ):
        for p, r, a in zip(P, map(json.loads, f), map(json.loads, g), strict=True):
            assert p["id"] == r["id"] == a["id"]
            p["refs"], p["openalex"], p["authors"] = r["refs"], r["openalex"], a["authors"]
    H, o0, o1 = (2012, 2013, 2016) if smoke else WINDOW
    min_cites, min_pos = (2, 1) if smoke else (p11.MIN_CITES, p11.MIN_POSITIVE)
    boot = 20 if smoke else p11.BOOT
    texts = [p["title"] + ". " + p["abstract"] for p in P]
    vec = TfidfVectorizer(
        sublinear_tf=True, min_df=1 if smoke else 5, max_df=0.5, stop_words="english"
    )
    vec.fit([t for t, p in zip(texts, P, strict=True) if p["year"] <= H])
    w = p11.window_cells(P, H, o0, o1, vec.transform(texts), min_cites, min_pos)
    rung, ladder_info = p12.ladder(P, H, w)
    report: dict = {"seed": SEED, "boot": boot, "smoke": smoke, "window": [H, o0, o1]}
    report["counts"], report["ladder"] = w["counts"], ladder_info
    report["rungs"] = {
        f"{k} {p12.RUNGS[k]}": {
            "cells": int((rung == k).sum()),
            "positives": int(w["pos"][rung == k].sum()),
            "rate": float(w["pos"][rung == k].mean()) if (rung == k).any() else None,
        }
        for k in p12.RUNGS
    }
    log(f"rungs: {report['rungs']}")

    cold = rung == 5
    X, tool = w["X"][cold], w["tool_row"][cold]
    jump, held = w["pos"][cold], w["outcome"][cold] >= TOOK_HOLD
    nt = len(w["tools"])
    rng = np.random.default_rng(SEED)
    if not (jump.any() and (~jump).any()):
        report["note"] = "too few cold jumps to fit"
        (out / "phase13.json").write_text(json.dumps(report, indent=2) + "\n")
        log("too few cold jumps; wrote counts only")
        return 0
    scores = oof_scores(X, jump, tool, nt, rng)
    report["H1"] = compare(scores, jump, tool, nt, boot, rng)
    report["H1"]["verdict"] = verdict(report["H1"], MIN_JUMPS)
    if held.any() and (~held).any():
        report["H2"] = compare(scores, held, tool, nt, boot, rng)
        report["H2"]["verdict"] = verdict(report["H2"], MIN_HELD)
    for k in ("H1", "H2"):
        r = report.get(k)
        if r:
            log(
                f"{k}: {r['auc_BASE']:.4f} -> {r['auc_BASE+SHAPE']:.4f} ({r['difference']:+.4f} "
                f"{r['ci95']}) {r['positives']} positives -> {r['verdict']}; top {r['top']}"
            )

    # for reading
    pct = [(np.argsort(np.argsort(s)) + 0.5) / len(s) for s in scores]
    idx = np.nonzero(cold)[0]

    def row(j):
        k = idx[j]
        return {
            "tool": w["tools"][w["tool_row"][k]],
            "area": w["areas"][w["area_col"][k]],
            "outcome_papers": int(w["outcome"][k]),
            "percentile_BASE": float(pct[0][j]),
            "percentile_BASE+SHAPE": float(pct[1][j]),
        }

    oc = w["outcome"][cold]
    report["strongest_cold_jumps"] = [row(j) for j in np.argsort(-oc, kind="stable")[:20]]
    report["top_20_BASE+SHAPE"] = [row(j) for j in np.argsort(-scores[1], kind="stable")[:20]]
    (out / "phase13.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase13.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
