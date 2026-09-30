#!/usr/bin/env python3
"""run-phase20.py -- forecast important (far, caught-on) jumps before they happen.

Everything is fixed in results/phase-20-forecast-far-jumps/README.md. Span is
Phase 18's (scripts/run-phase18.py); the model and bootstrap are Phase 15's.

    scripts/run-phase20.py --out DIR [--smoke]
        (reads papers.jsonl.gz and refs.jsonl.gz in DIR, writes phase20.json)
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


SEED = 20261010
CUTOFFS = {"train": 2005, "forward": 2015, "live": 2025}
WINDOW = 10
LAST_FULL = 2025
RECENT = 5
MIN_CITERS = 5
TOOK_HOLD = 5
TIERS = (0.01, 0.05, 0.10)
MIN_POS = 100
DROP = {"W4285719527"}
FEATURES = ["log_citers", "log_recent", "log_area_size", "span", "sim"]
LANDMARK_PAIRS = [
    ("W116915404", "math.MG", "Zagier, Elliptic Modular Forms -> metric geometry"),
    (
        "W1537136047",
        "math.MG",
        "Diamond-Shurman, A First Course in Modular Forms -> metric geometry",
    ),
    ("W2156858248", "math.CO", "Fisk, interlacing note -> combinatorics"),
]


def span_matrix(counts, F):
    """span[w, A] = -log2 sum_B s_w(B) F[A | B], s_w = counts[w] normalised."""
    s = counts / np.maximum(counts.sum(1, keepdims=True), 1)
    return -np.log2(np.maximum(s @ F.T, 1e-12))


def cocitation_matrix(used):
    """F[A, B] from a works x areas 0/1 matrix: share of B's works that A also uses."""
    G = (used.T @ used).astype(float)
    if hasattr(G, "toarray"):
        G = G.toarray()
    return G / np.maximum(np.diag(G), 1)[None, :]


def choose_tier(span_far_pos, tiers=TIERS, need=MIN_POS):
    """Smallest tier whose count of positives reaches need; (tier, underpowered)."""
    for t in tiers:
        if span_far_pos[t] >= need:
            return t, False
    return tiers[-1], True


def verdict(r):
    if r["positives"] < MIN_POS:
        return "underpowered"
    lo, hi = r["ci95"]
    if lo > 0:
        return (
            "similarity forecasts important jumps"
            if r["difference"] >= 0.03
            else "detectable, small"
        )
    return "similarity hurts" if hi < 0 else "no measurable help"


