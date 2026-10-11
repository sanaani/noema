#!/usr/bin/env python3
"""analyze-phase28.py -- Phase 28's tests of a fine-tuned arm against B.

Everything is fixed in results/phase-28-far-pair-proof-states/README.md.

    compare     H1: arm minus B on the hard subset, kind-aware (and plain), all
                2,284 positives; R1 the same on fresh pairs; G1 the same on
                all eligible positives. 2,000-draw pigeonhole endpoint
                bootstrap, phase 4's procedure.
    popularity  reported: AUC with each hard-subset positive compared only to
                hard-subset negatives whose two ends sit in the same 2024
                popularity deciles (how many 2024 theorems use each end)

H2 (the arm against the cluster null) and the cells come from
scripts/analyze-phase3.py run on the arm's centroids.

    scripts/analyze-phase28.py compare --a B/centroids.npz --a-hist hist-b.npz \\
        --b ARM/centroids.npz --b-hist hist-arm.npz --union U --out compare.json
    scripts/analyze-phase28.py popularity --a B/centroids.npz --b ARM/centroids.npz \\
        --union U --out popularity.json
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forward_blocks as fb  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261018
BOOT = 2000
HARD = "cross-area AND vocab<5%"
ALL = "all eligible"
WIN = 0.03  # H1's threshold
GUARD = -0.02  # G1's
DECILES = 10
NEG_PER_CELL = 2000
DRAWS_PER_CELL = 40_000


def _load(stem: str, path: str):
    spec = importlib.util.spec_from_file_location(stem, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


a3 = _load("a3", "scripts/analyze-phase3.py")
a4 = _load("a4", "scripts/analyze-phase4.py")


def boot_weights(pi, pj, rng):
    ends = np.unique(np.concatenate([pi, pj]))
    slot = np.searchsorted(ends, np.stack([pi, pj]))
    mults = rng.multinomial(len(ends), np.full(len(ends), 1 / len(ends)), size=BOOT)
    return mults[:, slot[0]] * mults[:, slot[1]], len(ends)


def paired(ua, ub, w) -> dict:
    diffs = ((ub - ua)[None] * w).sum(1) / np.maximum(w.sum(1), 1)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {"auc_B": float(ua.mean()), "auc_arm": float(ub.mean()),
            "difference": float(ub.mean() - ua.mean()), "ci95": [float(lo), float(hi)]}  # fmt: skip


def h1_verdict(d: float, lo: float, hi: float) -> str:
    if d >= WIN and lo > 0:
        return "far-pair training helps"
    if lo > 0:
        return "real but small gain"
    if hi < WIN:
        return "no useful gain"
    return "inconclusive"


def compare(args) -> int:
    ca, fa = a4.side(args, args.a)
    cb, fbt = a4.side(args, args.b)
    for key in ("pos_i", "pos_j"):
        if not np.array_equal(getattr(ca, key), getattr(cb, key)):
            raise SystemExit("B and the arm disagree on the positives; the corpora differ")
    masks = fb.subset_masks(fa)
    if not all(np.array_equal(masks[k], fb.subset_masks(fbt)[k]) for k in (HARD, ALL)):
        raise SystemExit("B and the arm disagree on a subset")
    Ha, Hb = np.load(args.a_hist)["H"], np.load(args.b_hist)["H"]
    kind, fresh = fa["kind"], fa["fresh"]
    rng = np.random.default_rng(SEED)
    report = {"seed": SEED, "boot": BOOT}

    def placements(H, feat, s, sel, fresh_only, kind_aware):
        f = 1 if fresh_only else slice(None)
        bins = fb.bin_of(feat["angle"])[sel]
        if kind_aware:
            hk = [H[s][q][f] if fresh_only else H[s][q].sum(axis=0) for q in range(3)]
            pct = a3.Percentile(hk)
            return a3.placements(pct.pop, pct.bins(kind[sel], bins))
        h = H[s][:, 1].sum(axis=0) if fresh_only else H[s].sum(axis=(0, 1))
        return a3.placements(fb.Population(h), bins)

    for name, subset, fresh_only in (("H1", HARD, False), ("R1", HARD, True), ("G1", ALL, False)):
        s = a3.SUBS.index(subset)
        sel = masks[subset] & fresh if fresh_only else masks[subset]
        w, n_ends = boot_weights(ca.pos_i[sel], ca.pos_j[sel], rng)
        row = {"subset": subset, "positives": int(sel.sum()), "endpoints": n_ends}
        for label, ka in (("kind_aware", True), ("plain", False)):
            ua = placements(Ha, fa, s, sel, fresh_only, ka)
            ub = placements(Hb, fbt, s, sel, fresh_only, ka)
            row[label] = paired(ua, ub, w)
            r = row[label]
            print(f"{name} [{label}] B {r['auc_B']:.4f}  arm {r['auc_arm']:.4f}  "
                  f"diff {r['difference']:+.4f} [{r['ci95'][0]:+.4f}, {r['ci95'][1]:+.4f}]"
                  f"  ({row['positives']} positives)")  # fmt: skip
        report[name] = row
    k = report["H1"]["kind_aware"]
    report["H1"]["verdict"] = h1_verdict(k["difference"], *k["ci95"])
    g = report["G1"]["kind_aware"]
    report["G1"]["cost_to_near_pairs"] = bool(g["difference"] < GUARD and g["ci95"][1] < 0)
    print(f"H1: {report['H1']['verdict']}; G1 cost: {report['G1']['cost_to_near_pairs']}")
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    return 0


def popularity_deciles(names: list[str]) -> np.ndarray:
    uses: collections.Counter[str] = collections.Counter()
    for line in gzip.open(a3.EDGES, "rt"):
        uses.update(set(json.loads(line).get("deps") or []))
    pop = np.array([uses[n] for n in names], dtype=np.float64)
    # mid-rank percentile, so tied counts (many zeros) share one decile
    order = np.argsort(pop, kind="stable")
    ranks = np.empty(len(pop))
    ranks[order] = np.arange(len(pop))
    _, inv = np.unique(pop, return_inverse=True)
    mid = np.bincount(inv, weights=ranks) / np.bincount(inv)
    return np.minimum((mid[inv] / len(pop) * DECILES).astype(int), DECILES - 1)


def popularity(args) -> int:
    ca, fa = a4.side(args, args.a)
    cb = fb.load_corpus(args.b, args.union / "new-connectors.json",
                        args.union / "states-union.jsonl.gz",
                        args.union / "selection-modules.json.gz", a3.EDGES)  # fmt: skip
    if ca.names != cb.names:
        raise SystemExit("B and the arm list different theorems")
    hard = fb.subset_masks(fa)[HARD]
    pi, pj = ca.pos_i[hard], ca.pos_j[hard]
    dec = popularity_deciles(ca.names)
    positives = set(zip(ca.pos_i.tolist(), ca.pos_j.tolist(), strict=True))
    cell = np.minimum(dec[pi], dec[pj]) * DECILES + np.maximum(dec[pi], dec[pj])
    members = [np.flatnonzero(dec == d) for d in range(DECILES)]
    rng = np.random.default_rng(SEED)
    neg = {}
    for c in np.unique(cell):
        lo, hi = divmod(int(c), DECILES)
        i = rng.choice(members[lo], DRAWS_PER_CELL)
        j = rng.choice(members[hi], DRAWS_PER_CELL)
        i, j = np.minimum(i, j), np.maximum(i, j)
        keep = i != j
        i, j = i[keep], j[keep]
        f = fb.pair_features(ca, i, j)
        ok = f["eligible"] & f["cross"] & f["low"]
        ok &= np.array(
            [(a, b) not in positives for a, b in zip(i.tolist(), j.tolist(), strict=True)]
        )
        neg[int(c)] = (i[ok][:NEG_PER_CELL], j[ok][:NEG_PER_CELL])

    def placements(corpus):
        out = np.empty(len(pi))
        ang = fb.angles(corpus.C, pi, pj)
        for c, (ni, nj) in neg.items():
            sel = cell == c
            na = np.sort(fb.angles(corpus.C, ni, nj))
            a = ang[sel]
            below = len(na) - np.searchsorted(na, a, "right")  # negatives farther away
            ties = np.searchsorted(na, a, "right") - np.searchsorted(na, a, "left")
            out[sel] = (below + 0.5 * ties) / max(len(na), 1)
        return out

    ua, ub = placements(ca), placements(cb)
    w, n_ends = boot_weights(pi, pj, rng)
    report = {"seed": SEED, "positives": len(pi), "endpoints": n_ends,
              "cells": len(neg), "negatives": int(sum(len(v[0]) for v in neg.values())),
              "negatives_min_per_cell": int(min(len(v[0]) for v in neg.values())),
              **paired(ua, ub, w)}  # fmt: skip
    print(json.dumps(report, indent=1))
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("compare")
    for k in ("a", "a-hist", "b", "b-hist", "union", "out"):
        m.add_argument(f"--{k}", type=Path, required=True)
    p = sub.add_parser("popularity")
    for k in ("a", "b", "union", "out"):
        p.add_argument(f"--{k}", type=Path, required=True)
    args = ap.parse_args()
    return compare(args) if args.cmd == "compare" else popularity(args)


if __name__ == "__main__":
    sys.exit(main())
