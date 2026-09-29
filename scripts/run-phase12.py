#!/usr/bin/env python3
"""run-phase12.py -- how close was the tool already? (Phase 11 cells on a closeness ladder)

Everything is fixed in results/phase-12-closeness-ladder/README.md. Papers,
references, cells and features come from scripts/run-phase11.py.

    authors    author ids from the OpenAlex parquet snapshot -> authors.jsonl.gz
    analyze    rungs, H1 (shape on cold cells), H2 (rate by rung) -> phase12.json

    scripts/run-phase12.py authors --out DIR --files works-files.txt [--smoke]
    scripts/run-phase12.py analyze --out DIR [--smoke]
"""

from __future__ import annotations

import argparse
import collections
import gzip
import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np

_spec = importlib.util.spec_from_file_location(
    "phase11", Path(__file__).with_name("run-phase11.py")
)
p11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p11)
log = p11.log

SEED = 20261003
FLOW_QUANTILE = 0.75
MIN_COLD_POSITIVES = 100
TOOK_HOLD = 5
RUNGS = {
    1: "shared paper",
    2: "shared author",
    3: "second-hand",
    4: "neighbouring field",
    5: "cold",
}


# ---------------------------------------------------------------- authors
def authors(out: Path, files: Path, smoke: bool) -> None:
    """authors.jsonl.gz: OpenAlex author ids per paper, joined by DOI as Phase 11's refs."""
    import duckdb

    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        papers = [json.loads(line) for line in f]
    owner: dict[str, int] = {}
    for i, p in enumerate(papers):
        owner["10.48550/arxiv." + p["id"].lower()] = i
        if p["doi"] and re.fullmatch(r"10\.\d{4,9}/[^\s|,]+", p["doi"]):
            owner.setdefault(p["doi"], i)
    paths = [ln.strip() for ln in files.read_text().splitlines() if ln.strip().endswith(".parquet")]
    if smoke:
        paths = paths[-3:]
    con = duckdb.connect()
    con.sql(f"SET home_directory = '{out.resolve()}'")
    con.sql("INSTALL httpfs; LOAD httpfs; SET threads = 16")
    want = out / "want-dois.txt"
    want.write_text("".join("https://doi.org/" + d + "\n" for d in owner))
    con.execute(
        "CREATE TABLE want AS SELECT column0 AS doi FROM read_csv(?, header = false, "
        "delim = '\\t', quote = '', columns = {'column0': 'VARCHAR'})",
        [str(want)],
    )
    found: dict[int, set[str]] = collections.defaultdict(set)
    for k in range(0, len(paths), 20):
        urls = [p11.SNAPSHOT + p for p in paths[k : k + 20]]
        rows = con.execute(
            "SELECT lower(w.doi), list_transform(w.authorships, x -> x.author.id) "
            "FROM read_parquet(?, union_by_name = true) w JOIN want ON lower(w.doi) = want.doi",
            [urls],
        ).fetchall()
        for doi, ids in rows:
            i = owner[doi.replace("https://doi.org/", "")]
            found[i].update(a.rsplit("/", 1)[-1] for a in ids or () if a)
        log(f"authors {min(k + 20, len(paths)):,} / {len(paths):,} files, {len(found):,} papers")
    if smoke and not found:
        raise RuntimeError("smoke: the join found no authors in the newest snapshot files")
    with gzip.open(out / "authors.jsonl.gz", "wt") as f:
        for i, p in enumerate(papers):
            f.write(json.dumps({"id": p["id"], "authors": sorted(found.get(i, ()))}) + "\n")
    log(f"authors done: {len(found):,} of {len(papers):,} papers with author ids")


