#!/usr/bin/env python3
"""run-phase15.py -- cold jumps between OpenAlex topics, not arXiv areas.

Everything is fixed in results/phase-15-topic-grain/README.md. Cells and
features come from scripts/run-phase11.py, the first three rungs from
scripts/run-phase12.py, topics as areas from scripts/count-grains.py.

    scripts/run-phase15.py --out DIR [--smoke]
        (reads papers, refs, authors, topics .jsonl.gz)
"""

from __future__ import annotations

import argparse
import collections
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


p11, p12, grains = load("run-phase11"), load("run-phase12"), load("count-grains")
log = p11.log

SEED = 20261006
WINDOW = (2006, 2007, 2021)
FOLDS = 5
TOOK_HOLD = 5
ENOUGH_JUMPS, ENOUGH_HOLD = 600, 150
MIN_JUMPS, MIN_HELD = 400, 100
RUNG_BOOT = 200
RUNGS = {
    1: "shared paper",
    2: "shared author",
    3: "second-hand",
    4: "same subfield",
    5: "neighbouring field",
    6: "cold",
}


def ladder(Q, H, w, subfield_of):
    """Rungs 1-6 (README table). Rungs 1-3 are Phase 12's."""
    r12, info = p12.ladder(Q, H, w)
    ai = {a: c for c, a in enumerate(w["areas"])}
    ti = {t: r for r, t in enumerate(w["tools"])}
    subs = sorted({subfield_of.get(a, a) for a in w["areas"]})
    si = {s: k for k, s in enumerate(subs)}
    area_sub = np.array([si[subfield_of.get(a, a)] for a in w["areas"]])
    tool_sub = np.zeros((len(ti), len(subs)), bool)
    for p in Q:
        if p["year"] <= H:
            s = area_sub[ai[p["area"]]]
            for t in p["refs"]:
                r = ti.get(t)
                if r is not None:
                    tool_sub[r, s] = True
    tr, ar = w["tool_row"], w["area_col"]
    same = tool_sub[tr, area_sub[ar]]
    flow = w["X"][:, p11.BASE.index("flow")]
    thr = float(np.quantile(flow[flow > 0], p12.FLOW_QUANTILE)) if (flow > 0).any() else 0.0
    rung = np.full(len(tr), 6)
    rung[(flow > 0) & (flow >= thr)] = 5
    rung[same] = 4
    rung[r12 <= 3] = r12[r12 <= 3]
    info.update({"subfields": len(subs), "positive_flow_threshold": thr})
    return rung, info


