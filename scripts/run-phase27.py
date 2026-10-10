#!/usr/bin/env python3
"""run-phase27.py -- train the embedding on past surprising jumps; grade its lists.

Everything is fixed in results/phase-27-jump-trained-embedding/README.md.
Population, model and lists are Phase 26's (scripts/run-phase26.py); the
trained embedding comes from scripts/train-phase27.py.

    scripts/run-phase27.py pairs   --out DIR [--smoke]
        (reads papers.jsonl.gz, refs.jsonl.gz; writes pairs.jsonl, pairs.json)
    scripts/run-phase27.py analyze --out DIR [--smoke]
        (reads those, emb.npy/json and emb-trained.npy/json; writes phase27.json)
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


p26 = load("run-phase26")
p25, p22 = p26.p25, p26.p22
SEED = 20261017
CUTOFFS = (2000, 1998)  # the sizing rule: the second only if the first gives too few pairs
ARRIVE_TO = 2005
MIN_PAIRS = 300
MAX_PAIRS = 3000
PER_JUMP = 3
TEXTS = ("tfidf", "embedding", "trained")


def h1_verdict(lo, hi):
    if lo > 0:
        return "training helps"
    return "training hurts" if hi < 0 else "no measurable difference"


def h2_verdict(lo, hi):
    if lo > 0:
        return "trained beats TF-IDF"
    return "trained is worse than TF-IDF" if hi < 0 else "no measurable difference"


def read(out, smoke):
    p20 = p22.load("run-phase20")
    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        P = [json.loads(line) for line in f]
    with gzip.open(out / "refs.jsonl.gz", "rt") as f:
        for p, r in zip(P, map(json.loads, f), strict=True):
            assert p["id"] == r["id"]
            p["refs"] = [w for w in r["refs"] if w not in p20.DROP]
            p["openalex"] = r["openalex"]
    return P[::4] if smoke else P


def jump_pairs(C, b, ce, to, rng, per_jump=PER_JUMP):
    """Anchor (arriving paper), positive (an earlier citer), hard negative, per jump."""
    year, area, cp, cw = C.year, C.area, C.cp, C.cw
    rows = np.nonzero((b.later >= 1) & ~b.book)[0]
    want = {(int(b.work[i]), int(b.target[i])) for i in rows}
    hist = year[cp] <= ce
    citers = collections.defaultdict(list)
    for k, w in zip(cp[hist], cw[hist], strict=True):
        citers[int(w)].append(int(k))
    arrive = collections.defaultdict(list)
    late = (year[cp] > ce) & (year[cp] <= to)
    for k, w in zip(cp[late], cw[late], strict=True):
        key = (int(w), int(area[k]))
        if key in want:
            arrive[key].append(int(k))
    home = {}
    for w, h in zip(b.work, b.home, strict=True):
        home.setdefault(int(w), int(h))
    by_home = collections.defaultdict(list)
    for w, h in sorted(home.items()):
        by_home[h].append(w)
    out = []
    for w, a in sorted(want):
        got = sorted(set(arrive[(w, a)]))
        if not got:
            continue
        for k in rng.choice(got, min(per_jump, len(got)), replace=False):
            others = [x for x in by_home[home[w]] if x != w]
            if not others:
                continue
            mine = set(citers[w])
            neg = None
            for _ in range(10):
                pool = [c for c in citers[int(rng.choice(others))] if c not in mine]
                if pool:
                    neg = int(rng.choice(pool))
                    break
            if neg is None:
                continue
            out.append(
                {
                    "work": C.works[w],
                    "target": C.areas[a],
                    "anchor": int(k),
                    "positive": int(rng.choice(citers[w])),
                    "negative": neg,
                }
            )
    return out


def text(p):
    return p["title"] + ". " + p["abstract"]


def stage_pairs(out, smoke, log):
    P = read(out, smoke)
    C = p26.corpus(P)
    zero = np.zeros((len(P), 1), np.float32)
    rng = np.random.default_rng(SEED)
    sizing = {}
    for ce in CUTOFFS:
        b = p26.build(C, ce, ARRIVE_TO, "embedding", zero, smoke, log)
        pairs = jump_pairs(C, b, ce, ARRIVE_TO, rng)
        sizing[ce] = {
            "surprising_pairs": int(len(b.r)),
            "jumps": int(((b.later >= 1) & ~b.book).sum()),
            "training_pairs": len(pairs),
        }
        log(f"cutoff {ce}: {sizing[ce]}")
        if len(pairs) >= MIN_PAIRS or smoke:
            break
    if len(pairs) > MAX_PAIRS:
        pairs = [pairs[i] for i in sorted(rng.choice(len(pairs), MAX_PAIRS, replace=False))]
    with open(out / "pairs.jsonl", "w", encoding="utf-8") as f:
        for q in pairs:
            row = {**q, **{k: text(P[q[k]]) for k in ("anchor", "positive", "negative")}}
            row["ids"] = [P[q[k]]["id"] for k in ("anchor", "positive", "negative")]
            f.write(json.dumps(row) + "\n")
    summary = {
        "cutoff": ce,
        "arrivals": [ce + 1, ARRIVE_TO],
        "sizing": sizing,
        "pairs": len(pairs),
        "jumps_used": len({(q["work"], q["target"]) for q in pairs}),
        "by_target_area": dict(collections.Counter(q["target"] for q in pairs).most_common()),
    }
    (out / "pairs.json").write_text(json.dumps(summary, indent=2) + "\n")
    log(f"wrote {len(pairs):,} pairs at cutoff {ce}")


def load_emb(out, name, P):
    meta = json.loads((out / f"{name}.json").read_text())
    pos = {pid: k for k, pid in enumerate(meta.pop("ids"))}
    raw = np.load(out / f"{name}.npy").astype(np.float32)
    E = np.zeros((len(P), raw.shape[1]), np.float32)
    have = [(k, pos[p["id"]]) for k, p in enumerate(P) if p["id"] in pos]
    E[[k for k, _ in have]] = raw[[j for _, j in have]]
    return E, meta, len(have)


def grade(tr, gb, na, hold, flt):
    """Phase 26's graded lists for one text model and filter setting."""
    rows_t = np.nonzero(~tr.book if flt == "on" else np.ones(len(tr.r), bool))[0]
    rows_g = np.nonzero(~gb.book if flt == "on" else np.ones(len(gb.r), bool))[0]
    score = p26.fit(tr, na, rows_t, hold)(gb, rows_g)
    lists = p25.top_per_area(score, gb.target[rows_g], na)
    met_all = gb.later[rows_g] >= 1
    met_a = np.array([int(met_all[lists[a]].sum()) for a in range(na)])
    caught_a = np.array([int((gb.later[rows_g][lists[a]] >= hold).sum()) for a in range(na)])
    n_a = np.array([len(lists[a]) for a in range(na)])
    base = float(met_all.mean())
    prec = met_a.sum() / max(n_a.sum(), 1)
    return {
        "train_pairs": int(len(rows_t)),
        "train_positives": int((tr.later[rows_t] >= hold).sum()),
        "population_2011": int(len(rows_g)),
        "base_rate_met": base,
        "listed": int(n_a.sum()),
        "met": int(met_a.sum()),
        "caught_on": int(caught_a.sum()),
        "precision": float(prec),
        "lift": float(prec / base) if base else None,
        "_met_a": met_a,
        "_n_a": n_a,
        "_pairs": {
            (int(gb.work[rows_g[j]]), int(gb.target[rows_g[j]]))
            for a in range(na)
            for j in lists[a]
        },
    }


