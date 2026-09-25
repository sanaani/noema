#!/usr/bin/env python3
"""calibrate-phase3.py -- does phase 2's angle curve predict the fresh pairs' hits?

Exploratory, run after phase 3's results were read; not pre-registered. Phase 2's
pairs (base-base) give a hit rate per angle band; that rate, times the number of
fresh pairs in each band, predicts the fresh pairs' hits. Reported literally and
rescaled to the fresh total (shape only), with a 1,000-draw endpoint bootstrap
interval on each observed count. Reads the walk's cached histograms.

    scripts/calibrate-phase3.py results/phase-3-doubled-corpus/results/calibration.json
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forward_blocks as fb  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
UNION = ROOT / "outputs/phase-3-doubled-corpus/union"
HIST = ROOT / "outputs/phase-3-doubled-corpus/analysis/hist.npz"
EDGES_DEG = [0, 30, 45, 55, 65, 75, 85, 95, 180]
NB = len(EDGES_DEG) - 1
BOOT = 1000
SUBSETS = ("all eligible", "cross-area AND vocab<5%")

_spec = importlib.util.spec_from_file_location("a3", ROOT / "scripts/analyze-phase3.py")
a3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a3)


def per_band(hist: np.ndarray, eb: list[int]) -> np.ndarray:
    return np.array([hist[eb[k] : eb[k + 1]].sum() for k in range(NB)])


def boot_counts(ii, jj, bands, total, rng) -> np.ndarray:
    """Resample endpoints; a pair counts once per draw of each of its two ends."""
    ends = np.unique(np.concatenate([ii, jj]))
    li, lj = np.searchsorted(ends, ii), np.searchsorted(ends, jj)
    out = np.zeros((BOOT, NB))
    for t in range(BOOT):
        w = np.bincount(rng.integers(0, len(ends), len(ends)), minlength=len(ends))
        m = w[li] * w[lj]
        out[t] = np.bincount(bands, weights=m, minlength=NB)[:NB] * total / max(m.sum(), 1)
    return out


def main() -> int:
    corpus = fb.load_corpus(
        UNION / "centroids.npz",
        UNION / "new-connectors.json",
        UNION / "states-union.jsonl.gz",
        UNION / "selection-modules.json.gz",
        a3.EDGES,
    )
    observed, fresh_add = a3.load_side(UNION / "text-index.jsonl.gz", corpus.names)
    H = np.load(HIST)["H"]
    feat = a3.pair_info(corpus, observed, fresh_add, corpus.pos_i, corpus.pos_j)
    masks = fb.subset_masks(feat)
    pb = fb.bin_of(feat["angle"])
    fresh = feat["fresh"]
    eb = [int(round(e / fb.BINW)) for e in EDGES_DEG]
    rng = np.random.default_rng(a3.SEED)

    def band(b):
        return np.searchsorted(eb, b, side="right") - 1

    out = {}
    for tag in SUBSETS:
        s = fb.SUBSETS.index(tag)
        nb, nf = per_band(H[s][:, 0].sum(0), eb), per_band(H[s][:, 1].sum(0), eb)
        mb, mf = masks[tag] & ~fresh, masks[tag] & fresh
        kb = np.bincount(band(pb[mb]), minlength=NB)[:NB]
        kf = np.bincount(band(pb[mf]), minlength=NB)[:NB]
        rate_b = np.where(nb > 0, kb / np.maximum(nb, 1), 0)
        base_b, base_f = kb.sum() / nb.sum(), kf.sum() / nf.sum()
        pred_abs = nf * rate_b  # the curve taken literally
        pred_shape = pred_abs * kf.sum() / pred_abs.sum()  # its shape, at the fresh total
        boots = boot_counts(corpus.pos_i[mf], corpus.pos_j[mf], band(pb[mf]), kf.sum(), rng)
        lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)

        print(
            f"\n== {tag} ==  base-base: {kb.sum()} hits / {nb.sum():,} pairs;"
            f"  fresh: {kf.sum()} hits / {nf.sum():,} pairs"
        )
        print(f"base rate  base-base 1 in {1 / base_b:,.0f}   fresh 1 in {1 / base_f:,.0f}")
        print(
            f"{'band':>8}{'lift(p2)':>10}{'fresh pairs':>14}{'pred(abs)':>11}{'pred(shape)':>12}"
            f"{'observed':>10}{'95% cluster':>16}{'obs/pred':>10}"
        )
        rows = []
        for k in range(NB):
            lift = rate_b[k] / base_b
            r = kf[k] / pred_shape[k] if pred_shape[k] else float("nan")
            ci = f"[{lo[k]:.0f}, {hi[k]:.0f}]"
            print(
                f"{EDGES_DEG[k]:>3}-{EDGES_DEG[k + 1]:<4}{lift:>9.0f}x{nf[k]:>14,}"
                f"{pred_abs[k]:>11.1f}{pred_shape[k]:>12.1f}{kf[k]:>10}{ci:>16}{r:>10.2f}"
            )
            rows.append(
                {
                    "band": f"{EDGES_DEG[k]}-{EDGES_DEG[k + 1]}",
                    "base_pairs": int(nb[k]),
                    "base_hits": int(kb[k]),
                    "lift_base": lift,
                    "fresh_pairs": int(nf[k]),
                    "pred_abs": pred_abs[k],
                    "pred_shape": pred_shape[k],
                    "observed": int(kf[k]),
                    "ci95_cluster": [lo[k], hi[k]],
                }
            )
        print(f"total  predicted(abs) {pred_abs.sum():.0f}  observed {kf.sum()}")
        out[tag] = {
            "rows": rows,
            "pred_abs_total": pred_abs.sum(),
            "observed_total": int(kf.sum()),
        }
    Path(sys.argv[1]).write_text(json.dumps(out, indent=2, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
