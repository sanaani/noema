#!/usr/bin/env python3
"""run-phase18.py -- the longest-reaching citations up to 2015, and which caught on.

Everything is fixed in results/phase-18-citation-span/README.md. The model and
bootstrap are Phase 15's (scripts/run-phase15.py).

    scripts/run-phase18.py --out DIR [--smoke]
        (reads papers.jsonl.gz and refs.jsonl.gz in DIR, writes phase18.json)
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


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SEED = 20261008
CUTOFF = 2015
MIN_PRIOR = 5
TOOK_HOLD = 5
COHORT = (1998, 2002)
COHORT_WATCH = 13
T_QUANTILE = 0.8
TOP = 0.01
MIN_HELD = 100
DIMS = 256
MAX_K = 40
LANDMARKS = {
    "1603.04246": ["W116915404", "W1537136047"],
    "1603.06518": ["W116915404", "W1537136047"],
    "1605.01506": [],
    "1605.09223": ["W2347034157"],
    "1907.00847": ["W2156858248"],
}
EXTRA_REFS = {"1907.00847": ["W2156858248"]}  # Huang: OpenAlex has no references


def cocitation(area_sets, na):
    """F[A, B]: of the works some B-paper cites, the share some A-paper also cites."""
    G = np.zeros((na, na))
    for s in area_sets:
        s = list(s)
        G[np.ix_(s, s)] += 1
    return G / np.maximum(np.diag(G), 1)[None, :]


def span(prior, a, F):
    """Bits of surprise for area a using a work whose prior citers are spread as prior."""
    s = prior / prior.sum()
    return float(-np.log2(max(F[a] @ s, 1e-12)))


def cells_of_work(yrs, ars, min_prior):
    """Eligible arrivals of one work, as (area, year, prior citers, arriving, follow-on years).

    yrs, ars: the work's citers' years and areas, sorted by year. Prior citers are the first
    `prior` of them; arriving are indices into yrs; follow-on years count from the arrival."""
    out = []
    for a in np.unique(ars):
        on = ars == a
        y = int(yrs[on].min())
        pos = int(np.searchsorted(yrs, y, "left"))
        if pos < min_prior:
            continue
        arriving = np.nonzero(on & (yrs == y))[0]
        later = yrs[on & (yrs > y)] - y
        out.append((int(a), y, pos, arriving, later))
    return out


def verdict(r):
    if r["positives"] < MIN_HELD:
        return "underpowered"
    lo, hi = r["ci95"]
    if lo > 0:
        if r["difference"] >= 0.03:
            return "content closeness picks the far routes that catch on"
        return "detectable, small"
    return "content closeness hurts" if hi < 0 else "no measurable help"


def main() -> int:
    from scipy.stats import spearmanr
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

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
            p["refs"], p["openalex"] = r["refs"] + EXTRA_REFS.get(p["id"], []), r["openalex"]
    if smoke:
        keep = set(LANDMARKS)
        P = [p for k, p in enumerate(P) if k % 4 == 0 or p["id"] in keep]
    log(f"{len(P):,} papers")
    areas = sorted({p["area"] for p in P})
    ai = {a: k for k, a in enumerate(areas)}
    na = len(areas)
    year = np.array([p["year"] for p in P])
    area = np.array([ai[p["area"]] for p in P])
    last = int(year.max())
    size = np.zeros((na, last + 1))
    np.add.at(size, (area, year), 1)

    # text model, fitted on papers up to the cutoff
    texts = [p["title"] + ". " + p["abstract"] for p in P]
    vec = TfidfVectorizer(
        sublinear_tf=True, min_df=1 if smoke else 5, max_df=0.5, stop_words="english"
    )
    old = np.nonzero(year <= CUTOFF)[0]
    vec.fit([texts[k] for k in old])
    X = vec.transform(texts)
    del texts
    svd = TruncatedSVD(32 if smoke else DIMS, random_state=SEED)
    svd.fit(X[old])
    V = normalize(svd.transform(X)).astype(np.float32)
    del X
    log(f"text vectors {V.shape}, explained {svd.explained_variance_ratio_.sum():.3f}")

    # citers of each work, in year order
    order = np.argsort(year, kind="stable")
    citers: dict[str, list[int]] = collections.defaultdict(list)
    for k in order:
        for w in P[k]["refs"]:
            citers[w].append(int(k))
    log(f"{len(citers):,} works")

    F = cocitation(({int(area[k]) for k in c if year[k] <= CUTOFF} for c in citers.values()), na)

    # every eligible cell
    rows = collections.defaultdict(list)
    fol = []
    for w, c in citers.items():
        if len(c) <= MIN_PRIOR:
            continue
        c = np.array(c)
        yrs, ars = year[c], area[c]
        cs = None
        for a, y, pos, arr, later in cells_of_work(yrs, ars, MIN_PRIOR):
            if cs is None:
                cs = np.cumsum(V[c], axis=0)
            prior = np.bincount(ars[:pos], minlength=na).astype(float)
            pv, av = cs[pos - 1], V[c[arr]].sum(0)
            sim = float(pv @ av / (np.linalg.norm(pv) * np.linalg.norm(av) + 1e-12))
            rows["work"].append(w)
            rows["area"].append(a)
            rows["year"].append(y)
            rows["prior"].append(pos)
            rows["home"].append(int(prior.argmax()))
            rows["span"].append(span(prior, a, F))
            rows["sim"].append(sim)
            rows["first"].append(int(c[arr[0]]))
            rows["n_arriving"].append(len(arr))
            fol.append(np.bincount(np.minimum(later, MAX_K), minlength=MAX_K + 1)[: MAX_K + 1])
    C = {k: np.array(v) for k, v in rows.items()}
    fol = np.array(fol)
    cum = np.cumsum(fol, axis=1)  # cum[:, k]: follow-on papers in years y+1..y+k
    n = len(C["year"])
    log(f"{n:,} eligible cells")
    report: dict = {"seed": SEED, "smoke": smoke, "papers": len(P), "eligible_cells": n}

    # T from the earliest cohort
    coh = (C["year"] >= COHORT[0]) & (C["year"] <= COHORT[1])
    held13 = coh & (cum[:, COHORT_WATCH] >= TOOK_HOLD)
    tth = np.array([np.searchsorted(cum[i], TOOK_HOLD) for i in np.nonzero(held13)[0]], dtype=int)
    if len(tth):
        T = int(np.ceil(np.quantile(tth, T_QUANTILE)))
    else:
        T = 5
    report["time_window"] = {
        "cohort_cells": int(coh.sum()),
        "caught_on_within_13": int(held13.sum()),
        "years_to_catch_on": {str(k): int((tth == k).sum()) for k in range(1, COHORT_WATCH + 1)},
        "median": float(np.median(tth)) if len(tth) else None,
        "p80": float(np.quantile(tth, 0.8)) if len(tth) else None,
        "p90": float(np.quantile(tth, 0.9)) if len(tth) else None,
        "T": T,
        "note": None if len(tth) else "no cohort cell caught on; T=5 placeholder (smoke only)",
    }
    log(f"time window: {report['time_window']}")
    caught = cum[:, T] >= TOOK_HOLD

    learn = C["year"] <= CUTOFF - T
    thr = float(np.quantile(C["span"][learn], 1 - TOP))
    top = learn & (C["span"] >= thr)
    report["learn_window"] = {
        "arrival_years": [int(C["year"][learn].min()), CUTOFF - T],
        "cells": int(learn.sum()),
        "caught_on": int((learn & caught).sum()),
        "top1_threshold_bits": thr,
        "top1_cells": int(top.sum()),
        "groundbreaking": int((top & caught).sum()),
    }
    log(f"learn window: {report['learn_window']}")

    # H1: citation distance vs content distance
    rho = float(spearmanr(C["span"][learn], C["sim"][learn]).statistic)
    ar = abs(rho)
    report["H1"] = {
        "spearman_span_vs_similarity": rho,
        "verdict": "mostly the same thing"
        if ar >= 0.5
        else "related but different"
        if ar >= 0.2
        else "different things",
    }
    cent = np.zeros((na, V.shape[1]))
    np.add.at(cent, area[year <= CUTOFF], V[year <= CUTOFF])
    cent = normalize(cent)
    iu = np.triu_indices(na, 1)
    sym = (F + F.T) / 2
    report["H1"]["area_level_spearman"] = float(
        spearmanr(-np.log2(np.maximum(sym[iu], 1e-12)), (cent @ cent.T)[iu]).statistic
    )
    log(f"H1: {report['H1']}")

    # reported: catch-on by span decile, hidden bridges
    dec = np.minimum((np.argsort(np.argsort(C["span"][learn])) * 10) // learn.sum(), 9)
    report["catch_on_by_span_decile"] = [
        float(caught[learn][dec == d].mean()) if (dec == d).any() else None for d in range(10)
    ]
    report["catch_on_top1"] = float(caught[top].mean()) if top.any() else None
    med = float(np.median(C["sim"][learn]))
    hid = top & (C["sim"] >= med)
    report["hidden_bridges"] = {
        "median_similarity": med,
        "cells": int(hid.sum()),
        "caught_on_rate": float(caught[hid].mean()) if hid.any() else None,
        "other_top1_rate": float(caught[top & ~hid].mean()) if (top & ~hid).any() else None,
    }
    log(f"hidden bridges: {report['hidden_bridges']}")

    # H2
    works = sorted(set(C["work"].tolist()))
    wi = {w: k for k, w in enumerate(works)}
    tool = np.array([wi[w] for w in C["work"]])
    judged_to = np.minimum(C["year"] + T, last)
    judgeable = C["year"] + T <= last
    pop, which = top, "learn window (no peek)"
    if int((top & caught).sum()) < MIN_HELD:
        peek = (C["year"] <= CUTOFF) & judgeable
        pthr = float(np.quantile(C["span"][peek], 1 - TOP))
        pop, which = peek & (C["span"] >= pthr), "peek (caught-on judged past 2015)"
        report["peek"] = {
            "arrival_years_up_to": int(C["year"][peek].max()),
            "top1_threshold_bits": pthr,
            "top1_cells": int(pop.sum()),
            "caught_on": int((pop & caught).sum()),
            "judged_up_to_year": int(judged_to[pop].max()) if pop.any() else None,
        }
    y = caught[pop]
    base = np.column_stack(
        [
            np.log1p(C["prior"]),
            C["year"],
            np.log1p(size[C["area"], C["year"]]),
            C["span"],
            C["sim"],
        ]
    )[pop]
    report["H2"] = {"population": which, "cells": int(pop.sum()), "caught_on": int(y.sum())}
    if y.sum() >= 2 and (~y).sum() >= 2:
        rng = np.random.default_rng(SEED)
        s = p15.oof_scores(base, y, tool[pop], len(works), rng)
        r = p15.compare(s, y, tool[pop], len(works), 20 if smoke else p11.BOOT, rng)
        r["auc_BASE+CONTENT"] = r.pop("auc_BASE+SHAPE")
        for v in r["top"].values():
            v["BASE+CONTENT"] = v.pop("BASE+SHAPE")
        r["verdict"] = verdict(r)
        r["auc_similarity_alone"] = p11.auc(C["sim"][pop], y)
        report["H2"].update(r)
    log(f"H2: {report['H2']}")

    # the 50 groundbreaking cells with the highest span (H2's population)
    title = {}
    for p in P:
        for o in p["openalex"]:
            title[o] = p["id"] + " " + p["title"]
    gb = np.nonzero(pop & caught)[0]
    gb = gb[np.argsort(-C["span"][gb], kind="stable")][:50]
    report["top_50_groundbreaking"] = [
        {
            "work": C["work"][i],
            "work_title_if_arxiv": title.get(C["work"][i]),
            "home_area": areas[C["home"][i]],
            "target_area": areas[C["area"][i]],
            "year": int(C["year"][i]),
            "prior_citers": int(C["prior"][i]),
            "first_arriving": P[C["first"][i]]["id"] + " " + P[C["first"][i]]["title"],
            "follow_on_within_T": int(cum[i, T]),
            "span_bits": float(C["span"][i]),
            "similarity": float(C["sim"][i]),
        }
        for i in gb
    ]

    # landmarks
    pid = {p["id"]: k for k, p in enumerate(P)}
    lm = {}
    for L, decisive in LANDMARKS.items():
        if L not in pid:
            continue
        k = pid[L]
        yl = int(year[k])
        same_year = np.nonzero(C["year"] == yl)[0]
        seconds = [c for c in P[k]["categories"][1:] if c in ai]
        res = {"year": yl, "areas": {}}
        for label, a in [("primary", int(area[k]))] + [("secondary", ai[c]) for c in seconds[:1]]:
            refs = []
            for w in dict.fromkeys(P[k]["refs"]):
                pr = [q for q in citers.get(w, []) if year[q] < yl]
                if not pr:
                    refs.append({"work": w, "prior_citers": 0})
                    continue
                prior = np.bincount(area[pr], minlength=na).astype(float)
                pv = V[pr].sum(0)
                sim = float(pv @ V[k] / (np.linalg.norm(pv) + 1e-12))
                sp = span(prior, a, F)
                refs.append(
                    {
                        "work": w,
                        "title_if_arxiv": title.get(w),
                        "prior_citers": len(pr),
                        "first_arrival": bool(prior[a] == 0),
                        "home_area": areas[int(prior.argmax())],
                        "span_bits": sp,
                        "similarity": sim,
                        "span_percentile_same_year": float((C["span"][same_year] < sp).mean())
                        if len(same_year)
                        else None,
                        "decisive": w in decisive,
                    }
                )
            scored = sorted(
                (r for r in refs if r["prior_citers"] >= MIN_PRIOR), key=lambda r: -r["span_bits"]
            )
            for rank, r in enumerate(scored, 1):
                r["span_rank"] = rank
            res["areas"][f"{label} {areas[a]}"] = {
                "scored_references": len(scored),
                "references": refs,
            }
        lm[L] = res
    report["landmarks"] = lm
    (out / "phase18.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase18.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