def difference(x, y, na, rng, draws=p26.AREA_BOOT):
    d_a = x["_met_a"] - y["_met_a"]
    d = d_a[rng.integers(0, na, (draws, na))].sum(1)
    lo, hi = np.percentile(d, [2.5, 97.5])
    return {"difference": int(d_a.sum()), "ci95": [float(lo), float(hi)]}


def forecast(gb, na, hold, rng, smoke, with_ci):
    """Phase 23's within-route AUC test at 2011 (as Phase 26's report)."""
    p15 = p22.load("run-phase15")
    y = gb.later >= hold
    g = np.unique(gb.work, return_inverse=True)[1]
    st = gb.home * na + gb.target
    Z = p26.design(gb, na, np.arange(len(y)))
    Z = (Z - Z.mean(0)) / np.maximum(Z.std(0), 1e-12)
    s = p15.oof_scores(Z, y, g, int(g.max()) + 1, rng)
    a0, a1 = p22.strat_auc(s[0], y, st), p22.strat_auc(s[1], y, st)
    res = {"auc_BASE": a0, "auc_BASE+SIM": a1, "difference": a1 - a0}
    if with_ci:
        ng = int(g.max()) + 1
        nb = 20 if smoke else p15.p11.BOOT
        dd = np.empty(nb)
        for k in range(nb):
            w = np.bincount(rng.integers(0, ng, ng), minlength=ng)[g].astype(float)
            dd[k] = p22.strat_auc(s[1], y, st, w) - p22.strat_auc(s[0], y, st, w)
        res["ci95"] = [float(x) for x in np.percentile(dd, [2.5, 97.5])]
    return res


