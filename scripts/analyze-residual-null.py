#!/usr/bin/env python3
"""The residual subsets have no cluster null. This computes one.

`analyze-forward-independence.py` runs a 5,000-draw degree-preserving cluster
null on the headline result and finds 0.500 +/- 0.017 -- 4.2x wider than the
iid band for 5,200 positives, because 1,633 endpoints carry them and
`Nat.cast_one` alone is in 371. `analyze-forward-residual.py` computes no null
at all, so the "3.4 null standard deviations" quoted for the hard subset
(0.549 on 401 positives) is the iid figure 1/sqrt(12n) = 0.0144.

If the hard subset carries the same clustering the full set does, that 3.4
sigma is nearer 0.8 and "small and real" becomes "small". If it does not --
stripping same-area and high-overlap pairs plausibly strips the hubs -- then
the quoted figure stands. It is asserted either way, and it is the step the
"signal where words give nothing" claim rests on. So: measure it.

Same null as the published one, restricted to each subset. Substitute every
distinct endpoint of that subset's positives with a uniformly drawn corpus
theorem, keep exactly which endpoints pair with which, drop drawn pairs that
are ineligible or fall outside the subset, and score what is left against the
subset's own population. A pair-level permutation null is run beside it, so
the variance inflation the clustering costs is measured rather than assumed.

    scripts/analyze-residual-null.py --draws 5000 --out outputs/corpus-scaling-v1/residual-null.json
"""

from __future__ import annotations

import argparse
import collections
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
SEED = 0


TOPK = (100, 1000, 10000)


def cluster_null(corpus, pos_i, pos_j, subset, pop, draws, rng, chunk=200):
    """Endpoint substitution with the subset's degree structure preserved.

    Also counts how many substituted pairs land in the closest k of the subset,
    which is the null the top-k enrichment table needs and does not have: its
    p-values are Poisson, and Poisson assumes the 401 pairs are 401 independent
    draws. They are 255 theorems, one of them in 58 pairs.
    """
    thresh = np.searchsorted(pop.cum[1:], TOPK, "left")
    endpoints = np.unique(np.concatenate([pos_i, pos_j]))
    slot = {int(e): k for k, e in enumerate(endpoints)}
    ai = np.fromiter((slot[int(x)] for x in pos_i), np.int32, len(pos_i))
    aj = np.fromiter((slot[int(x)] for x in pos_j), np.int32, len(pos_j))

    aucs, kept_n, hits = [], [], []
    for start in range(0, draws, chunk):
        batch = min(chunk, draws - start)
        sub = rng.integers(0, corpus.n, size=(batch, len(endpoints)))
        xi = sub[:, ai].ravel().astype(np.int32)
        xj = sub[:, aj].ravel().astype(np.int32)
        lo, hi = np.minimum(xi, xj), np.maximum(xi, xj)
        feat = fb.pair_features(corpus, lo, hi)
        ok = fb.subset_masks(feat)[subset] & (lo != hi)
        bins = fb.bin_of(feat["angle"])
        for d in range(batch):
            s = slice(d * len(ai), (d + 1) * len(ai))
            sel = ok[s]
            if sel.sum() < 10:
                continue
            # Dedupe: two substituted endpoints can collide onto one pair.
            key = lo[s][sel].astype(np.int64) * corpus.n + hi[s][sel]
            uniq = np.unique(key, return_index=True)[1]
            b = bins[s][sel][uniq]
            aucs.append(pop.auc(b))
            kept_n.append(len(b))
            hits.append([int((b < t).sum()) for t in thresh])
    return (np.array(aucs), np.array(kept_n), np.array(hits).reshape(-1, len(TOPK)), len(endpoints))


def permutation_null(corpus, pos_i, pos_j, subset, pop, draws, rng, chunk=200):
    """Relabel which of the subset's own endpoints sits at each slot in the wiring.

    The substitution null draws replacements from the whole corpus, so most
    drawn pairs leave the subset -- only ~90 of 401 survive in the hard one --
    and the inflation factor has to be measured at the wrong size and carried
    across. Permuting the subset's own 255 endpoints among the 255 slots keeps
    the degree structure *and* the endpoint composition, so retention is high
    and no size correction is needed.

    It also asks the sharper question. Substitution asks "are these theorems
    special?"; permutation asks "is this *wiring* right?" -- given exactly these
    theorems and exactly this pattern of who-connects-to-how-many, does the true
    assignment rank better than a random one? That is the forward test's claim.
    """
    endpoints = np.unique(np.concatenate([pos_i, pos_j]))
    slot = {int(e): k for k, e in enumerate(endpoints)}
    ai = np.fromiter((slot[int(x)] for x in pos_i), np.int32, len(pos_i))
    aj = np.fromiter((slot[int(x)] for x in pos_j), np.int32, len(pos_j))
    aucs, kept_n = [], []
    for start in range(0, draws, chunk):
        batch = min(chunk, draws - start)
        perm = np.argsort(rng.random((batch, len(endpoints))), axis=1)
        sub = endpoints[perm]
        xi, xj = sub[:, ai].ravel().astype(np.int32), sub[:, aj].ravel().astype(np.int32)
        lo, hi = np.minimum(xi, xj), np.maximum(xi, xj)
        feat = fb.pair_features(corpus, lo, hi)
        ok = fb.subset_masks(feat)[subset] & (lo != hi)
        bins = fb.bin_of(feat["angle"])
        for d in range(batch):
            sl = slice(d * len(ai), (d + 1) * len(ai))
            keep = ok[sl]
            if keep.sum() < 10:
                continue
            key = lo[sl][keep].astype(np.int64) * corpus.n + hi[sl][keep]
            b = bins[sl][keep][np.unique(key, return_index=True)[1]]
            aucs.append(pop.auc(b))
            kept_n.append(len(b))
    return np.array(aucs), np.array(kept_n)


