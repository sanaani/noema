#!/usr/bin/env python3
"""run-phase21.py -- forecast important jumps, with "far" set by real arrivals.

Everything is fixed in results/phase-21-forecast-real-far/README.md. Span,
co-citation and the verdict table are Phase 20's; the model and bootstrap are
Phase 15's.

    scripts/run-phase21.py --out DIR [--smoke]
        (reads papers.jsonl.gz and refs.jsonl.gz in DIR, writes phase21.json)
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


SEED = 20261011
CUTOFFS = {"train": 2005, "forward": 2011, "live": 2021}
WINDOW = 10
LAST_OUTCOME = 2021  # reference coverage collapses after 2021 (sizing/README.md)
FAR_BITS = 5.84  # Phase 18: start of the top 1% of real arrivals
WIDE_BITS = 4.65  # Phase 19: start of the top 10% of real arrivals
MIN_POS = 100
LANDMARK_PAIRS = [
    ("W116915404", "math.MG", "Zagier, Elliptic Modular Forms -> metric geometry"),
    (
        "W1537136047",
        "math.MG",
        "Diamond-Shurman, A First Course in Modular Forms -> metric geometry",
    ),
    ("W2156858248", "math.CO", "Fisk, interlacing note -> combinatorics"),
]


def forward_population(new_positives, need=MIN_POS):
    """H2 is scored on works new since the training cutoff if they hold enough positives."""
    return "new works" if new_positives >= need else "all works"


def main() -> int:
    import scipy.sparse as sp
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler, normalize

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
            p["refs"], p["openalex"] = [w for w in r["refs"] if w not in p20.DROP], r["openalex"]
    if smoke:
        P = P[::4]
    hold = 1 if smoke else p20.TOOK_HOLD  # the smoke sample is too thin for 5
    log(f"{len(P):,} papers")
    areas = sorted({p["area"] for p in P})
    ai = {a: k for k, a in enumerate(areas)}
    na = len(areas)
    year = np.array([p["year"] for p in P])
    area = np.array([ai[p["area"]] for p in P])
    texts = [p["title"] + ". " + p["abstract"] for p in P]
    title = {o: p["id"] + " " + p["title"] for p in P for o in p["openalex"]}

    # one citation list: (paper, work index)
    works = sorted({w for p in P for w in p["refs"]})
    wi = {w: k for k, w in enumerate(works)}
    cp = np.array([k for k, p in enumerate(P) for _ in p["refs"]])
    cw = np.array([wi[w] for p in P for w in p["refs"]])
    nw = len(works)
    log(f"{nw:,} works, {len(cp):,} citations")

    def build(H):
        """Candidate pairs at cutoff H, their features and (if known) outcomes."""
        hist = year <= H
        m = hist[cp]
        counts = sp.csr_matrix((np.ones(m.sum()), (cw[m], area[cp[m]])), shape=(nw, na)).toarray()
        rec = m & (year[cp] > H - p20.RECENT)
        recent = np.bincount(cw[rec], minlength=nw)
        n_cit = counts.sum(1)
        F = p20.cocitation_matrix(sp.csr_matrix(counts > 0).astype(float))
        keep = np.nonzero(n_cit >= p20.MIN_CITERS)[0]
        S = p20.span_matrix(counts[keep], F)

        hidx = np.nonzero(hist)[0]
        vec = TfidfVectorizer(
            sublinear_tf=True, min_df=1 if smoke else 5, max_df=0.5, stop_words="english"
        )
        X = vec.fit_transform([texts[k] for k in hidx])
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
        Ac = normalize(Ac)
        SIM = Wc @ Ac.T
        asize = np.bincount(area[ra], minlength=na)

        # papers of each area citing the work after H: in the outcome window, or (no full
        # window) in any later year
        full = H + WINDOW <= LAST_OUTCOME
        o = (year[cp] > H) & (kpos[cw] >= 0)
        if full:
            o &= year[cp] <= H + WINDOW
        later = sp.csr_matrix(
            (np.ones(o.sum()), (kpos[cw[o]], area[cp[o]])), shape=(len(keep), na)
        ).toarray()

        cand = counts[keep] == 0
        r, c = np.nonzero(cand)
        feats = np.column_stack(
            [
                np.log1p(n_cit[keep][r]),
                np.log1p(recent[keep][r]),
                np.log1p(asize[c]),
                S[r, c],
                SIM[r, c],
            ]
        )
        home = counts[keep].argmax(1)
        log(f"H={H}: {len(keep):,} works with >= 5 citers, {len(r):,} candidate pairs")
        return {
            "work": keep[r],
            "area": c,
            "X": feats,
            "outcome": later[r, c] if full else None,
            "later": later[r, c],
            "home": home[r],
            "keep": keep,
            "cand": cand,
            "S": S,
        }

    report: dict = {
        "seed": SEED,
        "smoke": smoke,
        "cutoffs": CUTOFFS,
        "far_bits": FAR_BITS,
        "wide_bits": WIDE_BITS,
    }
    D = {k: build(H) for k, H in CUTOFFS.items()}

    pops = {}
    for k, d in D.items():
        far = d["X"][:, 3] >= FAR_BITS
        pops[k] = far
        info = {"candidate_pairs": int(len(far)), "far_pairs": int(far.sum())}
        if d["outcome"] is not None:
            info["far_pairs_crossed_any"] = int((far & (d["outcome"] >= 1)).sum())
            info["important_jumps"] = int((far & (d["outcome"] >= hold)).sum())
        report[f"population_{k}"] = info
        log(f"{k}: {info}")

    def std(X):
        return (X - X.mean(0)) / np.maximum(X.std(0), 1e-12)

    def group(w):
        g = np.unique(w, return_inverse=True)[1]
        return g, int(g.max()) + 1

    rng = np.random.default_rng(SEED)
    boot = 20 if smoke else p11.BOOT

    def evaluate(scores, X, y, w):
        g, ng = group(w)
        r = p15.compare(scores, y, g, ng, boot, rng)
        r["auc_BASE+SIM"] = r.pop("auc_BASE+SHAPE")
        for n, v in r["top"].items():
            v["BASE+SIM"] = v.pop("BASE+SHAPE")
            v["SIM_alone"] = int(y[np.argsort(-X[:, 4], kind="stable")[: int(n)]].sum())
        r["auc_SIM_alone"] = p11.auc(X[:, 4], y)
        r["verdict"] = p20.verdict(r)
        return r

    def cross_validate(d, far):
        X, y = std(d["X"][far]), d["outcome"][far] >= hold
        if y.sum() < 2:
            return None
        g, ng = group(d["work"][far])
        return evaluate(p15.oof_scores(X, y, g, ng, rng), X, y, d["work"][far])

    # H1: cross-validated at 2005
    tr = D["train"]
    report["H1"] = cross_validate(tr, pops["train"])
    log(f"H1: {report['H1']}")

    # models trained on all of the 2005 far population
    Xt, yt = std(tr["X"][pops["train"]]), tr["outcome"][pops["train"]] >= hold
    models = []
    for cols in (slice(0, 4), slice(0, 5)):
        mdl = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
        mdl.fit(Xt[:, cols], yt)
        models.append((cols, mdl))
    report["coefficients_2005"] = dict(
        zip(p20.FEATURES, (float(c) for c in models[1][1][-1].coef_[0]), strict=True)
    )
    log(f"coefficients: {report['coefficients_2005']}")

    def score(X):
        return np.array([mdl.decision_function(X[:, cols]) for cols, mdl in models])

    # H2: forward at 2011, on works new since 2005 if they hold enough positives
    fw = D["forward"]
    fidx = np.nonzero(pops["forward"])[0]
    Xf, yf = std(fw["X"][fidx]), fw["outcome"][fidx] >= hold
    wf = fw["work"][fidx]
    sf = score(Xf)
    new = ~np.isin(wf, tr["keep"])
    chosen = forward_population(int((yf & new).sum()))
    report["H2_population"] = {
        "chosen": chosen,
        "new_works_pairs": int(new.sum()),
        "new_works_important_jumps": int((yf & new).sum()),
        "all_works_pairs": int(len(yf)),
        "all_works_important_jumps": int(yf.sum()),
    }
    log(f"H2 population: {report['H2_population']}")
    subsets = {"new works": new, "all works": np.ones(len(yf), bool)}
    for name, sub in subsets.items():
        key = "H2" if name == chosen else "H2_other_population"
        report[key] = None
        if yf[sub].sum() >= 2:
            report[key] = evaluate(sf[:, sub], Xf[sub], yf[sub], wf[sub]) | {"population": name}
        log(f"{key} ({name}): {report[key]}")

    # a wider far: H1 again at 4.65 bits
    wide = tr["X"][:, 3] >= WIDE_BITS
    report["H1_wide"] = cross_validate(tr, wide)
    log(f"H1 wide: {report['H1_wide']}")

    def row(d, k, s, outcome_key):
        w = works[d["work"][k]]
        return {
            "work": w,
            "work_title_if_arxiv": title.get(w),
            "home_area": areas[d["home"][k]],
            "target_area": areas[d["area"][k]],
            "citers_up_to_cutoff": int(np.expm1(d["X"][k, 0]).round()),
            "span_bits": float(d["X"][k, 3]),
            "similarity": float(d["X"][k, 4]),
            "score": float(s),
            outcome_key: int(d["later"][k]),
        }

    sub = subsets[chosen]
    order = np.argsort(-sf[1][sub], kind="stable")
    report["top_50_2011"] = [
        row(fw, fidx[sub][j], sf[1][sub][j], "papers_2012_2021") for j in order[:50]
    ]

    # landmark check at 2011 (rank among all far pairs)
    rank = np.empty(len(fidx), int)
    rank[np.argsort(-sf[1], kind="stable")] = np.arange(1, len(fidx) + 1)
    lm = []
    for w, a, label in LANDMARK_PAIRS:
        res = {"pair": label}
        if w not in wi or a not in ai:
            res["status"] = "not in data"
        else:
            wk = wi[w]
            kp = np.nonzero(fw["keep"] == wk)[0]
            if not len(kp):
                res["status"] = "fewer than 5 citers by 2011"
            elif not fw["cand"][kp[0], ai[a]]:
                res["status"] = "already connected by 2011"
                res["span_bits"] = float(fw["S"][kp[0], ai[a]])
            else:
                j = np.nonzero((fw["work"] == wk) & (fw["area"] == ai[a]))[0][0]
                res["status"] = "unconnected at 2011"
                res["span_bits"] = float(fw["X"][j, 3])
                res["far"] = bool(pops["forward"][j])
                res["similarity_percentile"] = float((fw["X"][:, 4] < fw["X"][j, 4]).mean())
                res["papers_2012_2021"] = int(fw["outcome"][j])
                if pops["forward"][j]:
                    res["rank_in_far"] = int(rank[np.searchsorted(fidx, j)])
                    res["far_pairs"] = int(len(fidx))
        lm.append(res)
    report["landmark_check_2011"] = lm
    log(f"landmarks: {lm}")

    # forecast list at 2021
    lv = D["live"]
    lidx = np.nonzero(pops["live"])[0]
    sl = score(std(lv["X"][lidx]))[1]
    order = np.argsort(-sl, kind="stable")
    report["forecast_top_50_2021"] = [row(lv, lidx[j], sl[j], "papers_2022_on") for j in order[:50]]
    crossed = lv["later"][lidx] >= 1
    report["forecast_early_look"] = {
        "top_50_crossed": float(crossed[order[:50]].mean()),
        "top_1000_crossed": float(crossed[order[:1000]].mean()),
        "all_far_crossed": float(crossed.mean()),
    }
    log(f"early look: {report['forecast_early_look']}")
    (out / "phase21.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase21.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
