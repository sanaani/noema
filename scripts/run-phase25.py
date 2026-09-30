#!/usr/bin/env python3
"""run-phase25.py -- the matchmaker lists: per area, the 20 surprising pairs most likely to meet.

Everything is fixed in results/phase-25-matchmaker-lists/README.md. The build,
population and model are Phase 23's (scripts/run-phase23.py), at two cutoffs:
trained at TRAIN (outcomes to TRAIN+10), applied unchanged at LIVE.

    scripts/run-phase25.py --out DIR [--smoke]
        (reads papers.jsonl.gz and refs.jsonl.gz in DIR, writes phase25.json)
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import sys
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


p23 = load("run-phase23")
p22 = p23.p22
hits = p23.hits
SEED = 20261015
TRAIN = 2011
LIVE = 2021
LAST = 2025  # last full year of papers; references are sparse after 2021
WINDOW = p23.WINDOW
BITS = 4.65  # Phase 23's primary threshold
TOP = 20
EXAMPLES = 3
strat_auc, usable, choose_grain, verdict = p22.strat_auc, p22.usable, p22.choose_grain, p23.verdict


def top_per_area(score, target, na, k=TOP):
    """Indices of the k highest scores per target area, best first."""
    out = {}
    for a in range(na):
        idx = np.nonzero(target == a)[0]
        out[a] = idx[np.argsort(-score[idx], kind="stable")[:k]]
    return out


def lift(hit, chosen):
    """Share of hits among the chosen, over the share among all; None if undefined."""
    base = float(hit.mean()) if len(hit) else 0.0
    if not len(chosen) or base == 0:
        return None
    return float(hit[chosen].mean() / base)


def lookup_titles(ids, log):
    """Titles of non-arXiv works from OpenAlex, batched; best effort."""
    names = {}
    ids = sorted(ids)
    for i in range(0, len(ids), 50):
        chunk = ids[i : i + 50]
        url = (
            "https://api.openalex.org/works?filter=openalex_id:"
            + "|".join(chunk)
            + "&per-page=50&select=id,display_name,publication_year,type"
        )
        try:
            with urllib.request.urlopen(url, timeout=60) as f:
                for w in json.load(f)["results"]:
                    names[w["id"].rsplit("/", 1)[1]] = [
                        w["publication_year"],
                        w["type"],
                        (w["display_name"] or "")[:120],
                    ]
        except Exception as e:  # noqa: BLE001 -- titles are decoration, filled in later
            log(f"title lookup failed for batch {i // 50}: {e}")
    return names


def build(P, H, smoke, log, with_recent_papers=False):
    """Phase 23's build at cutoff H: every unconnected (work, area) pair with its features."""
    import scipy.sparse as sp
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    p20 = p22.load("run-phase20")
    hold = 1 if smoke else p20.TOOK_HOLD
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

    def area_papers_citing(lo, hi):
        o = (year[cp] > lo) & (year[cp] <= hi) & (kpos[cw] >= 0)
        return sp.csr_matrix(
            (np.ones(o.sum()), (kpos[cw[o]], area[cp[o]])), shape=(len(keep), na)
        ).toarray()

    outc = area_papers_citing(H, H + WINDOW)
    home_of = counts[keep].argmax(1)
    breadth_of = (counts[keep] > 0).sum(1)
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
    surprising = ~secondary[r, c] & ~next_door[r, c]
    span = S[r, c]
    f = np.nonzero(surprising & (span >= BITS))[0]
    r, c, span = r[f], c[f], span[f]
    b = SimpleNamespace(
        H=H,
        areas=areas,
        na=na,
        works=works,
        r=r,
        c=c,
        span=span,
        base_num=np.column_stack(
            [
                np.log1p(n_cit[keep][r]),
                np.log1p(recent[keep][r]),
                np.log1p(asize[c]),
                span,
                breadth_of[r],
            ]
        ),
        sim=SIM[r, c],
        home=home_of[r],
        target=c,
        y=outc[r, c] >= hold,
        outc=outc[r, c],
        work=keep[r],
        n_cit=n_cit[keep][r],
        recent=recent[keep][r],
        breadth=breadth_of[r],
        hold=hold,
    )
    log(f"H={H}: {len(keep):,} works, {len(r):,} surprising pairs at >= {BITS} bits")
    if with_recent_papers:
        b.forward = area_papers_citing(H, LAST)[r, c]
        b.Wc, b.V, b.year, b.area = Wc, V, year, area
        b.kpos = kpos
        b.recent_of = lambda a: np.nonzero((area == a) & (year > H - p20.RECENT) & (year <= H))[0]
    return b


