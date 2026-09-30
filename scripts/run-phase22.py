#!/usr/bin/env python3
"""run-phase22.py -- does similarity forecast the pair, or only the field?

Everything is fixed in results/phase-22-within-route/README.md. Population,
span and similarity are Phase 21's at the 2005 cutoff; the model and folds are
Phase 15's.

    scripts/run-phase22.py --out DIR [--smoke]
        (reads papers.jsonl.gz and refs.jsonl.gz in DIR, writes phase22.json)
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


SEED = 20261012
CUTOFF = 2005
WINDOW = 10
FAR_BITS = 5.84
WIDE_BITS = 4.65
MIN_POS = 100
MIN_STRATA = 10


def strat_auc(score, y, strata, w=None):
    """AUC over (positive, negative) pairs in the same stratum, pooled; ties count half."""
    w = np.ones(len(score)) if w is None else w
    order = np.lexsort((score, strata))
    s, g, yy, ww = score[order], strata[order], y[order], w[order]
    new = np.r_[True, (g[1:] != g[:-1]) | (s[1:] != s[:-1])]
    tid = np.cumsum(new) - 1
    pos, neg = np.bincount(tid, ww * yy), np.bincount(tid, ww * ~yy)
    gt = g[new]
    start = np.r_[True, gt[1:] != gt[:-1]]
    sid = np.cumsum(start) - 1
    before = np.cumsum(neg) - neg
    below = before - before[start][sid]
    den = (np.bincount(sid, pos) * np.bincount(sid, neg)).sum()
    return float((pos * (below + 0.5 * neg)).sum() / den) if den else float("nan")


def usable(y, strata):
    """(strata holding both jumps and non-jumps, jumps in them)."""
    p = np.bincount(strata, y)
    n = np.bincount(strata, ~y)
    ok = (p > 0) & (n > 0)
    return int(ok.sum()), int(p[ok].sum())


def choose_grain(counts, need_pos=MIN_POS, need_strata=MIN_STRATA):
    """First grain in order whose usable strata and jumps both reach the bar."""
    for name, (ns, npos) in counts.items():
        if ns >= need_strata and npos >= need_pos:
            return name
    return None


def verdict(r):
    if r is None:
        return "underpowered"
    lo, hi = r["ci95"]
    if lo > 0:
        return "similarity picks the pair" if r["difference"] >= 0.03 else "detectable, small"
    return "similarity hurts" if hi < 0 else "similarity only picks the field"


def main() -> int:
    import scipy.sparse as sp
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    p20 = load("run-phase20")
    p15 = load("run-phase15")
    p11 = p15.p11
    log = p11.log

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    out, smoke = args.out, args.smoke

    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        P = [json.loads(line) for line in f]
    with gzip.open(out / "refs.jsonl.gz", "rt") as f:
        for p, r in zip(P, map(json.loads, f), strict=True):
            assert p["id"] == r["id"]
            p["refs"] = [w for w in r["refs"] if w not in p20.DROP]
    if smoke:
        P = P[::4]
    hold = 1 if smoke else p20.TOOK_HOLD  # the smoke sample is too thin for 5
    log(f"{len(P):,} papers")
    areas = sorted({p["area"] for p in P})
    na = len(areas)
    ai = {a: k for k, a in enumerate(areas)}
    year = np.array([p["year"] for p in P])
    area = np.array([ai[p["area"]] for p in P])
    works = sorted({w for p in P for w in p["refs"]})
    wi = {w: k for k, w in enumerate(works)}
    cp = np.array([k for k, p in enumerate(P) for _ in p["refs"]])
    cw = np.array([wi[w] for p in P for w in p["refs"]])
    nw = len(works)

    # Phase 21's build at the 2005 cutoff, plus home area and breadth
    H = CUTOFF
    hist = year <= H
    m = hist[cp]
    counts = sp.csr_matrix((np.ones(m.sum()), (cw[m], area[cp[m]])), shape=(nw, na)).toarray()
    recent = np.bincount(cw[m & (year[cp] > H - p20.RECENT)], minlength=nw)
    n_cit = counts.sum(1)
    F = p20.cocitation_matrix(sp.csr_matrix(counts > 0).astype(float))
    keep = np.nonzero(n_cit >= p20.MIN_CITERS)[0]
    S = p20.span_matrix(counts[keep], F)
    hidx = np.nonzero(hist)[0]
    vec = TfidfVectorizer(
        sublinear_tf=True, min_df=1 if smoke else 5, max_df=0.5, stop_words="english"
    )
    X = vec.fit_transform([P[k]["title"] + ". " + P[k]["abstract"] for k in hidx])
    svd = TruncatedSVD(32 if smoke else 256, random_state=SEED)
    V = np.zeros((len(P), svd.n_components), np.float32)
    V[hidx] = normalize(svd.fit_transform(X))
    del X
    kpos = -np.ones(nw, int)
    kpos[keep] = np.arange(len(keep))
    mk = m & (kpos[cw] >= 0)
    inc = sp.csr_matrix((np.ones(mk.sum()), (kpos[cw[mk]], cp[mk])), shape=(len(keep), len(P)))
    Wc = normalize(inc @ V)
    ra = hist & (year > H - p20.RECENT)
    Ac = np.zeros((na, V.shape[1]))
    np.add.at(Ac, area[ra], V[ra])
    SIM = Wc @ normalize(Ac).T
    asize = np.bincount(area[ra], minlength=na)
    o = (year[cp] > H) & (year[cp] <= H + WINDOW) & (kpos[cw] >= 0)
    outc = sp.csr_matrix(
        (np.ones(o.sum()), (kpos[cw[o]], area[cp[o]])), shape=(len(keep), na)
    ).toarray()
    home_of = counts[keep].argmax(1)
    breadth_of = (counts[keep] > 0).sum(1)

    r, c = np.nonzero(counts[keep] == 0)
    span = S[r, c]
    base_num = np.column_stack(
        [
            np.log1p(n_cit[keep][r]),
            np.log1p(recent[keep][r]),
            np.log1p(asize[c]),
            span,
            breadth_of[r],
        ]
    )
    sim = SIM[r, c]
    home, target = home_of[r], c
    y_all = outc[r, c] >= hold
    work = keep[r]
    log(f"H={H}: {len(keep):,} works, {len(r):,} candidate pairs")

    report: dict = {"seed": SEED, "smoke": smoke, "cutoff": H, "far_bits": FAR_BITS}
    rng = np.random.default_rng(SEED)
    boot = 20 if smoke else p11.BOOT

    def std(Z):
        return (Z - Z.mean(0)) / np.maximum(Z.std(0), 1e-12)

    def design(f, breadth=True, dummies=True):
        cols = [base_num[f] if breadth else base_num[f][:, :4]]
        if dummies:
            cols += [np.eye(na)[home[f]], np.eye(na)[target[f]]]
        return np.column_stack(cols + [sim[f]])

    def oof(f, **kw):
        g = np.unique(work[f], return_inverse=True)[1]
        s = p15.oof_scores(std(design(f, **kw)), y_all[f], g, int(g.max()) + 1, rng)
        return s, g

    def boot_diff(s, y, strata, g):
        ng = int(g.max()) + 1
        d = np.empty(boot)
        for b in range(boot):
            w = np.bincount(rng.integers(0, ng, ng), minlength=ng)[g].astype(float)
            d[b] = strat_auc(s[1], y, strata, w) - strat_auc(s[0], y, strata, w)
            if (b + 1) % 100 == 0:
                log(f"  bootstrap {b + 1}/{boot}")
        return [float(x) for x in np.percentile(d, [2.5, 97.5])]

    def result(s, y, strata, g, interval=True):
        a0, a1 = strat_auc(s[0], y, strata), strat_auc(s[1], y, strata)
        res = {
            "auc_BASE": a0,
            "auc_BASE+SIM": a1,
            "difference": a1 - a0,
            "auc_SIM_alone": strat_auc(sim_f, y, strata),
            "positives": int(y.sum()),
            "pairs": int(len(y)),
        }
        if interval:
            res["ci95"] = boot_diff(s, y, strata, g)
        return res

    for label, bits in (("primary", FAR_BITS), ("wide", WIDE_BITS)):
        f = span >= bits
        y = y_all[f]
        strata = {
            "route": home[f] * na + target[f],
            "target area": target[f],
            "none": np.zeros(int(f.sum()), int),
        }
        grain_counts = {k: usable(y, strata[k]) for k in ("route", "target area")}
        grain = choose_grain(grain_counts)
        info = {
            "far_pairs": int(f.sum()),
            "important_jumps": int(y.sum()),
            "usable_strata_and_jumps": {k: list(v) for k, v in grain_counts.items()},
            "grain": grain,
        }
        if label == "primary":
            tp = np.bincount(target[f], y, na)
            tn = np.bincount(target[f], minlength=na)
            info["by_target_area"] = {
                areas[a]: {"far_pairs": int(tn[a]), "important_jumps": int(tp[a])}
                for a in np.argsort(-tp, kind="stable")
                if tn[a]
            }
            rt = np.bincount(strata["route"], y, na * na)
            info["top_routes"] = [
                {
                    "route": f"{areas[k // na]} -> {areas[k % na]}",
                    "important_jumps": int(rt[k]),
                    "far_pairs": int((strata["route"] == k).sum()),
                }
                for k in np.argsort(-rt, kind="stable")[:15]
                if rt[k]
            ]
        log(f"{label}: {info}")
        report[f"population_{label}"] = info
        if grain is None:
            report[f"H1_{label}"] = None
            continue

        sim_f = sim[f]
        s, g = oof(f)
        main_ = result(s, y, strata[grain], g) | {"grain": grain}
        main_["verdict"] = verdict(main_)
        other = "target area" if grain == "route" else "route"
        main_["other_grain"] = result(s, y, strata[other], g, interval=False)
        main_["no_strata"] = result(s, y, strata["none"], g, interval=False)
        main_["top"] = {
            str(n): {
                "BASE": int(y[np.argsort(-s[0], kind="stable")[:n]].sum()),
                "BASE+SIM": int(y[np.argsort(-s[1], kind="stable")[:n]].sum()),
                "chance": n * float(y.mean()),
            }
            for n in (100, 1000)
        }
        if label == "primary":
            s2, _ = oof(f, breadth=False)
            main_["without_breadth"] = result(s2, y, strata[grain], g, interval=False)
            s3, _ = oof(f, dummies=False)
            main_["without_area_indicators"] = result(s3, y, strata[grain], g, interval=False)
        report[f"H1_{label}"] = main_
        log(f"H1 {label}: {main_}")

    (out / "phase22.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase22.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
