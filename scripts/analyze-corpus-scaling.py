#!/usr/bin/env python3
"""Does the forward AUC rise with corpus size, or is it flat with tighter error bars?

The hypothesis under test: the unseeded corpus's 0.709 -- and 0.549 in the
regime the project exists for -- reads low because 11,489 theorems is a thin
sample, so a larger corpus would show the randomness fall and the effect grow.

That conflates two quantities. The width of the null band *is* a sample-size
artifact and does shrink. The AUC itself is a population parameter, and the
Mann-Whitney estimator of it is unbiased, so more pairs should narrow the
interval around 0.709 without moving it.

The two are separable without capturing a single new proof. Subsample the
committed corpus down to 1,500 / 2,500 / 4,000 / 6,000 / 8,500 theorems, which
reproduces the N-scaling of both the pair set (N^2) and the positives (N^2),
and score each draw exactly as the published analysis scores the whole. Then:

* AUC flat in N, error bars narrowing  -> the hypothesis is refuted for the
  effect size; more corpus buys significance only.
* AUC trending up in N                 -> extrapolation is justified and the
  larger capture is worth its cost.

A degree-preserving cluster null is run at each size too, so the other half of
the claim -- that the noise floor falls -- is measured rather than argued.

    scripts/analyze-corpus-scaling.py --out outputs/corpus-scaling-v1/corpus-scaling.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forward_blocks as fb  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
U = ROOT / "results/phase-2-dependency-labels/unseeded-corpus-v1"
EDGES = ROOT / "results/phase-1-recognition/link-graph-v1/edges.jsonl.gz"
SEED = 20260922
TRACKED = ("all eligible", "cross-area AND vocab<5%")
PLAN = ((1500, 12), (2500, 12), (4000, 10), (6000, 8), (8500, 5), (None, 1))
# The corpus was drawn as 350 files, not as theorems, and capture cost is per
# file. Growing it means adding files, which adds whole clusters of
# same-file theorems at once. Subsampling theorems breaks that clustering, so
# the module plan is the faithful mirror of how a larger corpus would be built.
MODULE_PLAN = ((45, 12), (75, 12), (120, 10), (175, 8), (250, 5), (None, 1))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--null-draws", type=int, default=400)
    ap.add_argument(
        "--unit",
        choices=("theorem", "module"),
        default="theorem",
        help="subsample theorems uniformly, or whole source files",
    )
    ap.add_argument("--block", type=int, default=256)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    t0 = time.time()
    corpus = fb.load_corpus(
        U / "centroids.npz",
        U / "new-connectors.json",
        U / "states-augmented.jsonl.gz",
        U / "selection-modules.json.gz",
        EDGES,
    )
    print(
        f"corpus: {corpus.n} theorems, {len(corpus.pos_i)} eligible positives "
        f"({time.time() - t0:.0f}s)\n"
    )

    feat_all = fb.pair_features(corpus, corpus.pos_i, corpus.pos_j)
    masks_all = fb.subset_masks(feat_all)
    bins_all = fb.bin_of(feat_all["angle"])

    rng = np.random.default_rng(SEED)
    by_module = None
    if args.unit == "module":
        order = np.argsort(corpus.module, kind="stable")
        bounds = np.flatnonzero(np.r_[True, np.diff(corpus.module[order]) != 0, True])
        spans = zip(bounds[:-1], bounds[1:], strict=True)
        by_module = [order[a:b].astype(np.int32) for a, b in spans]
        print(
            f"{len(by_module)} source files, "
            f"{np.median([len(g) for g in by_module]):.0f} theorems each (median)\n"
        )
    plan = MODULE_PLAN if args.unit == "module" else PLAN
    rows = []
    hdr = f"{'N':>7}{'rep':>5}" + "".join(
        f"{t.split(' AND ')[0][:9]:>11}{'pos':>6}{'nullSD':>8}" for t in TRACKED
    )
    print(hdr)
    print("-" * len(hdr))
    for size, reps in plan:
        for rep in range(reps):
            if by_module is not None:
                pick = (
                    range(len(by_module))
                    if size is None
                    else rng.choice(len(by_module), size, replace=False)
                )
                sel = np.sort(np.concatenate([by_module[g] for g in pick])).astype(np.int32)
                n = len(sel)
            else:
                n = size or corpus.n
                sel = (
                    np.arange(corpus.n, dtype=np.int32)
                    if size is None
                    else np.sort(rng.choice(corpus.n, n, replace=False)).astype(np.int32)
                )
            keep_set = np.zeros(corpus.n, bool)
            keep_set[sel] = True
            inpair = keep_set[corpus.pos_i] & keep_set[corpus.pos_j]

            t = time.time()
            hist = fb.population_histograms(corpus, sel, block=args.block)
            row = {
                "theorems": int(n),
                "unit": args.unit,
                "units_drawn": int(size) if size else None,
                "rep": rep,
                "seconds": round(time.time() - t, 1),
                "subsets": {},
            }
            line = f"{n:>7}{rep:>5}"
            for tag in fb.SUBSETS:
                m = inpair & masks_all[tag]
                pop = fb.Population(hist[tag])
                b = bins_all[m]
                auc = pop.auc(b)
                entry = {"pairs": pop.total, "positives": int(m.sum()), "auc": auc}
                if tag in TRACKED and args.null_draws and int(m.sum()) >= 20:
                    cl = _cluster_null(
                        corpus, corpus.pos_i[m], corpus.pos_j[m], tag, pop, args.null_draws, rng
                    )
                    entry |= {
                        "null_mean": float(cl.mean()),
                        "null_sd": float(cl.std()),
                        "null_draws": int(len(cl)),
                        "sigma": float((auc - cl.mean()) / cl.std()) if cl.std() else None,
                    }
                    line += f"{auc:>11.4f}{int(m.sum()):>6}{cl.std():>8.4f}"
                elif tag in TRACKED:
                    line += f"{auc:>11.4f}{int(m.sum()):>6}{'-':>8}"
                row["subsets"][tag] = entry
            print(line, flush=True)
            rows.append(row)

    print()
    fits = {}
    for tag in fb.SUBSETS:
        x = np.log2([r["theorems"] for r in rows])
        y = np.array([r["subsets"][tag]["auc"] for r in rows])
        ok = np.isfinite(y)
        slope, intercept = np.polyfit(x[ok], y[ok], 1)
        resid = y[ok] - (slope * x[ok] + intercept)
        sx = ((x[ok] - x[ok].mean()) ** 2).sum()
        se = float(np.sqrt((resid**2).sum() / (ok.sum() - 2) / sx))
        fits[tag] = {
            "slope_per_doubling": float(slope),
            "stderr": se,
            "t": float(slope / se) if se else None,
        }
        print(
            f"{tag:<28} AUC per doubling of corpus: {slope:+.4f} +/- {se:.4f} "
            f"(t = {slope / se:+.1f})"
        )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(
                {
                    "seed": SEED,
                    "unit": args.unit,
                    "plan": [[s, r] for s, r in plan],
                    "null_draws": args.null_draws,
                    "rows": rows,
                    "fits": fits,
                },
                indent=2,
            )
            + "\n"
        )
        print(f"\nwrote {args.out}")
    return 0


def _cluster_null(corpus, pos_i, pos_j, subset, pop, draws, rng):
    """Endpoint substitution with degree preserved, restricted to `subset`."""
    endpoints = np.unique(np.concatenate([pos_i, pos_j]))
    slot = {int(e): k for k, e in enumerate(endpoints)}
    ai = np.fromiter((slot[int(x)] for x in pos_i), np.int32, len(pos_i))
    aj = np.fromiter((slot[int(x)] for x in pos_j), np.int32, len(pos_j))
    chunk = max(1, min(500, 250_000 // max(len(ai), 1)))
    aucs = []
    for start in range(0, draws, chunk):
        batch = min(chunk, draws - start)
        sub = rng.integers(0, corpus.n, size=(batch, len(endpoints)))
        xi, xj = sub[:, ai].ravel().astype(np.int32), sub[:, aj].ravel().astype(np.int32)
        lo, hi = np.minimum(xi, xj), np.maximum(xi, xj)
        feat = fb.pair_features(corpus, lo, hi)
        ok = fb.subset_masks(feat)[subset] & (lo != hi)
        bins = fb.bin_of(feat["angle"])
        for d in range(batch):
            s = slice(d * len(ai), (d + 1) * len(ai))
            keep = ok[s]
            if keep.sum() < 10:
                continue
            key = lo[s][keep].astype(np.int64) * corpus.n + hi[s][keep]
            aucs.append(pop.auc(bins[s][keep][np.unique(key, return_index=True)[1]]))
    return np.array(aucs)


if __name__ == "__main__":
    raise SystemExit(main())