def stage_analyze(out, smoke, log):
    p20 = p22.load("run-phase20")
    P = read(out, smoke)
    hold = 1 if smoke else p20.TOOK_HOLD
    C = p26.corpus(P)
    na, areas = C.na, C.areas
    E0, meta0, n0 = load_emb(out, "emb", P)
    ET, metaT, nT = load_emb(out, "emb-trained", P)
    log(f"{len(P):,} papers; embedded {n0:,} ({meta0['model']}), trained {nT:,}")
    rng = np.random.default_rng(SEED)
    report: dict = {
        "seed": SEED,
        "smoke": smoke,
        "embedding": meta0,
        "trained": metaT,
        "pairs": json.loads((out / "pairs.json").read_text()),
    }
    kinds = {"tfidf": ("tfidf", None), "embedding": ("embedding", E0), "trained": ("embedding", ET)}
    variants, fc = {}, {}
    for name in TEXTS:
        kind, E = kinds[name]
        tr = p26.build(C, p26.TRAIN, p26.TRAIN_TO, kind, E, smoke, log)
        gb = p26.build(C, p26.GRADE, p26.GRADE_TO, kind, E, smoke, log)
        for flt in ("off", "on"):
            v = grade(tr, gb, na, hold, flt)
            v["met_by_area"] = {areas[a]: int(v["_met_a"][a]) for a in range(na)}
            variants[f"{name}/{flt}"] = v
            log(f"{name}/{flt}: listed {v['listed']}, met {v['met']}, caught {v['caught_on']}")
        del tr
        fc[name] = forecast(gb, na, hold, rng, smoke, with_ci=name == "trained")
        log(f"forecast 2011 {name}: {fc[name]}")
        del gb
    t, e, f = variants["trained/on"], variants["embedding/on"], variants["tfidf/on"]
    report["H1"] = {"met_trained": t["met"], "met_embedding": e["met"], **difference(t, e, na, rng)}
    report["H1"]["verdict"] = h1_verdict(*report["H1"]["ci95"])
    report["H2"] = {"met_trained": t["met"], "met_tfidf": f["met"], **difference(t, f, na, rng)}
    report["H2"]["verdict"] = h2_verdict(*report["H2"]["ci95"])
    log(f"H1: {report['H1']}")
    log(f"H2: {report['H2']}")
    report["overlap_on"] = {
        "trained&embedding": len(t["_pairs"] & e["_pairs"]),
        "trained&tfidf": len(t["_pairs"] & f["_pairs"]),
        "embedding&tfidf": len(e["_pairs"] & f["_pairs"]),
    }
    report["variants"] = {
        k: {x: y for x, y in v.items() if not x.startswith("_")} for k, v in variants.items()
    }
    report["forecast_2011"] = fc
    (out / "phase27.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase27.json'}")


def main() -> int:
    log = p26.p22.load("run-phase15").p11.log
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("stage", choices=["pairs", "analyze"])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    {"pairs": stage_pairs, "analyze": stage_analyze}[args.stage](args.out, args.smoke, log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
