#!/usr/bin/env python3
"""run-phase23.py -- does similarity forecast the surprising jumps?

Everything is fixed in results/phase-23-surprising-jumps/README.md. The build,
model, grain rule and scores are Phase 22's (scripts/run-phase22.py); the
population keeps only pairs that are neither knocking nor next door (the rule
in scripts/phase22-hits.py).

    scripts/run-phase23.py --out DIR [--smoke]
        (reads papers.jsonl.gz and refs.jsonl.gz in DIR, writes phase23.json)
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


p22 = load("run-phase22")
hits = load("phase22-hits")
SEED = 20261013
CUTOFF = p22.CUTOFF
WINDOW = p22.WINDOW
THRESHOLDS = (("primary", 4.65), ("strict", 5.84), ("all", 0.0))
MIN_POS = p22.MIN_POS
TOP = 100
strat_auc, usable, choose_grain = p22.strat_auc, p22.usable, p22.choose_grain


def verdict(r):
    if r is None:
        return "underpowered"
    lo, hi = r["ci95"]
    if lo > 0:
        return (
            "similarity forecasts surprising jumps"
            if r["difference"] >= 0.03
            else "detectable, small"
        )
    return "similarity hurts" if hi < 0 else "no measurable help"


def main() -> int:
    import scipy.sparse as sp
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    p20 = p22.load("run-phase20")
    p15 = p22.load("run-phase15")
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
            p["openalex"] = r["openalex"]
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

    # Phase 22's build, unchanged
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

    # the follow-up's labels: knocking (secondary citers of A), next door (A's nearest areas)
    sr, sc = [], []
    for k in hidx:
        sec = {ai[x] for x in P[k]["categories"][1:] if x in ai} - {area[k]}
        for w in P[k]["refs"]:
            if kpos[wi[w]] >= 0:
                for a in sec:
                    sr.append(kpos[wi[w]])
                    sc.append(a)
    secondary = sp.csr_matrix((np.ones(len(sr)), (sr, sc)), shape=(len(keep), na)).toarray() > 0
    near = np.zeros((na, na), bool)
    for a in range(na):
        near[a, hits.nearest_areas(F, a)] = True
    next_door = (counts[keep] > 0) @ near.T > 0
    title = {o: p["id"] + " " + p["title"] for p in P for o in p["openalex"]}

    r, c = np.nonzero(counts[keep] == 0)
    surprising = ~secondary[r, c] & ~next_door[r, c]
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

    report: dict = {
        "seed": SEED,
        "smoke": smoke,
        "cutoff": H,
        "surprising_pairs": int(surprising.sum()),
    }
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

    for label, bits in THRESHOLDS:
        f = (span >= bits) & surprising
        y = y_all[f]
        strata = {
            "route": home[f] * na + target[f],
            "target area": target[f],
            "none": np.zeros(int(f.sum()), int),
        }
        grain_counts = {k: usable(y, strata[k]) for k in ("route", "target area")}
        grain = choose_grain(grain_counts)
        below_bar = grain is None and label != "primary"
        if below_bar:  # reported anyway, at route grain, and labelled underpowered
            grain = "route"
        info = {
            "span_at_least": bits,
            "pairs": int(f.sum()),
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
        main_["verdict"] = "underpowered" if below_bar else verdict(main_)
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
            idx = np.nonzero(f)[0]
            order = np.argsort(-s[1], kind="stable")[:TOP]
            main_["top_100"] = [
                {
                    "rank": int(q + 1),
                    "work": works[work[idx[j]]],
                    "work_title_if_arxiv": title.get(works[work[idx[j]]]),
                    "route": f"{areas[home[idx[j]]]} -> {areas[target[idx[j]]]}",
                    "citers_up_to_2005": int(n_cit[work[idx[j]]]),
                    "breadth": int(breadth_of[r[idx[j]]]),
                    "span_bits": float(span[idx[j]]),
                    "similarity": float(sim[idx[j]]),
                    "papers_2006_2015": int(outc[r[idx[j]], c[idx[j]]]),
                    "important_jump": bool(y_all[idx[j]]),
                }
                for q, j in enumerate(order)
            ]
        report[f"H1_{label}"] = main_
        log(f"H1 {label}: {main_}")

    (out / "phase23.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase23.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