# ---------------------------------------------------------------- ladder
def ladder(P, H, w):
    """Each cell's rung (1-5, README table) and the counts behind it, history papers only."""
    import scipy.sparse as sp

    def binary(m):
        m = sp.csr_matrix(m)
        m.data[:] = 1
        return m

    def ones(r, c, shape):
        return binary(sp.csr_matrix((np.ones(len(r)), (r, c)), shape=shape))

    ai = {a: k for k, a in enumerate(w["areas"])}
    ti = {t: r for r, t in enumerate(w["tools"])}
    hist = [k for k, p in enumerate(P) if p["year"] <= H]
    nh, nt, na = len(hist), len(ti), len(ai)
    at = {o: j for j, k in enumerate(hist) for o in P[k]["openalex"]}
    ir, ic, cr, cc, pr, pc = [], [], [], [], [], []
    aid: dict[str, int] = {}
    for j, k in enumerate(hist):
        for t in P[k]["refs"]:
            if t in ti:
                ir.append(ti[t])
                ic.append(j)
            if t in at:
                cr.append(j)
                cc.append(at[t])
        for a in P[k]["authors"]:
            pr.append(j)
            pc.append(aid.setdefault(a, len(aid)))
    inc = ones(ir, ic, (nt, nh))  # T is cited by history paper j
    cites = ones(cr, cc, (nh, nh))  # history paper j cites history paper i
    wrote = ones(pr, pc, (nh, len(aid)))  # history paper j has author a
    area_of = ones(range(nh), [ai[P[k]["area"]] for k in hist], (nh, na))

    second = (binary(inc @ cites.T) @ area_of).toarray()  # A papers citing a T-citer
    shared = (binary(inc @ wrote) @ binary(area_of.T @ wrote).T).toarray()  # authors in both
    tr, ar = w["tool_row"], w["area_col"]
    flow = w["X"][:, p11.BASE.index("flow")]
    rung = np.full(len(tr), 5)
    rung[flow >= np.quantile(flow, FLOW_QUANTILE)] = 4
    rung[second[tr, ar] > 0] = 3
    rung[shared[tr, ar] > 0] = 2
    rung[w["xlist"] > 0] = 1
    return rung, {
        "history_papers_with_authors": int(sum(1 for k in hist if P[k]["authors"])),
        "history_papers": nh,
        "authors": len(aid),
        "flow_threshold": float(np.quantile(flow, FLOW_QUANTILE)),
    }


