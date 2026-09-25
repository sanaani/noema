#!/usr/bin/env python3
"""analyze-phase3.py -- the pre-registered phase 3 tests, in one pass over the triangle.

Every test is fixed in results/phase-3-doubled-corpus/README.md, written before
the capture. This script computes exactly those and nothing else:

    H1  pooled angle AUC on the hard subset (cross-area AND vocabulary < 5%),
        against the size-corrected cluster null, both designs; smaller z quoted
    R1  H1 on fresh pairs only -- at least one endpoint from the new draw
    H2  the same subset ranked by each pair's angle percentile within its pair
        kind (observed-observed, observed-synthetic, synthetic-synthetic)
    H3  on observed-observed pairs, proof-state centroid angle vs statement
        vector angle, same pairs, 2,000-draw pigeonhole endpoint bootstrap

plus the reported-not-tested rows: full-set AUC, the four subsets by kind and
by origin, and top-k enrichment with a cluster-null p.

The walk is forward_blocks.py's -- histograms of angle per stratum, so rank
statistics are exact to a 0.0005 degree bin -- extended with two stratifiers
(pair kind, fresh or not) and a second angle for observed-observed pairs.
`--self-check` runs it on phase 2's corpus with every theorem marked "base"
and compares the four subsets against residual.json.

    scripts/analyze-phase3.py --centroids ... --statements ... --index ... \\
        --connectors ... --states ... --selection ... --out phase3.json
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forward_blocks as fb  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EDGES = ROOT / "results/phase-1-recognition/link-graph-v1/edges.jsonl.gz"
SEED = 20260925
KINDS = ("OO", "OS", "SS")
SUBS = fb.SUBSETS
HARD = "cross-area AND vocab<5%"
TOPK = (100, 1000, 10000)
PBINS = 1_000_000  # percentile bins for H2


def load_side(index: Path, names: list[str]):
    """Per theorem: observed (1) or synthetic (0), and from the new draw (1) or not."""
    obs, add = {}, {}
    with gzip.open(index, "rt") as f:
        for line in f:
            r = json.loads(line)
            n = r["theorem_id"].split(":", 1)[1]
            obs[n] = r["object_kind"] == "observed"
            add[n] = r.get("origin", "base") == "add"
    return (
        np.array([obs[n] for n in names], dtype=bool),
        np.array([add[n] for n in names], dtype=bool),
    )


def load_statements(path: Path | None, names: list[str], observed: np.ndarray):
    """Statement vectors aligned to the corpus rows; zero rows where there is none."""
    S = np.zeros((len(names), 1), dtype=np.float32)
    have = np.zeros(len(names), dtype=bool)
    if path is None:
        return S, have
    z = np.load(path, allow_pickle=False)
    at = {str(n): i for i, n in enumerate(z["names"])}
    V = z["vectors"].astype(np.float32)
    S = np.zeros((len(names), V.shape[1]), dtype=np.float32)
    for r, n in enumerate(names):
        if n in at:
            v = V[at[n]]
            S[r] = v / np.linalg.norm(v)
            have[r] = True
    missing = int((observed & ~have).sum())
    if missing:
        raise SystemExit(f"{missing} observed theorems have no statement vector")
    return S, have


def kind_of(obs_i, obs_j):
    """0 = OO, 1 = OS, 2 = SS."""
    return 2 - (obs_i.astype(np.int8) + obs_j.astype(np.int8))


def walk(corpus, observed, fresh_add, S, have_stmt, block, log):
    """Angle histograms per (subset, kind, fresh), and statement-angle histograms
    for observed-observed pairs per (subset, fresh)."""
    m = corpus.n
    C, area, vsize = corpus.C, corpus.area, corpus.vsize
    V, R = corpus.vocab, corpus.rare
    Vt, Rt = V.T.tocsc(), R.T.tocsc()
    H = np.zeros((len(SUBS), 3, 2, fb.NBINS), dtype=np.int64)
    HS = np.zeros((len(SUBS), 2, fb.NBINS), dtype=np.int64)
    col = np.arange(m, dtype=np.int32)
    for a0 in range(0, m, block):
        a1 = min(a0 + block, m)
        rows = np.arange(a0, a1, dtype=np.int32)
        ang = np.degrees(np.arccos(np.clip(C[a0:a1] @ C.T, -1.0, 1.0)))
        keep = col[None, :] > rows[:, None]
        keep &= np.asarray((R[a0:a1] @ Rt).todense()) == 0
        inter = np.asarray((V[a0:a1] @ Vt).todense(), dtype=np.float32)
        union = vsize[a0:a1, None] + vsize[None, :] - inter
        np.divide(inter, np.maximum(union, 1e-9), out=inter)
        low = inter < 0.05
        cross = area[a0:a1, None] != area[None, :]
        kind = kind_of(observed[a0:a1, None], observed[None, :])
        fresh = (fresh_add[a0:a1, None] | fresh_add[None, :]).astype(np.int8)
        idx = fb.bin_of(ang)
        sub_masks = (keep, keep & cross, keep & low, keep & cross & low)
        # One bincount per (subset) over a combined (kind, fresh, bin) key.
        key = (kind.astype(np.int64) * 2 + fresh) * fb.NBINS + idx
        for s, mask in enumerate(sub_masks):
            H[s] += np.bincount(key[mask], minlength=6 * fb.NBINS).reshape(3, 2, fb.NBINS)
        if have_stmt.any():
            oo = kind == 0
            sang = np.degrees(np.arccos(np.clip(S[a0:a1] @ S.T, -1.0, 1.0)))
            skey = fresh.astype(np.int64) * fb.NBINS + fb.bin_of(sang)
            for s, mask in enumerate(sub_masks):
                sel = mask & oo
                HS[s] += np.bincount(skey[sel], minlength=2 * fb.NBINS).reshape(2, fb.NBINS)
        if log:
            log(a1, m)
    return H, HS


def pair_info(corpus, observed, fresh_add, lo, hi):
    feat = fb.pair_features(corpus, lo, hi)
    feat["kind"] = kind_of(observed[lo], observed[hi])
    feat["fresh"] = fresh_add[lo] | fresh_add[hi]
    return feat


def placements(pop: fb.Population, bins: np.ndarray) -> np.ndarray:
    """Per positive: fraction of negatives ranked below it (smaller score = closer),
    ties half. The AUC is their mean, which is what the bootstrap resamples."""
    k = len(bins)
    n_neg = pop.total - k
    order = np.sort(bins)
    pb = np.searchsorted(order, bins, "left")
    pt = np.searchsorted(order, bins, "right") - pb
    nb = pop.cum[bins] - pb
    nt = pop.hist[bins] - pt
    return (n_neg - nb - nt + 0.5 * nt) / n_neg


class Percentile:
    """H2's score: a pair's angle as a mid-rank percentile within its kind's population
    in the same subset, pooled over kinds on a PBINS-bin grid."""

    def __init__(self, kind_hists):
        self.F = []
        pooled = np.zeros(PBINS, dtype=np.int64)
        for h in kind_hists:
            h = np.asarray(h, dtype=np.int64)
            n = max(int(h.sum()), 1)
            cum = np.concatenate(([0], np.cumsum(h)))[:-1]
            F = (cum + 0.5 * h) / n
            fbins = np.minimum((F * PBINS).astype(np.int64), PBINS - 1)
            self.F.append(fbins)
            pooled += np.bincount(fbins, weights=h, minlength=PBINS).astype(np.int64)
        self.pop = fb.Population(pooled)

    def bins(self, kind, angle_bins):
        out = np.empty(len(kind), dtype=np.int64)
        for k in range(3):
            sel = kind == k
            out[sel] = self.F[k][angle_bins[sel]]
        return out


def null_z(corpus, observed, fresh_add, pi, pj, in_set, to_bins, pop, obs, draws, rng):
    """Both published cluster nulls for one statistic, size-corrected as in
    analyze-residual-null.py. Returns the two z and the substitution top-k hits.

    in_set(feat) selects the pairs of the tested population; to_bins(feat) maps
    them to the score's bins in `pop`.
    """
    k = len(pi)
    thresh = np.searchsorted(pop.cum[1:], TOPK, "left")
    endpoints = np.unique(np.concatenate([pi, pj]))
    slot = {int(e): s for s, e in enumerate(endpoints)}
    ai = np.fromiter((slot[int(x)] for x in pi), np.int32, k)
    aj = np.fromiter((slot[int(x)] for x in pj), np.int32, k)
    chunk = max(1, min(500, 250_000 // max(k, 1)))

    def run(draw_fn):
        aucs, kept, hits = [], [], []
        for start in range(0, draws, chunk):
            batch = min(chunk, draws - start)
            sub = draw_fn(batch)
            xi, xj = sub[:, ai].ravel().astype(np.int32), sub[:, aj].ravel().astype(np.int32)
            lo, hi = np.minimum(xi, xj), np.maximum(xi, xj)
            feat = pair_info(corpus, observed, fresh_add, lo, hi)
            ok = in_set(feat) & (lo != hi)
            b_all = to_bins(feat)
            for d in range(batch):
                s = slice(d * k, (d + 1) * k)
                sel = ok[s]
                if sel.sum() < 10:
                    continue
                key = lo[s][sel].astype(np.int64) * corpus.n + hi[s][sel]
                b = b_all[s][sel][np.unique(key, return_index=True)[1]]
                aucs.append(pop.auc(b))
                kept.append(len(b))
                hits.append([int((b < t).sum()) for t in thresh])
        return np.array(aucs), np.array(kept), np.array(hits).reshape(-1, len(TOPK))

    def iid(sizes):
        out = np.empty(len(sizes))
        for d, n in enumerate(sizes):
            b = np.searchsorted(pop.cum[1:], rng.integers(0, pop.total, int(n)), "right")
            out[d] = pop.auc(b.astype(np.int64))
        return out

    sd_obs = float(iid(np.full(min(draws, 1000), k)).std())
    out = {"positives": k, "endpoints": len(endpoints), "iid_sd_at_observed_size": sd_obs}
    for name, fn in (
        ("substitution", lambda b: rng.integers(0, corpus.n, size=(b, len(endpoints)))),
        (
            "permutation",
            lambda b: endpoints[np.argsort(rng.random((b, len(endpoints))), axis=1)],
        ),
    ):
        a, kept, hits = run(fn)
        sd_raw = float(a.std())
        sd_matched = float(iid(kept).std())
        D = sd_raw / sd_matched if sd_matched else float("nan")
        sd = D * sd_obs
        z = (obs - float(a.mean())) / sd if sd else float("nan")
        zs = (a - a.mean()) / sd_raw
        out[name] = {
            "draws": len(a),
            "mean": float(a.mean()),
            "sd_raw": sd_raw,
            "median_kept": float(np.median(kept)),
            "inflation_D": D,
            "sd_corrected": sd,
            "z": z,
            "p": float((zs >= z).mean()),
        }
        if name == "substitution":
            out["_hits"], out["_kept"] = hits, kept
    out["z_quoted"] = min(out["substitution"]["z"], out["permutation"]["z"])
    return out


def verdict_h1(z):
    return "supported" if z >= 3.0 else ("inconclusive" if z >= 2.0 else "not supported")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--centroids", type=Path, required=True)
    ap.add_argument("--statements", type=Path, help="npz names/vectors, observed theorems")
    ap.add_argument("--index", type=Path, required=True, help="text-index with origin")
    ap.add_argument("--connectors", type=Path, required=True)
    ap.add_argument("--states", type=Path, required=True)
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--edges", type=Path, default=EDGES)
    ap.add_argument("--draws", type=int, default=5000)
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--block", type=int, default=256)
    ap.add_argument("--cache", type=Path, help="save/load the walk's histograms")
    ap.add_argument("--self-check", action="store_true", help="compare with residual.json")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    rng = np.random.default_rng(SEED)
    t0 = time.time()

    corpus = fb.load_corpus(
        args.centroids, args.connectors, args.states, args.selection, args.edges
    )
    observed, fresh_add = load_side(args.index, corpus.names)
    S, have_stmt = load_statements(args.statements, corpus.names, observed)
    print(
        f"corpus {corpus.n:,} theorems ({int(fresh_add.sum()):,} new, "
        f"{int(observed.sum()):,} observed), {len(corpus.pos_i):,} eligible positives, "
        f"{time.time() - t0:.0f}s",
        flush=True,
    )

    if args.cache and args.cache.exists():
        z = np.load(args.cache)
        H, HS = z["H"], z["HS"]
        print(f"histograms from {args.cache}")
    else:
        t = time.time()
        H, HS = walk(
            corpus,
            observed,
            fresh_add,
            S,
            have_stmt,
            args.block,
            lambda a, m: (
                (a % 2560 == 0 or a == m)
                and print(f"  walk {a:>6}/{m}  {time.time() - t:>6.0f}s", flush=True)
            ),
        )
        if args.cache:
            args.cache.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(args.cache, H=H, HS=HS)

    feat = pair_info(corpus, observed, fresh_add, corpus.pos_i, corpus.pos_j)
    masks = fb.subset_masks(feat)
    pbins = fb.bin_of(feat["angle"])
    kind, fresh = feat["kind"], feat["fresh"]
    report: dict = {"seed": SEED, "draws": args.draws, "corpus": {}}
    report["corpus"] = {
        "theorems": corpus.n,
        "new": int(fresh_add.sum()),
        "observed": int(observed.sum()),
        "eligible_positives": len(corpus.pos_i),
    }

    # Reported: every subset x kind x origin cell. H is (subset, kind, fresh, bin).
    cells = {}
    print(f"\n{'subset':<26}{'cell':<11}{'pairs':>14}{'pos':>7}{'AUC':>8}")
    for s, tag in enumerate(SUBS):
        rows = [
            ("all", H[s].sum(axis=(0, 1)), masks[tag]),
            ("base-base", H[s][:, 0].sum(axis=0), masks[tag] & ~fresh),
            ("fresh", H[s][:, 1].sum(axis=0), masks[tag] & fresh),
        ] + [(KINDS[q], H[s][q].sum(axis=0), masks[tag] & (kind == q)) for q in range(3)]
        for label, h, pm in rows:
            b = pbins[pm]
            a = fb.auc_from_hist(h, b)
            cells[f"{tag} | {label}"] = {"pairs": int(h.sum()), "positives": len(b), "auc": a}
            print(f"{tag:<26}{label:<11}{int(h.sum()):>14,}{len(b):>7}{a:>8.4f}")
    report["cells"] = cells

    if args.self_check:
        ref = json.loads(
            (
                ROOT / "results/phase-2-dependency-labels/unseeded-corpus-v1/residual.json"
            ).read_text()
        )["subsets"]
        print("\nself-check against residual.json:")
        ok = True
        for tag, r in zip(SUBS, ref, strict=True):
            c = cells[f"{tag} | all"]
            same = (c["pairs"], c["positives"]) == (r["pairs"], r["positives"])
            same &= abs(c["auc"] - r["auc_angle"]) < 5e-4
            ok &= same
            print(
                f"  {tag:<26}{c['auc']:.4f} vs {r['auc_angle']:.4f}  {'ok' if same else 'MISMATCH'}"
            )
        if not ok:
            return 1

    hard = SUBS.index(HARD)
    pop_h1 = fb.Population(H[hard].sum(axis=(0, 1)))
    m_h1 = masks[HARD]

    def in_hard(f):
        return fb.subset_masks(f)[HARD]

    def angle_bins(f):
        return fb.bin_of(f["angle"])

    # H1
    obs_h1 = pop_h1.auc(pbins[m_h1])
    print(
        f"\nH1: hard subset AUC {obs_h1:.4f} on {int(m_h1.sum())} positives; nulls...", flush=True
    )
    h1 = null_z(
        corpus, observed, fresh_add, corpus.pos_i[m_h1], corpus.pos_j[m_h1],
        in_hard, angle_bins, pop_h1, obs_h1, args.draws, rng,
    )  # fmt: skip
    hits, kept = h1.pop("_hits"), h1.pop("_kept")
    thresh = np.searchsorted(pop_h1.cum[1:], TOPK, "left")
    topk = {}
    for c, (kk, tt) in enumerate(zip(TOPK, thresh, strict=True)):
        o = int((pbins[m_h1] < tt).sum())
        scaled = hits[:, c] * (int(m_h1.sum()) / np.maximum(kept, 1))
        topk[str(kk)] = {
            "observed": o,
            "expected_iid": float(m_h1.sum() * kk / pop_h1.total),
            "cluster_null_mean": float(scaled.mean()),
            "cluster_null_p": float((scaled >= o).mean()),
        }
    h1 |= {
        "auc": obs_h1,
        "pairs": pop_h1.total,
        "top_k": topk,
        "verdict": verdict_h1(h1["z_quoted"]),
    }
    report["H1"] = h1
    print(f"H1: z = {h1['z_quoted']:.2f} -> {h1['verdict']}", flush=True)

    # R1 -- needs pairs from the new draw; on phase 2 alone (--self-check) there are none.
    if (masks[HARD] & fresh).sum() >= 10:
        pop_r1 = fb.Population(H[hard][:, 1].sum(axis=0))
        m_r1 = m_h1 & fresh
        obs_r1 = pop_r1.auc(pbins[m_r1])
        r1 = null_z(
            corpus, observed, fresh_add, corpus.pos_i[m_r1], corpus.pos_j[m_r1],
            lambda f: in_hard(f) & f["fresh"], angle_bins, pop_r1, obs_r1, args.draws, rng,
        )  # fmt: skip
        r1.pop("_hits"), r1.pop("_kept")
        r1 |= {"auc": obs_r1, "pairs": pop_r1.total}
        r1["contradicts_h1"] = bool(h1["verdict"] == "supported" and obs_r1 <= 0.5)
        report["R1"] = r1
        print(f"R1: fresh-pair AUC {obs_r1:.4f}, z = {r1['z_quoted']:.2f}", flush=True)

    # H2
    pct = Percentile([H[hard][q].sum(axis=0) for q in range(3)])
    obs_h2 = pct.pop.auc(pct.bins(kind[m_h1], pbins[m_h1]))
    h2 = null_z(
        corpus, observed, fresh_add, corpus.pos_i[m_h1], corpus.pos_j[m_h1],
        in_hard, lambda f: pct.bins(f["kind"], fb.bin_of(f["angle"])), pct.pop, obs_h2,
        args.draws, rng,
    )  # fmt: skip
    h2.pop("_hits"), h2.pop("_kept")
    h2 |= {"auc_kind_percentile": obs_h2, "auc_plain_angle": obs_h1}
    report["H2"] = h2
    print(f"H2: kind-percentile AUC {obs_h2:.4f} vs plain {obs_h1:.4f}", flush=True)

    # H3
    if have_stmt.any():
        report["H3"] = {}
        pi, pj = corpus.pos_i, corpus.pos_j
        sd = np.einsum("ij,ij->i", S[pi], S[pj])
        sbins = fb.bin_of(np.degrees(np.arccos(np.clip(sd, -1.0, 1.0))))
        for tag in ("all eligible", HARD):
            s = SUBS.index(tag)
            m = masks[tag] & (kind == 0)
            pp = fb.Population(H[s][0].sum(axis=0))
            ps = fb.Population(HS[s].sum(axis=0))
            up, us = placements(pp, pbins[m]), placements(ps, sbins[m])
            ends = np.unique(np.concatenate([pi[m], pj[m]]))
            slot = np.searchsorted(ends, np.stack([pi[m], pj[m]]))
            diffs = np.empty(args.boot)
            for d in range(args.boot):
                mult = rng.multinomial(len(ends), np.full(len(ends), 1 / len(ends)))
                w = mult[slot[0]] * mult[slot[1]]
                diffs[d] = ((up - us) * w).sum() / max(w.sum(), 1)
            lo, hi = np.percentile(diffs, [2.5, 97.5])
            diff = float(up.mean() - us.mean())
            v = (
                "trajectory carries more"
                if lo > 0
                else ("statement better" if hi < 0 else "no measurable difference")
            )
            report["H3"][tag] = {
                "pairs": pp.total,
                "positives": int(m.sum()),
                "endpoints": len(ends),
                "auc_proof_states": float(up.mean()),
                "auc_statement": float(us.mean()),
                "difference": diff,
                "ci95": [float(lo), float(hi)],
                "verdict": v,
            }
            print(
                f"H3 [{tag}]: proof {up.mean():.4f} statement {us.mean():.4f} "
                f"diff {diff:+.4f} [{lo:+.4f}, {hi:+.4f}] -> {v}",
                flush=True,
            )

    report["seconds"] = round(time.time() - t0)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
