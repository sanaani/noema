#!/usr/bin/env python3
"""phase22-hits.py -- are Phase 22's top hits obvious or surprising?

Everything is fixed in results/phase-22-within-route/hits/README.md. The build,
seed and first out-of-fold scores are Phase 22's (scripts/run-phase22.py),
repeated here unchanged so the top 100 is the list Phase 22 scored.

    scripts/phase22-hits.py --out DIR [--smoke]
        (reads papers.jsonl.gz and refs.jsonl.gz in DIR, writes hits.json)
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


TOP = 100
NEAREST = 3


def nearest_areas(F, a, k=NEAREST):
    """The k areas B != a with the highest co-citation share F[a, B]."""
    row = F[a].astype(float).copy()
    row[a] = -np.inf
    return [int(b) for b in np.argsort(-row, kind="stable")[:k]]


def label(secondary_hit, next_door_hit):
    return "knocking" if secondary_hit else "next door" if next_door_hit else "surprising"


def main() -> int:
    import scipy.sparse as sp
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    p22 = load("run-phase22")
    p20 = p22.load("run-phase20")
    p15 = p22.load("run-phase15")
    log = p15.p11.log

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
    hold = 1 if smoke else p20.TOOK_HOLD
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
    H = p22.CUTOFF
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
    svd = TruncatedSVD(32 if smoke else 256, random_state=p22.SEED)
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
    o = (year[cp] > H) & (year[cp] <= H + p22.WINDOW) & (kpos[cw] >= 0)
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

    # papers up to 2005 that list each area as a secondary category, per work
    sr, sc = [], []
    for k in np.nonzero(hist)[0]:
        sec = {ai[x] for x in P[k]["categories"][1:] if x in ai} - {area[k]}
        for w in P[k]["refs"]:
            if kpos[wi[w]] >= 0:
                for a in sec:
                    sr.append(kpos[wi[w]])
                    sc.append(a)
    secondary = sp.csr_matrix((np.ones(len(sr)), (sr, sc)), shape=(len(keep), na)).toarray()
    near = [nearest_areas(F, a) for a in range(na)]
    title = {o: p["id"] + " " + p["title"] for p in P for o in p["openalex"]}

    # Phase 22's first draw: primary far pairs, out-of-fold BASE+SIM
    rng = np.random.default_rng(p22.SEED)
    f = np.nonzero(span >= p22.FAR_BITS)[0]
    Z = np.column_stack([base_num[f], np.eye(na)[home[f]], np.eye(na)[target[f]], sim[f]])
    Z = (Z - Z.mean(0)) / np.maximum(Z.std(0), 1e-12)
    g = np.unique(work[f], return_inverse=True)[1]
    s = p15.oof_scores(Z, y_all[f], g, int(g.max()) + 1, rng)[1]
    order = f[np.argsort(-s, kind="stable")]
    rank = np.empty(len(r), int)
    rank[order] = np.arange(1, len(order) + 1)

    def describe(j):
        kp, a = r[j], c[j]
        return {
            "work": works[work[j]],
            "work_title_if_arxiv": title.get(works[work[j]]),
            "home_area": areas[home[j]],
            "target_area": areas[a],
            "citers_up_to_2005": int(n_cit[work[j]]),
            "breadth": int(breadth_of[kp]),
            "span_bits": float(span[j]),
            "similarity": float(sim[j]),
            "papers_2006_2015": int(outc[kp, a]),
            "rank": int(rank[j]),
            "secondary_citers_of_target": int(secondary[kp, a]),
            "nearest_areas": [areas[b] for b in near[a]],
            "citers_in_nearest": int(counts[work[j], near[a]].sum()),
            "label": label(secondary[kp, a] > 0, counts[work[j], near[a]].sum() > 0),
        }

    top = order[:TOP]
    jumps = f[y_all[f]]
    tally = {}
    for name, idx in (("top_100_hits", top[y_all[top]]), ("all_jumps", jumps)):
        labels = [describe(j)["label"] for j in idx]
        tally[name] = {k: labels.count(k) for k in ("knocking", "next door", "surprising")}
    report = {
        "smoke": smoke,
        "far_pairs": int(len(f)),
        "important_jumps": int(len(jumps)),
        "top_100_jumps": int(y_all[top].sum()),
        "labels": tally,
        "top_100": [describe(j) | {"important_jump": bool(y_all[j])} for j in top],
        "all_jumps": [describe(j) for j in jumps[np.argsort(rank[jumps])]],
    }
    log(f"labels: {tally}, top-100 jumps {report['top_100_jumps']}")
    (out / "hits.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'hits.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