# ---------------------------------------------------------------- tests
def gain(fit_X, fit_y, test_X, test_y, test_tool, n_tools, boot, rng):
    """Fit without and with the last column; test AUCs, tool-bootstrap interval, scores."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    if not (fit_y.any() and (~fit_y).any() and test_y.any() and (~test_y).any()):
        return None, None
    scores = []
    for cols in (slice(0, fit_X.shape[1] - 1), slice(0, fit_X.shape[1])):
        m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
        m.fit(fit_X[:, cols], fit_y)
        scores.append(m.decision_function(test_X[:, cols]))
    inv = [np.unique(s, return_inverse=True)[1] for s in scores]
    draws = np.empty((boot, 2))
    for d in range(boot):
        wt = np.bincount(rng.integers(0, n_tools, n_tools), minlength=n_tools)[test_tool]
        wt = wt.astype(float)
        for j in range(2):
            n = inv[j].max() + 1
            draws[d, j] = p11.rank_auc(
                inv[j], np.bincount(inv[j], wt * test_y, n), np.bincount(inv[j], wt * ~test_y, n)
            )
    a0, a1 = p11.auc(scores[0], test_y), p11.auc(scores[1], test_y)
    rep = {
        "auc_without_shape": a0,
        "auc_with_shape": a1,
        "difference": a1 - a0,
        "ci95": [float(x) for x in np.percentile(draws[:, 1] - draws[:, 0], [2.5, 97.5])],
        "positives": int(test_y.sum()),
        "cells": int(len(test_y)),
    }
    return rep, scores


def top(score, y, n=1000):
    return int(y[np.argsort(-score, kind="stable")[:n]].sum())


def verdict(r):
    lo, hi = r["ci95"]
    if lo > 0:
        return (
            "shape predicts cold jumps"
            if r["difference"] >= 0.03
            else ("detectable on cold cells, small")
        )
    return "shape hurts on cold cells" if hi < 0 else "no measurable help on cold cells"


def analyze(out: Path, smoke: bool) -> None:
    from sklearn.feature_extraction.text import TfidfVectorizer

    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        P = [json.loads(line) for line in f]
    with (
        gzip.open(out / "refs.jsonl.gz", "rt") as f,
        gzip.open(out / "authors.jsonl.gz", "rt") as g,
    ):
        for p, r, a in zip(P, map(json.loads, f), map(json.loads, g), strict=True):
            assert p["id"] == r["id"] == a["id"]
            p["refs"], p["openalex"], p["authors"] = r["refs"], r["openalex"], a["authors"]
    log(f"{len(P):,} papers, {sum(1 for p in P if p['authors']):,} with author ids")

    min_cites, min_pos = (2, 1) if smoke else (p11.MIN_CITES, p11.MIN_POSITIVE)
    windows = {"fit": (2012, 2013, 2015), "test": (2015, 2016, 2016)} if smoke else p11.WINDOWS
    report: dict = {"seed": SEED, "boot": p11.BOOT, "smoke": smoke}
    W = {}
    for name, (H, o0, o1) in windows.items():
        texts = [p["title"] + ". " + p["abstract"] for p in P]
        vec = TfidfVectorizer(
            sublinear_tf=True, min_df=1 if smoke else 5, max_df=0.5, stop_words="english"
        )
        vec.fit([t for t, p in zip(texts, P, strict=True) if p["year"] <= H])
        w = p11.window_cells(P, H, o0, o1, vec.transform(texts), min_cites, min_pos)
        w["rung"], report[f"ladder_{name}"] = ladder(P, H, w)
        report[f"rungs_{name}"] = {
            f"{k} {RUNGS[k]}": {
                "cells": int((w["rung"] == k).sum()),
                "positives": int(w["pos"][w["rung"] == k].sum()),
                "rate": float(w["pos"][w["rung"] == k].mean()) if (w["rung"] == k).any() else None,
            }
            for k in RUNGS
        }
        log(f"{name}: {report[f'rungs_{name}']}")
        W[name] = w
    fit, test = W["fit"], W["test"]
    nt = len(test["tools"])
    boot = 20 if smoke else p11.BOOT
    rng = np.random.default_rng(SEED)

    # H1: cold cells only
    fc, tc = fit["rung"] == 5, test["rung"] == 5
    h1, s = gain(
        fit["X"][fc],
        fit["pos"][fc],
        test["X"][tc],
        test["pos"][tc],
        test["tool_row"][tc],
        nt,
        boot,
        rng,
    )
    powered = min(fit["pos"][fc].sum(), test["pos"][tc].sum()) >= MIN_COLD_POSITIVES
    if h1 is not None:
        h1["verdict"] = verdict(h1) if powered else "underpowered"
        y, out_c = test["pos"][tc], test["outcome"][tc]
        held = out_c >= TOOK_HOLD
        rate, hold_rate = y.mean(), held.mean()
        h1["top_1000"] = {"BASE": top(s[0], y), "BASE+SHAPE": top(s[1], y), "chance": 1000 * rate}
        h1["took_hold"] = {
            "cells": int(held.sum()),
            "top_1000_BASE": top(s[0], held),
            "top_1000_BASE+SHAPE": top(s[1], held),
            "chance": 1000 * hold_rate,
        }
        # the top 20 cold predictions, for reading
        by_oa = {o: p for p in P for o in p["openalex"]}
        idx = np.nonzero(tc)[0][np.argsort(-s[1], kind="stable")[:20]]
        h1["top_20"] = [
            {
                "tool": test["tools"][test["tool_row"][k]],
                "title": (by_oa.get(test["tools"][test["tool_row"][k]]) or {}).get("title"),
                "area": test["areas"][test["area_col"][k]],
                "outcome_papers": int(test["outcome"][k]),
            }
            for k in idx
        ]
        log(
            f"H1 cold: {h1['auc_without_shape']:.4f} -> {h1['auc_with_shape']:.4f} "
            f"({h1['difference']:+.4f} {h1['ci95']}) {h1['positives']} positives -> "
            f"{h1['verdict']}; top-1000 {h1['top_1000']}"
        )
    report["H1"] = h1 or {"verdict": "too few positives to fit or score"}

    # H2: positive rate by rung
    rates = {k: v["rate"] for k, v in zip(RUNGS, report["rungs_test"].values(), strict=True)}
    others = [r for k, r in rates.items() if k != 5 and r is not None]
    report["H2"] = {
        "rates": {f"{k} {RUNGS[k]}": r for k, r in rates.items()},
        "passes": bool(rates[5] is not None and others and rates[5] < min(others)),
        "falls_1_to_5": bool(
            all(r is not None for r in rates.values())
            and all(rates[k] > rates[k + 1] for k in range(1, 5))
        ),
    }
    log(f"H2: {report['H2']}")

    # shape's gain within each rung
    report["gain_by_rung"] = {}
    for k in range(1, 5):
        fm, tm = fit["rung"] == k, test["rung"] == k
        r, _ = gain(
            fit["X"][fm],
            fit["pos"][fm],
            test["X"][tm],
            test["pos"][tm],
            test["tool_row"][tm],
            nt,
            boot,
            rng,
        )
        report["gain_by_rung"][f"{k} {RUNGS[k]}"] = r
    report["gain_by_rung"]["5 cold"] = {
        k: v for k, v in (h1 or {}).items() if k not in ("top_20", "took_hold")
    }

    # all cells, ladder controlled: BASE + rung 1-4 indicators, without and with shape
    def with_ladder(w):
        nb = len(p11.BASE)
        ind = np.column_stack([(w["rung"] == k).astype(float) for k in range(1, 5)])
        return np.column_stack([w["X"][:, :nb], ind, w["X"][:, nb]])

    report["all_cells_ladder_controlled"], _ = gain(
        with_ladder(fit),
        fit["pos"],
        with_ladder(test),
        test["pos"],
        test["tool_row"],
        nt,
        boot,
        rng,
    )
    (out / "phase12.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase12.json'}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("stage", choices=["authors", "analyze"])
    ap.add_argument("--files", type=Path, help="authors: parquet paths, one per line")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.stage == "authors":
        authors(args.out, args.files, args.smoke)
    else:
        analyze(args.out, args.smoke)
    return 0


if __name__ == "__main__":
    sys.exit(main())
