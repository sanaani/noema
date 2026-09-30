#!/usr/bin/env python3
"""run-phase24.py -- would the forecast have pointed at known breakthroughs?

Everything is fixed in results/phase-24-curated-backtest/README.md. The build
and model are Phase 23's (scripts/run-phase23.py) on every unconnected pair at
2005, with no span or label filter; the curated pairs are those marked
eligible in results/phase-24-curated-backtest/eligible.json.

    scripts/run-phase24.py --out DIR --curated FILE [--smoke]
        (reads papers.jsonl.gz and refs.jsonl.gz in DIR, writes phase24.json)
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
SEED = 20261014
CUTOFF = p22.CUTOFF
WINDOW = p22.WINDOW
MIN_PAIRS = 8


def percentile(s, j):
    """Share of pairs scoring below pair j, ties counted half, in percent."""
    return float(100 * (np.mean(s < s[j]) + 0.5 * np.mean(s == s[j])))


def verdict(median, n):
    if n < MIN_PAIRS:
        return "underpowered"
    if median >= 99:
        return "points at known breakthroughs"
    if median >= 90:
        return "flags them, not sharply"
    return "weak" if median >= 50 else "misses them"


def sign_verdict(up, down, p):
    if p >= 0.05:
        return "no clear effect"
    return "similarity lifts known breakthroughs" if up > down else "similarity lowers them"


def main() -> int:
    import scipy.sparse as sp
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    p20 = p22.load("run-phase20")
    p15 = p22.load("run-phase15")
    log = p15.p11.log

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--curated", type=Path, required=True)
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

    r, c = np.nonzero(counts[keep] == 0)
    label = np.where(secondary[r, c], 0, np.where(next_door[r, c], 1, 2))
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
    y = outc[r, c] >= hold
    work = keep[r]
    log(f"H={H}: {len(keep):,} works, {len(r):,} candidate pairs, {int(y.sum())} jumps")

    Z = np.column_stack([base_num, np.eye(na)[home], np.eye(na)[target], sim])
    Z = (Z - Z.mean(0)) / np.maximum(Z.std(0), 1e-12)
    g = np.unique(work, return_inverse=True)[1]
    rng = np.random.default_rng(SEED)
    s = p15.oof_scores(Z, y, g, int(g.max()) + 1, rng)
    scores = {"BASE": s[0], "BASE+SIM": s[1], "SIM alone": sim}

    pair = -np.ones((len(keep), na), int)
    pair[r, c] = np.arange(len(r))
    names = ["knocking", "next door", "surprising"]
    rows = []
    for e in json.loads(args.curated.read_text()):
        if not e["eligible"]:
            continue
        row = {k: e[k] for k in ("programme", "work", "year", "target", "openalex")}
        w, a = wi.get(e["openalex"], -1), ai.get(e["target"], -1)
        j = pair[kpos[w], a] if w >= 0 and kpos[w] >= 0 and a >= 0 else -1
        if j < 0:
            rows.append(row | {"candidate": False})
            continue
        in_a = target == a
        rows.append(
            row
            | {
                "candidate": True,
                "home_area": areas[home[j]],
                "citers_up_to_2005": int(n_cit[work[j]]),
                "span_bits": float(span[j]),
                "similarity": float(sim[j]),
                "label": names[label[j]],
                "papers_2006_2015": int(outc[r[j], c[j]]),
                "important_jump": bool(y[j]),
                "percentile": {k: percentile(v, j) for k, v in scores.items()},
                "rank": {k: int((v > v[j]).sum() + 1) for k, v in scores.items()},
                "percentile_in_target_area_BASE+SIM": percentile(s[1][in_a], int(in_a[:j].sum())),
            }
        )
        log(str(rows[-1]))

    got = [x for x in rows if x["candidate"]]
    pb = np.array([x["percentile"]["BASE"] for x in got])
    ps = np.array([x["percentile"]["BASE+SIM"] for x in got])
    med = float(np.median(ps)) if got else float("nan")
    report: dict = {
        "seed": SEED,
        "smoke": smoke,
        "cutoff": H,
        "candidate_pairs": int(len(r)),
        "important_jumps": int(y.sum()),
        "curated_eligible": len(rows),
        "curated_in_candidates": len(got),
        "H1": {
            "median_percentile_BASE+SIM": med,
            "median_percentile_BASE": float(np.median(pb)) if got else float("nan"),
            "median_percentile_SIM_alone": (
                float(np.median([x["percentile"]["SIM alone"] for x in got]))
                if got
                else float("nan")
            ),
            "in_top": {
                str(n): {k: sum(x["rank"][k] <= n for x in got) for k in scores}
                for n in (100, 1000, max(1, len(r) // 100), max(1, len(r) // 10))
            },
            "verdict": verdict(med, len(got)),
        },
    }
    if got:
        from scipy.stats import binomtest

        d = ps - pb
        up, down = int((d > 0).sum()), int((d < 0).sum())
        p = float(binomtest(up, up + down).pvalue) if up + down else 1.0
        boot = 20 if smoke else p15.p11.BOOT
        means = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(boot)]
        report["H2"] = {
            "improved": up,
            "worsened": down,
            "sign_test_p": p,
            "mean_difference": float(d.mean()),
            "ci95": [float(x) for x in np.percentile(means, [2.5, 97.5])],
            "verdict": "underpowered" if len(got) < MIN_PAIRS else sign_verdict(up, down, p),
        }
    jumps = np.nonzero(y)[0]
    report["comparison_all_important_jumps"] = {
        k: float(np.median([percentile(v, j) for j in jumps])) if len(jumps) else None
        for k, v in scores.items()
    }
    sj = jumps[label[jumps] == 2]
    report["comparison_surprising_important_jumps"] = {
        k: float(np.median([percentile(v, j) for j in sj])) if len(sj) else None
        for k, v in scores.items()
    }
    report["pairs"] = rows
    log(f"H1: {report['H1']}")
    log(f"H2: {report.get('H2')}")
    (out / "phase24.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase24.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
