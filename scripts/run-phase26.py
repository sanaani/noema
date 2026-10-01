#!/usr/bin/env python3
"""run-phase26.py -- grade the matchmaker lists at 2011, test two fixes, ship 2021 lists.

Everything is fixed in results/phase-26-graded-lists/README.md. Population and
model are Phase 25's (scripts/run-phase25.py); the embedding comes from
scripts/embed-phase26.py.

    scripts/run-phase26.py --out DIR [--smoke] [--no-lookup]
        (reads papers.jsonl.gz, refs.jsonl.gz, emb.npy, emb.json in DIR;
         writes phase26.json)
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


p25 = load("run-phase25")
p22, hits = p25.p22, p25.hits
SEED = 20261016
TRAIN, GRADE, LIVE = 2005, 2011, 2021
TRAIN_TO, GRADE_TO, LIVE_TO = 2011, 2021, 2025
BITS = p25.BITS
TOP = p25.TOP
TEXTBOOK_QUANTILE = 0.9
AREA_BOOT = 10_000
TEXTS = ("tfidf", "embedding")


def textbook_mask(breadth, q=TEXTBOOK_QUANTILE):
    """Works whose breadth is in the top (1 - q) of breadth among works."""
    return breadth >= np.quantile(breadth, q)


def area_bootstrap(met_by_area, n_by_area, draws, rng):
    """Precision over resampled areas: sum met / sum listed, per draw."""
    k = len(met_by_area)
    pick = rng.integers(0, k, (draws, k))
    return met_by_area[pick].sum(1) / np.maximum(n_by_area[pick].sum(1), 1)


def h1_verdict(lift, lo):
    if lo <= 1:
        return "no better than chance"
    return "far better than chance" if lift >= 10 else "better than chance"


def h2_verdict(lo, hi):
    if lo > 0:
        return "embedding is better"
    return "embedding is worse" if hi < 0 else "no measurable difference"


def corpus(P):
    areas = sorted({p["area"] for p in P})
    ai = {a: k for k, a in enumerate(areas)}
    works = sorted({w for p in P for w in p["refs"]})
    wi = {w: k for k, w in enumerate(works)}
    return SimpleNamespace(
        P=P,
        areas=areas,
        ai=ai,
        na=len(areas),
        year=np.array([p["year"] for p in P]),
        area=np.array([ai[p["area"]] for p in P]),
        works=works,
        wi=wi,
        cp=np.array([k for k, p in enumerate(P) for _ in p["refs"]]),
        cw=np.array([wi[w] for p in P for w in p["refs"]]),
    )


def build(C, H, label_to, text, E, smoke, log, examples=False):
    """Phase 25's surprising population at cutoff H, with text = tfidf or embedding."""
    import scipy.sparse as sp
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    p20 = p22.load("run-phase20")
    year, area, cp, cw, na = C.year, C.area, C.cp, C.cw, C.na
    nw = len(C.works)
    hist = year <= H
    m = hist[cp]
    counts = sp.csr_matrix((np.ones(m.sum()), (cw[m], area[cp[m]])), shape=(nw, na)).toarray()
    recent = np.bincount(cw[m & (year[cp] > H - p20.RECENT)], minlength=nw)
    n_cit = counts.sum(1)
    F = p20.cocitation_matrix(sp.csr_matrix(counts > 0).astype(float))
    keep = np.nonzero(n_cit >= p20.MIN_CITERS)[0]
    S = p20.span_matrix(counts[keep], F)
    hidx = np.nonzero(hist)[0]
    if text == "tfidf":
        vec = TfidfVectorizer(
            sublinear_tf=True, min_df=1 if smoke else 5, max_df=0.5, stop_words="english"
        )
        X = vec.fit_transform([C.P[k]["title"] + ". " + C.P[k]["abstract"] for k in hidx])
        svd = TruncatedSVD(32 if smoke else 256, random_state=p25.SEED)
        V = np.zeros((len(C.P), svd.n_components), np.float32)
        V[hidx] = normalize(svd.fit_transform(X))
        del X
    else:
        V = np.zeros_like(E)
        V[hidx] = E[hidx]
    kpos = -np.ones(nw, int)
    kpos[keep] = np.arange(len(keep))
    mk = m & (kpos[cw] >= 0)
    inc = sp.csr_matrix((np.ones(mk.sum()), (kpos[cw[mk]], cp[mk])), shape=(len(keep), len(C.P)))
    Wc = normalize(inc @ V)
    ra = hist & (year > H - p20.RECENT)
    Ac = np.zeros((na, V.shape[1]))
    np.add.at(Ac, area[ra], V[ra])
    SIM = Wc @ normalize(Ac).T
    asize = np.bincount(area[ra], minlength=na)

    def citing(lo, hi):
        o = (year[cp] > lo) & (year[cp] <= hi) & (kpos[cw] >= 0)
        return sp.csr_matrix(
            (np.ones(o.sum()), (kpos[cw[o]], area[cp[o]])), shape=(len(keep), na)
        ).toarray()

    later = citing(H, label_to)
    home_of = counts[keep].argmax(1)
    breadth_of = (counts[keep] > 0).sum(1)
    book_of = textbook_mask(breadth_of)
    sr, sc = [], []
    for k in hidx:
        sec = {C.ai[x] for x in C.P[k]["categories"][1:] if x in C.ai} - {area[k]}
        for w in C.P[k]["refs"]:
            if kpos[C.wi[w]] >= 0:
                for a in sec:
                    sr.append(kpos[C.wi[w]])
                    sc.append(a)
    secondary = sp.csr_matrix((np.ones(len(sr)), (sr, sc)), shape=(len(keep), na)).toarray() > 0
    near = np.zeros((na, na), bool)
    for a in range(na):
        near[a, hits.nearest_areas(F, a)] = True
    next_door = (counts[keep] > 0) @ near.T > 0

    r, c = np.nonzero(counts[keep] == 0)
    f = np.nonzero(~secondary[r, c] & ~next_door[r, c] & (S[r, c] >= BITS))[0]
    r, c = r[f], c[f]
    b = SimpleNamespace(
        H=H,
        text=text,
        r=r,
        target=c,
        home=home_of[r],
        work=keep[r],
        base_num=np.column_stack(
            [
                np.log1p(n_cit[keep][r]),
                np.log1p(recent[keep][r]),
                np.log1p(asize[c]),
                S[r, c],
                breadth_of[r],
            ]
        ),
        sim=SIM[r, c],
        later=later[r, c],
        book=book_of[r],
        n_cit=n_cit[keep][r],
        breadth=breadth_of[r],
        span=S[r, c],
    )
    if examples:
        b.Wc, b.V, b.kpos = Wc, V, kpos
        b.recent_of = lambda a: np.nonzero((area == a) & ra)[0]
    log(
        f"H={H} {text}: {len(keep):,} works, {len(r):,} surprising pairs, "
        f"{int(b.book.sum()):,} on textbooks"
    )
    return b


