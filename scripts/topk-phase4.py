#!/usr/bin/env python3
"""topk-phase4.py -- hits among the top k hard-subset pairs, A against B, for large k.

Exploratory, run after phase 4's results were read; not pre-registered. The
pre-registered top-k stops at 10,000; this extends it to 5,000,000, plain and
kind-aware, from the walks' cached histograms. A bin straddling k contributes
its positives pro rata.

    scripts/topk-phase4.py results/phase-4-trained-encoder/results/topk.json
"""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import forward_blocks as fb  # noqa: E402

spec = importlib.util.spec_from_file_location("a4", R / "scripts/analyze-phase4.py")
a4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a4)
a3 = a4.a3


class Args:
    union = R / "outputs/phase-3-doubled-corpus/union"


s = a3.SUBS.index(a4.HARD)
out = {}
ARMS = (
    ("A", Args.union / "centroids.npz", R / "outputs/phase-3-doubled-corpus/analysis/hist.npz"),
    (
        "B",
        R / "outputs/phase-4-trained-encoder/union-b/centroids.npz",
        R / "outputs/phase-4-trained-encoder/analysis/hist-b.npz",
    ),
)
for tag, cen, hist in ARMS:
    corpus, feat = a4.side(Args, cen)
    m = fb.subset_masks(feat)[a4.HARD]
    H = np.load(hist)["H"]
    bins = fb.bin_of(feat["angle"])[m]
    pct = a3.Percentile([H[s][q].sum(axis=0) for q in range(3)])
    rows = {}
    variants = (
        ("plain", H[s].sum(axis=(0, 1)), bins),
        ("kind_aware", pct.pop.hist, pct.bins(feat["kind"][m], bins)),
    )
    for label, pop_h, pb in variants:
        cum = np.cumsum(pop_h)
        total, P = cum[-1], int(m.sum())
        for k in (10_000, 100_000, 1_000_000, 5_000_000):
            b = int(np.searchsorted(cum, k))  # smallest bin reaching k pairs
            below = cum[b - 1] if b else 0
            hits = int((pb < b).sum()) + (pb == b).sum() * (k - below) / max(pop_h[b], 1)
            rows[f"{label} top {k:,}"] = {"hits": float(hits), "chance": P * k / float(total)}
    out[tag] = rows
for k in out["A"]:
    a, b = out["A"][k], out["B"][k]
    print(f"{k:<28} A {a['hits']:>7.1f}  B {b['hits']:>7.1f}   chance {a['chance']:.2f}")
Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
Path(sys.argv[1]).write_text(json.dumps(out, indent=2) + "\n")