def iid_null(pop, sizes, rng):
    """Pair-level permutation: for each entry of `sizes`, that many pairs drawn
    uniformly from the same population.

    Sizes matter. A substituted endpoint often carries its pair *out* of the
    subset -- only ~90 of 401 survive in the hard one -- so a cluster draw scores
    an AUC on far fewer pairs than the observed statistic does, and an AUC on
    fewer pairs is noisier for reasons that have nothing to do with clustering.
    Comparing the cluster null against an iid null drawn at the *same* sizes
    separates the two: their ratio is the clustering inflation alone.
    """
    sizes = np.atleast_1d(np.asarray(sizes, dtype=int))
    out = np.empty(len(sizes))
    for d, k in enumerate(sizes):
        b = np.searchsorted(pop.cum[1:], rng.integers(0, pop.total, int(k)), "right")
        out[d] = pop.auc(b.astype(np.int32))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--draws", type=int, default=5000)
    ap.add_argument("--block", type=int, default=256)
    ap.add_argument("--cache", type=Path)
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
        f"({time.time() - t0:.0f}s)"
    )

    if args.cache and args.cache.exists():
        z = np.load(args.cache)
        hist = {k: z[k] for k in fb.SUBSETS}
        print(f"population histograms from {args.cache}")
    else:
        print("walking the upper triangle...", flush=True)
        t = time.time()
        hist = fb.population_histograms(
            corpus,
            np.arange(corpus.n),
            block=args.block,
            log=lambda a, m: (
                (a % 2560 == 0) and print(f"  {a:>6}/{m}  {time.time() - t:>5.0f}s", flush=True)
            ),
        )
        if args.cache:
            args.cache.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(args.cache, **hist)

    feat = fb.pair_features(corpus, corpus.pos_i, corpus.pos_j)
    masks = fb.subset_masks(feat)
    pos_bins = fb.bin_of(feat["angle"])

    print(f"\n{'subset':<28}{'pairs':>14}{'pos':>6}{'AUC':>8}   reference (residual.json)")
    published = {
        "all eligible": (65773320, 5200, 0.7089158665396057),
        "cross-area only": (60352871, 2562, 0.5719212162721994),
        "vocab<5%": (16191305, 640, 0.6103154471071757),
        "cross-area AND vocab<5%": (15218798, 401, 0.5487936877957694),
    }
    rows = {}
    for tag in fb.SUBSETS:
        n = int(hist[tag].sum())
        b = pos_bins[masks[tag]]
        a = fb.auc_from_hist(hist[tag], b)
        pn, pp, pa = published[tag]
        flag = "ok" if (n == pn and len(b) == pp and abs(a - pa) < 5e-4) else "MISMATCH"
        print(f"{tag:<28}{n:>14,}{len(b):>6}{a:>8.4f}   {pn:>12,} {pp:>5} {pa:>7.4f}  {flag}")
        rows[tag] = {"pairs": n, "positives": len(b), "auc": a, "self_check": flag}

    pops = {tag: fb.Population(hist[tag]) for tag in fb.SUBSETS}
    rng = np.random.default_rng(SEED)
    print(
        f"\n{'subset':<28}{'pos':>5}{'ends':>6}{'maxdeg':>7}{'kept':>6}"
        f"{'sd_clus':>9}{'sd_iid@k':>10}{'D':>6}{'sd_corr':>9}"
        f"{'n_eff':>7}{'sigma':>7}{'p':>8}"
        f"{'permKept':>7}{'Dp':>6}{'sdP_corr':>9}{'sigmaP':>7}{'pPerm':>8}"
    )
    for tag in fb.SUBSETS:
        m = masks[tag]
        pi, pj = corpus.pos_i[m], corpus.pos_j[m]
        k = len(pi)
        deg = collections.Counter(np.concatenate([pi, pj]).tolist())
        obs = rows[tag]["auc"]

        pop = pops[tag]
        cl, kept, hits, n_end = cluster_null(
            corpus, pi, pj, tag, pop, args.draws, rng, chunk=max(1, min(500, 250_000 // max(k, 1)))
        )
        # Size-matched iid null: same per-draw pair counts the cluster null kept.
        iid_matched = iid_null(pop, kept, rng)
        iid_obs = iid_null(pop, np.full(min(args.draws, 1000), k), rng)
        sd_c = float(cl.std())
        sd_m, sd_o = float(iid_matched.std()), float(iid_obs.std())
        D = sd_c / sd_m if sd_m else float("nan")  # clustering inflation, size removed
        sd_corr = D * sd_o  # what the cluster null would be at the observed size
        n_eff = 1.0 / (12.0 * sd_corr**2)
        sigma = (obs - float(cl.mean())) / sd_corr
        # Empirical p, taking the null's shape from the draws and its scale from
        # sd_corr, so the size mismatch does not leak into the tail.
        z = (cl - cl.mean()) / sd_c
        p = float((z >= sigma).mean())

        # Second null: permute the subset's own endpoints. Retention is high, so
        # this needs no size correction and is the figure to quote when it and
        # the corrected substitution null disagree.
        pm, pm_kept = permutation_null(
            corpus, pi, pj, tag, pop, args.draws, rng, chunk=max(1, min(500, 250_000 // max(k, 1)))
        )
        sd_p = float(pm.std())
        # The permutation null retains far more than substitution (192 of 401 in
        # the hard subset against 90) but still not all, so it gets the same
        # size correction: its inflation over an iid null at *its* sizes, applied
        # at the observed size.
        sd_pm_matched = float(iid_null(pop, pm_kept, rng).std())
        D_p = sd_p / sd_pm_matched if sd_pm_matched else float("nan")
        sd_p_corr = D_p * sd_o
        sigma_p = (obs - float(pm.mean())) / sd_p_corr if sd_p_corr else float("nan")
        zp = (pm - pm.mean()) / sd_p
        p_perm = float((zp >= sigma_p).mean())
        print(
            f"{tag:<28}{k:>5}{n_end:>6}{max(deg.values()):>7}{int(np.median(kept)):>6}"
            f"{sd_c:>9.4f}{sd_m:>10.4f}{D:>6.2f}{sd_corr:>9.4f}"
            f"{n_eff:>7.0f}{sigma:>7.1f}{p:>8.4f}"
            f"{int(np.median(pm_kept)):>7}{D_p:>6.2f}{sd_p_corr:>9.4f}{sigma_p:>7.1f}"
            f"{p_perm:>8.4f}"
        )
        obs_bins = pos_bins[m]
        thresh = np.searchsorted(pop.cum[1:], TOPK, "left")
        topk = {}
        for c, (kk, t) in enumerate(zip(TOPK, thresh, strict=True)):
            if kk > pop.total:
                continue
            observed_hits = int((obs_bins < t).sum())
            # Null draws keep fewer pairs than the observed k (a substituted pair
            # often leaves the subset), so scale each draw's hit count to the
            # observed positive count before comparing. Coarse, but it is a
            # measurement of the clustering rather than an assumption about it.
            scaled = hits[:, c] * (k / np.maximum(kept, 1))
            topk[str(kk)] = {
                "observed": observed_hits,
                "poisson_expected": float(k * kk / pop.total),
                "cluster_null_mean": float(scaled.mean()),
                "cluster_null_p": float((scaled >= observed_hits).mean()),
            }
        rows[tag] |= {
            "top_k": topk,
            "endpoints": n_end,
            "max_endpoint_degree": max(deg.values()),
            "cluster_null": {
                "draws": len(cl),
                "mean": float(cl.mean()),
                "sd": sd_c,
                "median_pairs_kept": float(np.median(kept)) if len(kept) else 0.0,
                "p": p,
                "sigma": float(sigma),
                "sd_raw_size_mismatched": sd_c,
            },
            "iid_null_size_matched": {"sd": sd_m, "median_size": float(np.median(kept))},
            "iid_null_at_observed_size": {"sd": sd_o, "size": k},
            "permutation_null": {
                "draws": len(pm),
                "mean": float(pm.mean()),
                "sd_raw": sd_p,
                "inflation_D": float(D_p),
                "sd_corrected": float(sd_p_corr),
                "median_pairs_kept": float(np.median(pm_kept)) if len(pm_kept) else 0.0,
                "sigma": float(sigma_p),
                "p": p_perm,
            },
            "clustering_inflation_D": float(D),
            "sd_corrected": float(sd_corr),
            "effective_n": float(n_eff),
        }

    print(
        f"\n{'subset':<28}{'k':>8}{'obs':>5}{'Poisson exp':>13}{'Poisson p':>11}"
        f"{'cluster exp':>13}{'cluster p':>11}"
    )
    from scipy.stats import poisson  # sf, not a factorial sum: 195 hits overflows float

    for tag in fb.SUBSETS:
        for kk, e in rows[tag].get("top_k", {}).items():
            lam = e["poisson_expected"]
            pp = float(poisson.sf(e["observed"] - 1, lam)) if e["observed"] else 1.0
            e["poisson_p"] = pp
            print(
                f"{tag:<28}{int(kk):>8,}{e['observed']:>5}{lam:>13.3f}{pp:>11.2e}"
                f"{e['cluster_null_mean']:>13.3f}{e['cluster_null_p']:>11.4f}"
            )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps({"seed": SEED, "draws": args.draws, "subsets": rows}, indent=2) + "\n"
        )
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