def design(b, na):
    return np.column_stack([b.base_num, np.eye(na)[b.home], np.eye(na)[b.target], b.sim])


def main() -> int:
    from sklearn.linear_model import LogisticRegression

    p15 = p22.load("run-phase15")
    p11 = p15.p11
    log = p11.log

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--no-lookup", action="store_true")
    args = ap.parse_args()
    out, smoke = args.out, args.smoke

    p20 = p22.load("run-phase20")
    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        P = [json.loads(line) for line in f]
    with gzip.open(out / "refs.jsonl.gz", "rt") as f:
        for p, r in zip(P, map(json.loads, f), strict=True):
            assert p["id"] == r["id"]
            p["refs"] = [w for w in r["refs"] if w not in p20.DROP]
            p["openalex"] = r["openalex"]
    if smoke:
        P = P[::4]
    log(f"{len(P):,} papers")
    title = {o: p["id"] + " " + p["title"] for p in P for o in p["openalex"]}
    ptitle = {k: p["id"] + " " + p["title"] for k, p in enumerate(P)}
    rng = np.random.default_rng(SEED)
    boot = 20 if smoke else p11.BOOT
    report: dict = {"seed": SEED, "smoke": smoke, "train_cutoff": TRAIN, "live_cutoff": LIVE}

    # 1. train at TRAIN, and replicate Phase 23's test there
    t = build(P, TRAIN, smoke, log)
    na, areas = t.na, t.areas
    Zt = design(t, na)
    mu, sd = Zt.mean(0), np.maximum(Zt.std(0), 1e-12)
    Zt = (Zt - mu) / sd
    y, strata = t.y, t.home * na + t.target
    g = np.unique(t.work, return_inverse=True)[1]
    grain_counts = {"route": usable(y, strata), "target area": usable(y, t.target)}
    grain = choose_grain(grain_counts)
    info = {
        "pairs": int(len(y)),
        "important_jumps": int(y.sum()),
        "usable_strata_and_jumps": {k: list(v) for k, v in grain_counts.items()},
        "grain": grain,
    }
    if grain is None:
        info["H1"] = None
    else:
        st = strata if grain == "route" else t.target
        s = p15.oof_scores(Zt, y, g, int(g.max()) + 1, rng)
        ng = int(g.max()) + 1
        d = np.empty(boot)
        for k in range(boot):
            w = np.bincount(rng.integers(0, ng, ng), minlength=ng)[g].astype(float)
            d[k] = strat_auc(s[1], y, st, w) - strat_auc(s[0], y, st, w)
            if (k + 1) % 100 == 0:
                log(f"  bootstrap {k + 1}/{boot}")
        a0, a1 = strat_auc(s[0], y, st), strat_auc(s[1], y, st)
        res = {
            "auc_BASE": a0,
            "auc_BASE+SIM": a1,
            "difference": a1 - a0,
            "ci95": [float(x) for x in np.percentile(d, [2.5, 97.5])],
            "auc_SIM_alone": strat_auc(t.sim, y, st),
            "top": {
                str(n): {
                    "BASE": int(y[np.argsort(-s[0], kind="stable")[:n]].sum()),
                    "BASE+SIM": int(y[np.argsort(-s[1], kind="stable")[:n]].sum()),
                    "chance": n * float(y.mean()),
                }
                for n in (100, 1000)
            },
        }
        res["verdict"] = verdict(res)
        info["H1"] = res
    log(f"train {TRAIN}: {info}")
    report["train"] = info
    models = {}
    for name, cols in (("BASE", slice(0, Zt.shape[1] - 1)), ("BASE+SIM", slice(0, Zt.shape[1]))):
        models[name] = LogisticRegression(C=1.0, max_iter=1000).fit(Zt[:, cols], y)
    report["train"]["coefficients_BASE+SIM"] = dict(
        zip(
            ["log citers", "log recent citers", "log area size", "span", "breadth"]
            + [f"home {a}" for a in areas]
            + [f"target {a}" for a in areas]
            + ["similarity"],
            [float(x) for x in models["BASE+SIM"].coef_[0]],
            strict=True,
        )
    )
    del t, Zt

    # 2. apply at LIVE
    v = build(P, LIVE, smoke, log, with_recent_papers=True)
    assert v.areas == areas
    Zv = (design(v, na) - mu) / sd
    score = {
        "BASE": models["BASE"].decision_function(Zv[:, :-1]),
        "BASE+SIM": models["BASE+SIM"].decision_function(Zv),
        "SIM alone": v.sim,
    }
    del Zv
    order = np.argsort(-score["BASE+SIM"], kind="stable")
    grank = np.empty(len(order), int)
    grank[order] = np.arange(1, len(order) + 1)
    met1, met5 = v.forward >= 1, v.forward >= v.hold
    lists = top_per_area(score["BASE+SIM"], v.target, na)
    chosen = np.concatenate([lists[a] for a in range(na)])
    live = {
        "pairs": int(len(v.r)),
        "met_2022_2025": {
            "at_least_1": int(met1.sum()),
            "at_least_hold": int(met5.sum()),
            "note": "corpus references are sparse after 2021; lower bounds",
        },
        "lift_of_top_lists": {
            "at_least_1": lift(met1, chosen),
            "at_least_hold": lift(met5, chosen),
            "chosen": int(len(chosen)),
            "chosen_met_1": int(met1[chosen].sum()),
            "chosen_met_hold": int(met5[chosen].sum()),
        },
        "lift_by_score_top_560": {
            k: lift(met1, np.argsort(-s_, kind="stable")[: len(chosen)]) for k, s_ in score.items()
        },
    }
    need = {v.works[v.work[j]] for a in range(na) for j in lists[a]} - set(title)
    names = {} if args.no_lookup or smoke else lookup_titles(need, log)
    per_area = {}
    for a in range(na):
        rec = v.recent_of(a)
        M = v.V[rec]
        rows = []
        for q, j in enumerate(lists[a]):
            w = v.works[v.work[j]]
            ex = np.argsort(-(M @ v.Wc[v.kpos[v.work[j]]]), kind="stable")[:EXAMPLES]
            rows.append(
                {
                    "rank_in_area": q + 1,
                    "global_rank": int(grank[j]),
                    "work": w,
                    "title": title.get(w) or (names.get(w) or [None, None, None])[2],
                    "year_type": names.get(w, [None, None, None])[:2] if w in names else None,
                    "home_area": areas[v.home[j]],
                    "citers_up_to_2021": int(v.n_cit[j]),
                    "recent_citers": int(v.recent[j]),
                    "breadth": int(v.breadth[j]),
                    "span_bits": float(v.span[j]),
                    "similarity": float(v.sim[j]),
                    "score": float(score["BASE+SIM"][j]),
                    "target_papers_2022_2025": int(v.forward[j]),
                    "most_similar_recent_papers": [ptitle[int(rec[e])] for e in ex],
                }
            )
        idx = np.nonzero(v.target == a)[0]
        per_area[areas[a]] = {
            "surprising_pairs": int(len(idx)),
            "met_1_share": float(met1[idx].mean()) if len(idx) else None,
            "top_met_1": int(met1[lists[a]].sum()),
            "list": rows,
        }
        log(f"{areas[a]}: {len(idx):,} pairs, top {TOP} met {met1[lists[a]].sum()}")
    live["by_area"] = per_area
    report["live"] = live
    log(f"live: { ({k: live[k] for k in ('pairs', 'met_2022_2025', 'lift_of_top_lists')}) }")
    (out / "phase25.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase25.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
