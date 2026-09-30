#!/usr/bin/env python3
"""run-phase19.py -- does content closeness matter more the farther a citation reaches?

Everything is fixed in results/phase-19-reach-slope/README.md. Cells, span and
similarity are Phase 18's (scripts/run-phase18.py).

    scripts/run-phase19.py --out DIR [--smoke]
        (reads papers.jsonl.gz and refs.jsonl.gz in DIR, writes phase19.json)
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


p18 = load("run-phase18")

SEED = 20261009
T = 10
DROP = {"W4285719527"}
BOOT = 1000
FEATURES = ["log_prior", "year", "log_size", "span", "sim", "span_x_sim"]


def design(C, size, learn, span_key="span"):
    """Feature matrix (FEATURES order) with span and similarity standardised on learn."""
    s = (C[span_key] - C[span_key][learn].mean()) / C[span_key][learn].std()
    m = (C["sim"] - C["sim"][learn].mean()) / C["sim"][learn].std()
    return np.column_stack(
        [
            np.log1p(C["prior"]),
            C["year"] - 2000.0,
            np.log1p(size[C["area"], C["year"]]),
            s,
            m,
            s * m,
        ]
    )


def poisson_coefs(X, y):
    """Unpenalised Poisson regression; returns (intercept, coefficients)."""
    from sklearn.linear_model import PoissonRegressor

    r = PoissonRegressor(alpha=0.0, max_iter=1000).fit(X, y)
    return r.intercept_, r.coef_


def boot_coefs(X, y, groups, n, rng):
    """Coefficients refitted on n bootstrap draws resampling groups (works)."""
    ug, inv = np.unique(groups, return_inverse=True)
    rows_of = [np.nonzero(inv == g)[0] for g in range(len(ug))]
    out = np.empty((n, X.shape[1]))
    for d in range(n):
        pick = np.concatenate([rows_of[g] for g in rng.integers(0, len(ug), len(ug))])
        out[d] = poisson_coefs(X[pick], y[pick])[1]
    return out


def verdict(lo, hi, up, none, down):
    return up if lo > 0 else down if hi < 0 else none


def main() -> int:
    from scipy.stats import spearmanr
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    log = p18.load("run-phase11").log
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
            p["refs"] = [w for w in r["refs"] if w not in DROP]
    if smoke:
        P = P[::4]
    log(f"{len(P):,} papers")
    areas = sorted({p["area"] for p in P})
    ai = {a: k for k, a in enumerate(areas)}
    na = len(areas)
    year = np.array([p["year"] for p in P])
    area = np.array([ai[p["area"]] for p in P])
    cats = [sorted({ai[c] for c in p["categories"] if c in ai}) for p in P]
    last = int(year.max())
    size = np.zeros((na, last + 1))
    np.add.at(size, (area, year), 1)

    # text model, as Phase 18
    texts = [p["title"] + ". " + p["abstract"] for p in P]
    vec = TfidfVectorizer(
        sublinear_tf=True, min_df=1 if smoke else 5, max_df=0.5, stop_words="english"
    )
    old = np.nonzero(year <= p18.CUTOFF)[0]
    vec.fit([texts[k] for k in old])
    X = vec.transform(texts)
    del texts
    svd = TruncatedSVD(32 if smoke else p18.DIMS, random_state=p18.SEED)
    svd.fit(X[old])
    V = normalize(svd.transform(X)).astype(np.float32)
    del X
    log(f"text vectors {V.shape}")

    order = np.argsort(year, kind="stable")
    citers: dict[str, list[int]] = collections.defaultdict(list)
    for k in order:
        for w in P[k]["refs"]:
            citers[w].append(int(k))
    F = p18.cocitation(
        ({int(area[k]) for k in c if year[k] <= p18.CUTOFF} for c in citers.values()), na
    )

    rows = collections.defaultdict(list)
    for w, c in citers.items():
        if len(c) <= p18.MIN_PRIOR:
            continue
        c = np.array(c)
        yrs, ars = year[c], area[c]
        cs = None
        for a, y, pos, arr, later in p18.cells_of_work(yrs, ars, p18.MIN_PRIOR):
            if cs is None:
                cs = np.cumsum(V[c], axis=0)
            prior = np.bincount(ars[:pos], minlength=na).astype(float)
            pv, av = cs[pos - 1], V[c[arr]].sum(0)
            rows["work"].append(w)
            rows["area"].append(a)
            rows["year"].append(y)
            rows["prior"].append(pos)
            rows["span"].append(p18.span(prior, a, F))
            rows["span_any"].append(
                max(p18.span(prior, b, F) for k in c[arr] for b in cats[k] or [a])
            )
            rows["sim"].append(float(pv @ av / (np.linalg.norm(pv) * np.linalg.norm(av) + 1e-12)))
            rows["fol10"].append(int((later <= T).sum()))
    C = {k: np.array(v) for k, v in rows.items()}
    log(f"{len(C['year']):,} eligible cells")

    learn = C["year"] <= p18.CUTOFF - T
    y = C["fol10"][learn]
    groups = C["work"][learn]
    report: dict = {
        "seed": SEED,
        "smoke": smoke,
        "T": T,
        "learn_cells": int(learn.sum()),
        "learn_follow_on_total": int(y.sum()),
        "learn_caught_on_5": int((y >= 5).sum()),
        "span_mean_sd": [float(C["span"][learn].mean()), float(C["span"][learn].std())],
        "sim_mean_sd": [float(C["sim"][learn].mean()), float(C["sim"][learn].std())],
    }
    rng = np.random.default_rng(SEED)
    nboot = 20 if smoke else BOOT

    def fit(span_key):
        Xd = design(C, size, learn, span_key)[learn]
        b0, b = poisson_coefs(Xd, y)
        draws = boot_coefs(Xd, y, groups, nboot, rng)
        ci = np.percentile(draws, [2.5, 97.5], axis=0)
        res = {
            "intercept": float(b0),
            "coefficients": {
                f: {"estimate": float(b[j]), "ci95": [float(ci[0, j]), float(ci[1, j])]}
                for j, f in enumerate(FEATURES)
            },
        }
        # implied follow-on ratio for +1 SD similarity at a given (standardised) span
        mu, sd = C[span_key][learn].mean(), C[span_key][learn].std()
        js, jx = FEATURES.index("sim"), FEATURES.index("span_x_sim")
        for name, raw in [
            ("median_span", float(np.median(C[span_key][learn]))),
            ("top1_span", float(np.quantile(C[span_key][learn], 0.99))),
        ]:
            z = (raw - mu) / sd
            eff = np.exp(draws[:, js] + z * draws[:, jx])
            res[f"sim_ratio_at_{name}"] = {
                "span_bits": raw,
                "ratio": float(np.exp(b[js] + z * b[jx])),
                "ci95": [float(v) for v in np.percentile(eff, [2.5, 97.5])],
            }
        return res

    main_fit = fit("span")
    co = main_fit["coefficients"]
    main_fit["H1"] = verdict(
        *co["span_x_sim"]["ci95"],
        "content closeness matters more the farther the reach",
        "no evidence that it changes with reach",
        "content closeness matters less the farther the reach",
    )
    main_fit["H2"] = verdict(
        *co["sim"]["ci95"], "predicts more follow-on", "no evidence", "predicts less follow-on"
    )
    report["primary"] = main_fit
    log(f"primary: {json.dumps(main_fit)}")

    # by span decile
    sp, sm = C["span"][learn], C["sim"][learn]
    dec = np.minimum((np.argsort(np.argsort(sp)) * 10) // len(sp), 9)
    report["by_span_decile"] = []
    for d in range(10):
        m = dec == d
        hi = sm[m] >= np.median(sm[m])
        report["by_span_decile"].append(
            {
                "cells": int(m.sum()),
                "span_range": [float(sp[m].min()), float(sp[m].max())],
                "spearman_sim_followon": float(spearmanr(sm[m], y[m]).statistic),
                "mean_followon_high_sim": float(y[m][hi].mean()),
                "mean_followon_low_sim": float(y[m][~hi].mean()),
            }
        )
    log(f"by decile: {report['by_span_decile']}")

    # tail check on Phase 18's peek top 1% (follow-on judged past 2015)
    peek = (C["year"] <= p18.CUTOFF) & (C["year"] + T <= last)
    top = peek & (C["span"] >= np.quantile(C["span"][peek], 1 - p18.TOP))
    report["tail_check_peek_top1"] = {
        "cells": int(top.sum()),
        "caught_on_5": int((C["fol10"][top] >= 5).sum()),
        "spearman_sim_followon": float(spearmanr(C["sim"][top], C["fol10"][top]).statistic),
    }
    log(f"tail check: {report['tail_check_peek_top1']}")

    # label sensitivity
    alt = fit("span_any")
    alt["H1"] = verdict(
        *alt["coefficients"]["span_x_sim"]["ci95"],
        "content closeness matters more the farther the reach",
        "no evidence that it changes with reach",
        "content closeness matters less the farther the reach",
    )
    report["label_sensitivity_span_any"] = alt
    log(f"span_any: {json.dumps(alt)}")
    (out / "phase19.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase19.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