def design(b, na, rows):
    return np.column_stack(
        [b.base_num[rows], np.eye(na)[b.home[rows]], np.eye(na)[b.target[rows]], b.sim[rows]]
    )


def fit(b, na, rows, hold):
    from sklearn.linear_model import LogisticRegression

    Z = design(b, na, rows)
    mu, sd = Z.mean(0), np.maximum(Z.std(0), 1e-12)
    m = LogisticRegression(C=1.0, max_iter=1000).fit((Z - mu) / sd, b.later[rows] >= hold)
    return lambda bb, rr: m.decision_function((design(bb, na, rr) - mu) / sd)


def main() -> int:
    p15 = p22.load("run-phase15")
    p20 = p22.load("run-phase20")
    log = p15.p11.log
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--no-lookup", action="store_true")
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
    C = corpus(P)
    na, areas = C.na, C.areas
    meta = json.loads((out / "emb.json").read_text())
    pos = {pid: k for k, pid in enumerate(meta.pop("ids"))}
    raw = np.load(out / "emb.npy").astype(np.float32)
    E = np.zeros((len(P), raw.shape[1]), np.float32)
    have = [(k, pos[p["id"]]) for k, p in enumerate(P) if p["id"] in pos]
    E[[k for k, _ in have]] = raw[[j for _, j in have]]
    del raw
    log(f"{len(P):,} papers, {len(have):,} embedded ({meta['model']})")
    title = {o: p["id"] + " " + p["title"] for p in P for o in p["openalex"]}
    ptitle = {k: p["id"] + " " + p["title"] for k, p in enumerate(P)}
    rng = np.random.default_rng(SEED)
    report: dict = {"seed": SEED, "smoke": smoke, "embedding": meta}

    # graded lists: train at 2005 (labels to 2011), list at 2011, grade to 2021
    variants, grade_builds = {}, {}
    for text in TEXTS:
        tr = build(C, TRAIN, TRAIN_TO, text, E, smoke, log)
        gb = build(C, GRADE, GRADE_TO, text, E, smoke, log)
        grade_builds[text] = gb
        for flt in ("off", "on"):
            rows_t = np.nonzero(~tr.book if flt == "on" else np.ones(len(tr.r), bool))[0]
            rows_g = np.nonzero(~gb.book if flt == "on" else np.ones(len(gb.r), bool))[0]
            score = fit(tr, na, rows_t, hold)(gb, rows_g)
            lists = p25.top_per_area(score, gb.target[rows_g], na)
            met_all = gb.later[rows_g] >= 1
            met_a = np.array([int(met_all[lists[a]].sum()) for a in range(na)])
            caught_a = np.array(
                [int((gb.later[rows_g][lists[a]] >= hold).sum()) for a in range(na)]
            )
            n_a = np.array([len(lists[a]) for a in range(na)])
            base = float(met_all.mean())
            prec = met_a.sum() / max(n_a.sum(), 1)
            v = {
                "train_pairs": int(len(rows_t)),
                "train_positives": int((tr.later[rows_t] >= hold).sum()),
                "population_2011": int(len(rows_g)),
                "base_rate_met": base,
                "listed": int(n_a.sum()),
                "met": int(met_a.sum()),
                "caught_on": int(caught_a.sum()),
                "precision": float(prec),
                "lift": float(prec / base) if base else None,
                "met_by_area": {areas[a]: int(met_a[a]) for a in range(na)},
                "_met_a": met_a,
                "_n_a": n_a,
                "_pairs": {
                    (int(gb.work[rows_g[j]]), int(gb.target[rows_g[j]]))
                    for a in range(na)
                    for j in lists[a]
                },
            }
            variants[f"{text}/{flt}"] = v
            log(
                f"{text}/{flt}: listed {v['listed']}, met {v['met']}, caught {v['caught_on']}, "
                f"base {base:.4f}, lift {v['lift']}"
            )
        del tr

    # H1: Phase 25's method (tfidf, filter off)
    v = variants["tfidf/off"]
    keep_a = v["_n_a"] > 0
    boot = area_bootstrap(v["_met_a"][keep_a], v["_n_a"][keep_a], AREA_BOOT, rng)
    lo, hi = np.percentile(boot / v["base_rate_met"], [2.5, 97.5])
    report["H1"] = {
        "lift": v["lift"],
        "ci95": [float(lo), float(hi)],
        "precision": v["precision"],
        "met_per_20": 20 * v["precision"],
        "verdict": h1_verdict(v["lift"], lo),
    }
    log(f"H1: {report['H1']}")

    # H2: embedding vs tfidf, filter on, bootstrap over areas
    e, t = variants["embedding/on"], variants["tfidf/on"]
    d_a = e["_met_a"] - t["_met_a"]
    pick = rng.integers(0, na, (AREA_BOOT, na))
    d = d_a[pick].sum(1)
    lo, hi = np.percentile(d, [2.5, 97.5])
    report["H2"] = {
        "met_embedding": e["met"],
        "met_tfidf": t["met"],
        "difference": int(d_a.sum()),
        "ci95": [float(lo), float(hi)],
        "verdict": h2_verdict(lo, hi),
    }
    log(f"H2: {report['H2']}")
    ship = "tfidf" if report["H2"]["verdict"] == "embedding is worse" else "embedding"
    report["shipped_text"] = ship
    report["filter_cost"] = {
        text: variants[f"{text}/off"]["met"] - variants[f"{text}/on"]["met"] for text in TEXTS
    }
    report["overlap_on"] = len(e["_pairs"] & t["_pairs"])
    for k, v in variants.items():
        report.setdefault("variants", {})[k] = {x: y for x, y in v.items() if not x.startswith("_")}

    # Phase 23's test at 2011 for each text model (filter off, 10-year label)
    report["forecast_2011"] = {}
    for text in TEXTS:
        gb = grade_builds[text]
        y = gb.later >= hold
        g = np.unique(gb.work, return_inverse=True)[1]
        st = gb.home * na + gb.target
        Z = design(gb, na, np.arange(len(y)))
        Z = (Z - Z.mean(0)) / np.maximum(Z.std(0), 1e-12)
        s = p15.oof_scores(Z, y, g, int(g.max()) + 1, rng)
        a0, a1 = p22.strat_auc(s[0], y, st), p22.strat_auc(s[1], y, st)
        res = {"auc_BASE": a0, "auc_BASE+SIM": a1, "difference": a1 - a0}
        if text == "embedding":
            ng = int(g.max()) + 1
            nb = 20 if smoke else p15.p11.BOOT
            dd = np.empty(nb)
            for k in range(nb):
                w = np.bincount(rng.integers(0, ng, ng), minlength=ng)[g].astype(float)
                dd[k] = p22.strat_auc(s[1], y, st, w) - p22.strat_auc(s[0], y, st, w)
            res["ci95"] = [float(x) for x in np.percentile(dd, [2.5, 97.5])]
        report["forecast_2011"][text] = res
        log(f"forecast 2011 {text}: {res}")

    # the shipped 2021 lists: train at 2011 (10-year label), filter on
    gb = grade_builds[ship]
    rows_t = np.nonzero(~gb.book)[0]
    model = fit(gb, na, rows_t, hold)
    grade = variants[f"{ship}/on"]
    del grade_builds
    lv = build(C, LIVE, LIVE_TO, ship, E, smoke, log, examples=True)
    rows = np.nonzero(~lv.book)[0]
    score = model(lv, rows)
    lists = p25.top_per_area(score, lv.target[rows], na)
    need = {C.works[lv.work[rows[j]]] for a in range(na) for j in lists[a]} - set(title)
    names = {} if args.no_lookup or smoke else p25.lookup_titles(need, log)
    per_area = {}
    for a in range(na):
        rec = lv.recent_of(a)
        M = lv.V[rec]
        out_rows = []
        for q, j in enumerate(lists[a]):
            i = rows[j]
            w = C.works[lv.work[i]]
            ex = np.argsort(-(M @ lv.Wc[lv.kpos[lv.work[i]]]), kind="stable")[: p25.EXAMPLES]
            out_rows.append(
                {
                    "rank_in_area": q + 1,
                    "work": w,
                    "title": title.get(w) or (names.get(w) or [None, None, None])[2],
                    "home_area": areas[lv.home[i]],
                    "citers_up_to_2021": int(lv.n_cit[i]),
                    "breadth": int(lv.breadth[i]),
                    "span_bits": float(lv.span[i]),
                    "similarity": float(lv.sim[i]),
                    "score": float(score[j]),
                    "target_papers_2022_2025": int(lv.later[i]),
                    "most_similar_recent_papers": [ptitle[int(rec[e_])] for e_ in ex],
                }
            )
        per_area[areas[a]] = {
            "grade_2011_met_of_listed": [
                int(grade["_met_a"][a]),
                int(grade["_n_a"][a]),
            ],
            "list": out_rows,
        }
    report["live_2021"] = {"text": ship, "pairs": int(len(rows)), "by_area": per_area}
    (out / "phase26.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase26.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