def main() -> int:
    import scipy.sparse as sp
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler, normalize

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
            p["refs"], p["openalex"] = [w for w in r["refs"] if w not in DROP], r["openalex"]
    if smoke:
        P = P[::4]
    hold = 1 if smoke else TOOK_HOLD  # the smoke sample is too thin for 5
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
    log(f"{len(works):,} works, {len(cp):,} citations")

    def build(H):
        """Candidate pairs at cutoff H, their features and (if known) outcomes."""
        hist = year <= H
        m = hist[cp]
        nw = len(works)
        counts = sp.csr_matrix((np.ones(m.sum()), (cw[m], area[cp[m]])), shape=(nw, na)).toarray()
        rec = m & (year[cp] > H - RECENT)
        recent = np.bincount(cw[rec], minlength=nw)
        n_cit = counts.sum(1)
        F = cocitation_matrix(sp.csr_matrix(counts > 0).astype(float))
        keep = np.nonzero(n_cit >= MIN_CITERS)[0]
        S = span_matrix(counts[keep], F)

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
        ra = hist & (year > H - RECENT)
        Ac = np.zeros((na, V.shape[1]))
        np.add.at(Ac, area[ra], V[ra])
        Ac = normalize(Ac)
        SIM = Wc @ Ac.T
        asize = np.bincount(area[ra], minlength=na)

        outc = None
        if H + WINDOW <= LAST_FULL:
            o = (year[cp] > H) & (year[cp] <= H + WINDOW) & (kpos[cw] >= 0)
            outc = sp.csr_matrix(
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
        log(f"H={H}: {len(keep):,} works with >= {MIN_CITERS} citers, {len(r):,} candidate pairs")
        return {
            "work": keep[r],
            "area": c,
            "X": feats,
            "outcome": None if outc is None else outc[r, c],
            "home": home[r],
            "keep": keep,
            "cand": cand,
            "S": S,
        }

    report: dict = {"seed": SEED, "smoke": smoke, "cutoffs": CUTOFFS}
    D = {k: build(H) for k, H in CUTOFFS.items()}

    # the far tier, from counts at 2005
    tr = D["train"]
    pos_all = tr["outcome"] >= hold
    counts_by_tier = {}
    for t in TIERS:
        far = tr["X"][:, 3] >= np.quantile(tr["X"][:, 3], 1 - t)
        counts_by_tier[t] = int((far & pos_all).sum())
    tier, under = choose_tier(counts_by_tier)
    report["tier"] = {
        "counts_2005": {f"{t:.0%}": n for t, n in counts_by_tier.items()},
        "chosen": tier,
        "underpowered": under,
    }
    log(f"tier: {report['tier']}")

    pops = {}
    for k, d in D.items():
        far = d["X"][:, 3] >= np.quantile(d["X"][:, 3], 1 - tier)
        pops[k] = far
        info = {"candidate_pairs": int(len(far)), "far_pairs": int(far.sum())}
        info["span_threshold_bits"] = float(np.quantile(d["X"][:, 3], 1 - tier))
        if d["outcome"] is not None:
            info["important_jumps"] = int((far & (d["outcome"] >= hold)).sum())
            info["far_pairs_crossed_any"] = int((far & (d["outcome"] >= 1)).sum())
        report[f"population_{k}"] = info
        log(f"{k}: {info}")

    def std(X):
        return (X - X.mean(0)) / np.maximum(X.std(0), 1e-12)

    rng = np.random.default_rng(SEED)
    boot = 20 if smoke else p11.BOOT

    # H1: cross-validated at 2005
    f = pops["train"]
    Xt, yt = std(tr["X"][f]), tr["outcome"][f] >= hold
    wt = np.unique(tr["work"][f], return_inverse=True)[1]
    nwt = int(wt.max()) + 1
    if yt.sum() >= 2:
        s = p15.oof_scores(Xt, yt, wt, nwt, rng)
        r = p15.compare(s, yt, wt, nwt, boot, rng)
        r["auc_BASE+SIM"] = r.pop("auc_BASE+SHAPE")
        for v in r["top"].values():
            v["BASE+SIM"] = v.pop("BASE+SHAPE")
            v["SIM_alone"] = None
        for n in (100, 1000):
            r["top"][str(n)]["SIM_alone"] = int(yt[np.argsort(-Xt[:, 4], kind="stable")[:n]].sum())
        r["auc_SIM_alone"] = p11.auc(Xt[:, 4], yt)
        r["verdict"] = verdict(r)
        report["H1"] = r
    log(f"H1: {report.get('H1')}")

    # models trained on all of 2005
    models = []
    for cols in (slice(0, 4), slice(0, 5)):
        mdl = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
        mdl.fit(Xt[:, cols], yt)
        models.append((cols, mdl))

    def score(X):
        return np.array([mdl.decision_function(X[:, cols]) for cols, mdl in models])

    # H2: forward at 2015
    fw = D["forward"]
    f = pops["forward"]
    Xf, yf = std(fw["X"][f]), fw["outcome"][f] >= hold
    wf = np.unique(fw["work"][f], return_inverse=True)[1]
    nwf = int(wf.max()) + 1
    sf = score(Xf)
    if yf.sum() >= 2:
        r = p15.compare(sf, yf, wf, nwf, boot, rng)
        r["auc_BASE+SIM"] = r.pop("auc_BASE+SHAPE")
        for n, v in r["top"].items():
            v["BASE+SIM"] = v.pop("BASE+SHAPE")
            v["SIM_alone"] = int(yf[np.argsort(-Xf[:, 4], kind="stable")[: int(n)]].sum())
        r["auc_SIM_alone"] = p11.auc(Xf[:, 4], yf)
        r["verdict"] = verdict(r)
        report["H2"] = r
    log(f"H2: {report.get('H2')}")

    def row(d, idx, j, s):
        k = idx[j]
        w = works[d["work"][k]]
        out_ = {
            "work": w,
            "work_title_if_arxiv": title.get(w),
            "home_area": areas[d["home"][k]],
            "target_area": areas[d["area"][k]],
            "citers_up_to_cutoff": int(np.expm1(d["X"][k, 0]).round()),
            "span_bits": float(d["X"][k, 3]),
            "similarity": float(d["X"][k, 4]),
            "score": float(s[j]),
        }
        if d["outcome"] is not None:
            out_["outcome_papers"] = int(d["outcome"][k])
        return out_

    idx = np.nonzero(pops["forward"])[0]
    report["top_50_2015"] = [row(fw, idx, j, sf[1]) for j in np.argsort(-sf[1], kind="stable")[:50]]

    # landmark check at 2015
    rank = np.empty(len(idx), int)
    rank[np.argsort(-sf[1], kind="stable")] = np.arange(1, len(idx) + 1)
    lm = []
    for w, a, label in LANDMARK_PAIRS:
        res = {"pair": label}
        if w not in wi or a not in ai:
            res["status"] = "not in data"
        else:
            wk = wi[w]
            kp = np.nonzero(fw["keep"] == wk)[0]
            if not len(kp):
                res["status"] = f"fewer than {MIN_CITERS} citers by 2015"
            elif not fw["cand"][kp[0], ai[a]]:
                res["status"] = "already connected by 2015"
                res["span_bits"] = float(fw["S"][kp[0], ai[a]])
            else:
                j = np.nonzero((fw["work"] == wk) & (fw["area"] == ai[a]))[0][0]
                res["status"] = "unconnected at 2015"
                res["span_bits"] = float(fw["X"][j, 3])
                res["far"] = bool(pops["forward"][j])
                res["outcome_papers"] = int(fw["outcome"][j])
                if pops["forward"][j]:
                    res["rank_in_far"] = int(rank[np.searchsorted(idx, j)])
                    res["far_pairs"] = int(len(idx))
        lm.append(res)
    report["landmark_check_2015"] = lm
    log(f"landmarks: {lm}")

    # live list at 2025
    lv = D["live"]
    idx = np.nonzero(pops["live"])[0]
    sl = score(std(lv["X"][idx]))
    report["live_top_50_2025"] = [
        row(lv, idx, j, sl[1]) for j in np.argsort(-sl[1], kind="stable")[:50]
    ]
    (out / "phase20.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase20.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
