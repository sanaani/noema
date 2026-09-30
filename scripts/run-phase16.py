#!/usr/bin/env python3
"""run-phase16.py -- Phase 15 again without broken tool records and off-field topics.

Everything is fixed in results/phase-16-clean-labels/README.md. Cells, rungs
and the model are Phase 15's (scripts/run-phase15.py); the labels come from
scripts/phase16-labels.py.

    scripts/run-phase16.py --out DIR [--smoke]
        (reads papers, refs, authors, topics .jsonl.gz, tools.json, topic-fields.json)
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


p15 = load("run-phase15")
p11, grains = p15.p11, p15.grains
log = p11.log

SEED = 20261007
SIDE_BOOT = 200
NEAR_MATH = {
    "Mathematics",
    "Computer Science",
    "Physics and Astronomy",
    "Engineering",
    "Decision Sciences",
    "Economics, Econometrics and Finance",
}
POPULATIONS = {
    "B near-math topics": "primary",
    "A broken records removed": "side",
    "C mathematics topics": "side",
}


def broken(tools):
    """Tool records OpenAlex no longer serves, or serves with no title."""
    return {t for t, v in tools.items() if not v["found"] or not v["title"]}


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
    tools_meta = json.loads((out / "tools.json").read_text())
    field_of = {
        t: v["field"] for t, v in json.loads((out / "topic-fields.json").read_text()).items()
    }
    Q = grains.relabel(P, "oa_topic")
    del P
    if smoke:
        Q = Q[::50]
    log(f"{len(Q):,} papers with topics")

    H, o0, o1 = (2012, 2013, 2016) if smoke else p15.WINDOW
    min_cites, min_pos = (2, 1) if smoke else (p11.MIN_CITES, p11.MIN_POSITIVE)
    boot = 20 if smoke else p11.BOOT
    side_boot = 10 if smoke else SIDE_BOOT
    texts = [p["title"] + ". " + p["abstract"] for p in Q]
    vec = TfidfVectorizer(
        sublinear_tf=True, min_df=1 if smoke else 5, max_df=0.5, stop_words="english"
    )
    vec.fit([t for t, p in zip(texts, Q, strict=True) if p["year"] <= H])
    X_text = vec.transform(texts)
    del texts
    w = p11.window_cells(Q, H, o0, o1, X_text, min_cites, min_pos)
    del X_text
    rung, info = p15.ladder(Q, H, w, subfield_of)
    outc = w["outcome"]
    cold = rung == 6
    nt = len(w["tools"])

    bad = broken(tools_meta)
    tool_ok = np.array([t not in bad for t in w["tools"]])[w["tool_row"]]
    area_field = np.array([field_of.get(a, "") for a in w["areas"]])[w["area_col"]]
    near = np.isin(area_field, list(NEAR_MATH))
    maths = area_field == "Mathematics"
    report: dict = {"seed": SEED, "boot": boot, "smoke": smoke, "window": [H, o0, o1]}
    report["counts"], report["ladder"] = w["counts"], info
    report["broken_tools"] = sorted(bad & set(w["tools"]))

    # Phase 15's top 1,000 again (same seed, same population), then check each hit.
    rng = np.random.default_rng(p15.SEED)
    jump = outc[cold] >= 2
    s15 = p15.oof_scores(w["X"][cold], jump, w["tool_row"][cold], nt, rng)
    idx = np.nonzero(cold)[0]
    top = idx[np.argsort(-s15[1], kind="stable")[:1000]]
    hits = top[outc[top] >= 2]
    report["phase15_check"] = {
        "auc_BASE": p11.auc(s15[0], jump),
        "auc_BASE+SHAPE": p11.auc(s15[1], jump),
        "top_1000_jumps": int(len(hits)),
    }
    report["phase15_hits"] = {
        "total": int(len(hits)),
        "broken_tool": int((~tool_ok[hits]).sum()),
        "off_field_target": int((tool_ok[hits] & ~near[hits]).sum()),
        "survive_B": int((tool_ok[hits] & near[hits]).sum()),
        "survive_C": int((tool_ok[hits] & maths[hits]).sum()),
        "top_1000_broken_tool_cells": int((~tool_ok[top]).sum()),
        "top_1000_off_field_cells": int((tool_ok[top] & ~near[top]).sum()),
    }
    log(f"phase 15 check {report['phase15_check']}; hits {report['phase15_hits']}")

    rng = np.random.default_rng(SEED)
    masks = {
        "B near-math topics": cold & tool_ok & near,
        "A broken records removed": cold & tool_ok,
        "C mathematics topics": cold & tool_ok & maths,
    }
    report["populations"] = {}
    for name, m in masks.items():
        b = boot if POPULATIONS[name] == "primary" else side_boot
        X, tool = w["X"][m], w["tool_row"][m]
        y1, y2 = outc[m] >= 2, outc[m] >= p15.TOOK_HOLD
        log(f"{name}: {int(m.sum()):,} cells, {int(y1.sum())} jumps, {int(y2.sum())} took hold")
        if y1.sum() < 2:
            report["populations"][name] = {"cells": int(m.sum()), "note": "too few jumps"}
            continue
        s = p15.oof_scores(X, y1, tool, nt, rng)
        r = {"H1": p15.compare(s, y1, tool, nt, b, rng)}
        r["H1"]["verdict"] = p15.verdict(r["H1"], p15.MIN_JUMPS)
        if y2.any():
            r["H2"] = p15.compare(s, y2, tool, nt, b, rng)
            r["H2"]["verdict"] = p15.verdict(r["H2"], p15.MIN_HELD)
        report["populations"][name] = r
        for k in ("H1", "H2"):
            if k in r:
                x = r[k]
                log(
                    f"  {k}: {x['auc_BASE']:.4f} -> {x['auc_BASE+SHAPE']:.4f} "
                    f"({x['difference']:+.4f} {x['ci95']}) {x['positives']} -> {x['verdict']}; "
                    f"top {x['top']}"
                )
        if POPULATIONS[name] == "primary":
            ids = np.nonzero(m)[0]

            def row(j, ids=ids):
                k = ids[j]
                return {
                    "tool": w["tools"][w["tool_row"][k]],
                    "target_topic": w["areas"][w["area_col"][k]],
                    "outcome_papers": int(outc[k]),
                }

            r["top_20_BASE+SHAPE"] = [row(j) for j in np.argsort(-s[1], kind="stable")[:20]]
            best = np.argsort(-s[1], kind="stable")[:1000]
            r["top_1000_hits"] = [row(j) for j in best if y1[j]]
    (out / "phase16.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase16.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