def oof_scores(X, y, tool, n_tools, rng):
    """Out-of-fold decision scores, BASE (all but the last column) and BASE+SHAPE."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    f = (rng.permutation(n_tools) % FOLDS)[tool]
    scores = np.zeros((2, len(y)))
    for j, cols in enumerate((slice(0, X.shape[1] - 1), slice(0, X.shape[1]))):
        for k in range(FOLDS):
            tr, te = f != k, f == k
            if not te.any():
                continue
            m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
            m.fit(X[tr][:, cols], y[tr])
            scores[j, te] = m.decision_function(X[te][:, cols])
            log(f"  fold {k + 1}/{FOLDS}, model {j + 1}/2")
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
        if (d + 1) % 100 == 0:
            log(f"  bootstrap {d + 1}/{boot}")
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
        gzip.open(out / "topics.jsonl.gz", "rt") as h,
    ):
        for p, r, a, t in zip(P, *(map(json.loads, x) for x in (f, g, h)), strict=True):
            assert p["id"] == r["id"] == a["id"] == t["id"]
            p["refs"], p["openalex"], p["authors"] = r["refs"], r["openalex"], a["authors"]
            p["topics"], p["subfields"] = t["topics"], t["subfields"]
    subfield_of = {}
    for p in P:
        for t, s in zip(p["topics"], p["subfields"], strict=False):
            subfield_of.setdefault(t, s)
    Q = grains.relabel(P, "oa_topic")
    del P
    if smoke:  # every 50th paper: loose smoke thresholds on all papers would be huge
        Q = Q[::50]
    log(f"{len(Q):,} papers with topics, {len(subfield_of):,} topics")

    H, o0, o1 = (2012, 2013, 2016) if smoke else WINDOW
    min_cites, min_pos = (2, 1) if smoke else (p11.MIN_CITES, p11.MIN_POSITIVE)
    boot = 20 if smoke else p11.BOOT
    rung_boot = 10 if smoke else RUNG_BOOT
    texts = [p["title"] + ". " + p["abstract"] for p in Q]
    vec = TfidfVectorizer(
        sublinear_tf=True, min_df=1 if smoke else 5, max_df=0.5, stop_words="english"
    )
    vec.fit([t for t, p in zip(texts, Q, strict=True) if p["year"] <= H])
    X_text = vec.transform(texts)
    del texts
    w = p11.window_cells(Q, H, o0, o1, X_text, min_cites, min_pos)
    del X_text
    log(f"cells: {w['counts']}")
    rung, info = ladder(Q, H, w, subfield_of)
    outc = w["outcome"]
    report: dict = {"seed": SEED, "boot": boot, "smoke": smoke, "window": [H, o0, o1]}
    report["counts"], report["ladder"] = w["counts"], info
    report["rungs"] = {
        f"{k} {RUNGS[k]}": {
            "cells": int((rung == k).sum()),
            "jumps": int(((rung == k) & (outc >= 2)).sum()),
            "took_hold": int(((rung == k) & (outc >= TOOK_HOLD)).sum()),
            "rate": float((outc[rung == k] >= 2).mean()) if (rung == k).any() else None,
        }
        for k in RUNGS
    }
    log(f"rungs: {report['rungs']}")

    r6 = report["rungs"]["6 cold"]
    if r6["jumps"] >= ENOUGH_JUMPS and r6["took_hold"] >= ENOUGH_HOLD:
        pop, report["population"] = rung == 6, "rung 6 (cold)"
    else:
        pop, report["population"] = np.isin(rung, (4, 6)), "rungs 4 and 6 (cold or same subfield)"
    log(f"population: {report['population']}")

    nt = len(w["tools"])
    rng = np.random.default_rng(SEED)
    X, tool = w["X"][pop], w["tool_row"][pop]
    jump, held = outc[pop] >= 2, outc[pop] >= TOOK_HOLD
    if not (jump.any() and (~jump).any()):
        report["note"] = "too few cold jumps to fit"
        (out / "phase15.json").write_text(json.dumps(report, indent=2) + "\n")
        log("too few cold jumps; wrote counts only")
        return 0
    log("H1 scores")
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

    report["gain_by_rung"] = {}
    for k in range(1, 6):
        m = rung == k
        y = outc[m] >= 2
        if y.sum() < 10 or (~y).sum() < 10:
            report["gain_by_rung"][f"{k} {RUNGS[k]}"] = None
            continue
        log(f"rung {k} scores")
        s = oof_scores(w["X"][m], y, w["tool_row"][m], nt, rng)
        r = compare(s, y, w["tool_row"][m], nt, rung_boot, rng)
        report["gain_by_rung"][f"{k} {RUNGS[k]}"] = r
        log(f"rung {k}: {r['difference']:+.4f} {r['ci95']}, {r['positives']} jumps")

    # for reading: each tool's main topic of use, from its history citers
    ti = {t: r for r, t in enumerate(w["tools"])}
    home = collections.defaultdict(collections.Counter)
    for p in Q:
        if p["year"] <= H:
            for t in p["refs"]:
                if t in ti:
                    home[t][p["area"]] += 1
    pct = [(np.argsort(np.argsort(s)) + 0.5) / len(s) for s in scores]
    idx = np.nonzero(pop)[0]

    def row(j):
        k = idx[j]
        t = w["tools"][w["tool_row"][k]]
        return {
            "tool": t,
            "main_topic_of_use": home[t].most_common(1)[0][0] if home[t] else None,
            "target_topic": w["areas"][w["area_col"][k]],
            "rung": int(rung[k]),
            "outcome_papers": int(outc[k]),
            "percentile_BASE": float(pct[0][j]),
            "percentile_BASE+SHAPE": float(pct[1][j]),
        }

    report["strongest_cold_jumps"] = [row(j) for j in np.argsort(-outc[pop], kind="stable")[:20]]
    report["top_20_BASE+SHAPE"] = [row(j) for j in np.argsort(-scores[1], kind="stable")[:20]]
    (out / "phase15.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase15.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
