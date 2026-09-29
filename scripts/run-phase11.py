#!/usr/bin/env python3
"""run-phase11.py -- which tools will enter which areas? (arXiv + OpenAlex)

Everything is fixed in results/phase-11-tool-area-grid/README.md.

    harvest    arXiv OAI-PMH, set=math           -> papers.jsonl.gz
    openalex   references by arXiv and journal DOI -> refs.jsonl.gz (API)
    snapshot   the same, from the OpenAlex parquet snapshot (no rate limit)
    analyze    cells, features, BASE vs BASE+SHAPE -> phase11.json

    scripts/run-phase11.py harvest  --out DIR [--smoke]
    scripts/run-phase11.py openalex --out DIR
    scripts/run-phase11.py snapshot --out DIR --files works-files.txt [--smoke]
    scripts/run-phase11.py analyze  --out DIR [--smoke]
"""

from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

OAI = "https://oaipmh.arxiv.org/oai"
OPENALEX = "https://api.openalex.org/works"
NS = {"o": "http://www.openarchives.org/OAI/2.0/", "a": "http://arxiv.org/OAI/arXiv/"}
EXCLUDED_AREAS = {"math.GM", "math.HO"}
SMOKE_DATES = ("2016-03-01", "2016-03-10")
MAX_WAIT = 600  # longest server-requested wait honoured, seconds

MIN_CITES = 20
MIN_POSITIVE = 2
RECENT = 5
WINDOWS = {"fit": (2010, 2011, 2015), "test": (2015, 2016, 2020)}
BOOT = 1000
SEED = 20261002
LANDMARKS = {
    "1603.04246": "Viazovska, sphere packing in dimension 8",
    "1603.06518": "Cohn, Kumar, Miller, Radchenko, Viazovska, dimension 24",
    "1605.01506": "Croot, Lev, Pach",
    "1605.09223": "Ellenberg, Gijswijt",
    "1907.00847": "Huang, sensitivity conjecture",
}
BASE = ["cites", "recent", "reach", "size", "flow"]


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def get(url: str, tries: int = 12) -> bytes:
    """GET with the server's Retry-After on 503/429 and backoff on other failures."""
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 400:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or min(300, 10 * 2**k)
            if wait > MAX_WAIT:  # a quota, not a hiccup: fail so the worker uploads and stops
                raise RuntimeError(f"http {e.code} asks for {wait}s; over the {MAX_WAIT}s limit")
            log(f"http {e.code}, waiting {wait}s")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            wait = min(300, 10 * 2**k)
            log(f"{type(e).__name__}, waiting {wait}s")
        time.sleep(wait)
    raise RuntimeError(f"gave up on {url}")


def arxiv_year(aid: str) -> int:
    """2016 for 1603.04246, 2006 for math/0601001."""
    m = re.match(r"(?:[a-z\-]+(?:\.[A-Z]{2})?/)?(\d{2})(\d{2})", aid)
    yy = int(m.group(1))
    return 1900 + yy if yy >= 90 else 2000 + yy


# ---------------------------------------------------------------- harvest
def harvest(out: Path, smoke: bool) -> None:
    params = {"verb": "ListRecords", "metadataPrefix": "arXiv", "set": "math"}
    if smoke:
        params.update({"from": SMOKE_DATES[0], "until": SMOKE_DATES[1]})
    url = OAI + "?" + urllib.parse.urlencode(params)
    kept = seen = pages = 0
    with gzip.open(out / "papers.jsonl.gz", "wt") as f:
        while url:
            root = ET.fromstring(get(url))
            pages += 1
            for rec in root.iterfind(".//o:record", NS):
                meta = rec.find(".//a:arXiv", NS)
                if meta is None:
                    continue
                seen += 1
                text = lambda t: (meta.findtext(f"a:{t}", "", NS) or "").strip()  # noqa: E731
                cats = text("categories").split()
                if not cats or not cats[0].startswith("math.") or cats[0] in EXCLUDED_AREAS:
                    continue
                aid = text("id")
                row = {
                    "id": aid,
                    "year": arxiv_year(aid),
                    "area": cats[0],
                    "categories": cats,
                    "doi": text("doi").split()[0].lower() if text("doi") else None,
                    "msc": text("msc-class") or None,
                    "title": re.sub(r"\s+", " ", text("title")),
                    "abstract": re.sub(r"\s+", " ", text("abstract")),
                }
                f.write(json.dumps(row) + "\n")
                kept += 1
            tok = root.find(".//o:resumptionToken", NS)
            if tok is not None and (tok.text or "").strip():
                url = OAI + "?" + urllib.parse.urlencode(
                    {"verb": "ListRecords", "resumptionToken": tok.text.strip()}
                )
                if pages % 20 == 0:
                    log(f"harvest page {pages}: {seen:,} records, {kept:,} kept "
                        f"(list size {tok.get('completeListSize')})")  # fmt: skip
                time.sleep(3)
            else:
                url = None
    log(f"harvest done: {pages} pages, {seen:,} records, {kept:,} math-primary papers")


# ---------------------------------------------------------------- openalex
def openalex_batch(dois: list[str]) -> list[dict]:
    q = "|".join("https://doi.org/" + d for d in dois)
    url = OPENALEX + "?" + urllib.parse.urlencode(
        {"filter": "doi:" + q, "per_page": 100, "select": "id,doi,referenced_works"}
    )
    try:
        return json.loads(get(url))["results"]
    except urllib.error.HTTPError:  # one bad DOI spoils the batch: retry one by one
        if len(dois) == 1:
            return []
        return [w for d in dois for w in openalex_batch([d])]


def openalex(out: Path) -> None:
    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        papers = [json.loads(line) for line in f]
    owner: dict[str, int] = {}
    for i, p in enumerate(papers):
        owner["10.48550/arxiv." + p["id"].lower()] = i
        if p["doi"] and re.fullmatch(r"10\.\d{4,9}/[^\s|,]+", p["doi"]):
            owner.setdefault(p["doi"], i)
    dois = sorted(owner)
    refs: dict[int, set[str]] = collections.defaultdict(set)
    oa_ids: dict[int, set[str]] = collections.defaultdict(set)
    for k in range(0, len(dois), 50):
        for w in openalex_batch(dois[k : k + 50]):
            d = (w.get("doi") or "").lower().replace("https://doi.org/", "")
            if d in owner:
                i = owner[d]
                oa_ids[i].add(w["id"].rsplit("/", 1)[-1])
                refs[i].update(r.rsplit("/", 1)[-1] for r in w.get("referenced_works") or ())
        if k // 50 % 200 == 0:
            log(f"openalex {k + 50:,} / {len(dois):,} DOIs, {len(oa_ids):,} papers found")
        time.sleep(0.15)
    with gzip.open(out / "refs.jsonl.gz", "wt") as f:
        for i, p in enumerate(papers):
            f.write(json.dumps({"id": p["id"], "openalex": sorted(oa_ids.get(i, ())),
                                "refs": sorted(refs.get(i, ()))}) + "\n")  # fmt: skip
    log(f"openalex done: {len(oa_ids):,} of {len(papers):,} papers found, "
        f"{sum(1 for i in refs if refs[i]):,} with references")  # fmt: skip


SNAPSHOT = "https://openalex.s3.amazonaws.com/"


def snapshot(out: Path, files: Path, smoke: bool) -> None:
    """refs.jsonl.gz from the OpenAlex parquet snapshot, as `openalex` does from the API.

    The API's daily limit stopped the first run at 40,000 of 717,075 DOIs; the
    quarterly snapshot holds the same records with no limit. Only the id, doi
    and referenced_works columns are read.
    """
    import duckdb

    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        papers = [json.loads(line) for line in f]
    owner: dict[str, int] = {}
    for i, p in enumerate(papers):
        owner["10.48550/arxiv." + p["id"].lower()] = i
        if p["doi"] and re.fullmatch(r"10\.\d{4,9}/[^\s|,]+", p["doi"]):
            owner.setdefault(p["doi"], i)
    paths = [ln.strip() for ln in files.read_text().splitlines() if ln.strip().endswith(".parquet")]
    if smoke:  # the newest partitions: the oldest hold none of these papers
        paths = paths[-3:]
    con = duckdb.connect()
    con.sql(f"SET home_directory = '{out.resolve()}'")  # cloud-init has no $HOME
    con.sql("INSTALL httpfs; LOAD httpfs; SET threads = 16")
    want = out / "want-dois.txt"
    want.write_text("".join("https://doi.org/" + d + "\n" for d in owner))
    con.execute(
        "CREATE TABLE want AS SELECT column0 AS doi FROM read_csv(?, header = false, "
        "delim = '\\t', quote = '', columns = {'column0': 'VARCHAR'})",
        [str(want)],
    )
    log(f"{con.sql('SELECT count(*) FROM want').fetchone()[0]:,} DOIs to find")
    refs: dict[int, set[str]] = collections.defaultdict(set)
    oa_ids: dict[int, set[str]] = collections.defaultdict(set)
    for k in range(0, len(paths), 20):
        urls = [SNAPSHOT + p for p in paths[k : k + 20]]
        rows = con.execute(
            "SELECT w.id, lower(w.doi), w.referenced_works "
            "FROM read_parquet(?, union_by_name = true) w JOIN want ON lower(w.doi) = want.doi",
            [urls],
        ).fetchall()
        for wid, doi, rw in rows:
            i = owner[doi.replace("https://doi.org/", "")]
            oa_ids[i].add(wid.rsplit("/", 1)[-1])
            refs[i].update(r.rsplit("/", 1)[-1] for r in rw or ())
        log(f"snapshot {min(k + 20, len(paths)):,} / {len(paths):,} files, "
            f"{len(oa_ids):,} papers found")  # fmt: skip
    if smoke and not oa_ids:
        raise RuntimeError("smoke: the join found no papers in the newest snapshot files")
    with gzip.open(out / "refs.jsonl.gz", "wt") as f:
        for i, p in enumerate(papers):
            f.write(json.dumps({"id": p["id"], "openalex": sorted(oa_ids.get(i, ())),
                                "refs": sorted(refs.get(i, ()))}) + "\n")  # fmt: skip
    log(f"snapshot done: {len(oa_ids):,} of {len(papers):,} papers found, "
        f"{sum(1 for i in refs if refs[i]):,} with references")  # fmt: skip


# ---------------------------------------------------------------- analyze
def rank_auc(inv, counts_pos, counts_neg):
    below = np.concatenate(([0.0], np.cumsum(counts_neg)[:-1]))
    return float((counts_pos * (below + 0.5 * counts_neg)).sum() / (counts_pos.sum() * counts_neg.sum()))


def auc(score, pos, w=None):
    w = np.ones(len(score)) if w is None else w
    _, inv = np.unique(score, return_inverse=True)
    n = inv.max() + 1
    return rank_auc(inv, np.bincount(inv, w * pos, n), np.bincount(inv, w * ~pos, n))


def window_cells(P, H, o0, o1, X, min_cites, min_pos):
    """Cells and features for one window, from history papers only."""
    from sklearn.preprocessing import normalize
    import scipy.sparse as sp

    areas = sorted({p["area"] for p in P})
    ai = {a: k for k, a in enumerate(areas)}
    hist = [k for k, p in enumerate(P) if p["year"] <= H]
    recent = [k for k in hist if P[k]["year"] > H - RECENT]
    outc = [k for k, p in enumerate(P) if o0 <= p["year"] <= o1]

    citers: dict[str, list[int]] = collections.defaultdict(list)
    for k in hist:
        for t in P[k]["refs"]:
            citers[t].append(k)
    tools = sorted(t for t, c in citers.items() if len(c) >= min_cites)
    ti = {t: r for r, t in enumerate(tools)}
    nt, na = len(tools), len(areas)
    home = {}  # an arXiv paper's own area, by OpenAlex id
    for p in P:
        for o in p["openalex"]:
            home[o] = ai[p["area"]]

    hist_count = np.zeros((nt, na))
    recent_count = np.zeros(nt)
    rows, cols = [], []
    for t in tools:
        r = ti[t]
        for k in citers[t]:
            hist_count[r, ai[P[k]["area"]]] += 1
            recent_count[r] += P[k]["year"] > H - RECENT
            rows.append(r)
            cols.append(k)
    out_count = np.zeros((nt, na))
    for k in outc:
        for t in P[k]["refs"]:
            if t in ti:
                out_count[ti[t], ai[P[k]["area"]]] += 1

    size = np.zeros(na)
    W = np.zeros((na, na))  # W[A, B]: share of A's recent citations going to arXiv papers of area B
    for k in recent:
        a = ai[P[k]["area"]]
        size[a] += 1
        for t in P[k]["refs"]:
            if t in home:
                W[a, home[t]] += 1
    W /= np.maximum(W.sum(1, keepdims=True), 1)
    share = hist_count / hist_count.sum(1, keepdims=True)
    flow = share @ W.T

    # shape: tool demand profile vs area profile, TF-IDF of titles + abstracts
    hist_pos = {k: r for r, k in enumerate(hist)}
    Xh = X[hist]
    inc = sp.csr_matrix((np.ones(len(rows)), (rows, [hist_pos[c] for c in cols])), shape=(nt, len(hist)))
    inc = normalize(inc, "l1") if nt else inc
    rec_rows = [ai[P[k]["area"]] for k in recent]
    ainc = normalize(sp.csr_matrix((np.ones(len(recent)), (rec_rows, [hist_pos[k] for k in recent])),
                                   shape=(na, len(hist))), "l1")  # fmt: skip
    A_prof = normalize(ainc @ Xh)
    # cosine(normalize(inc @ Xh), A_prof), in chunks of tools: the tool profiles
    # are means of many abstracts, too dense to hold all at once
    shape = np.zeros((nt, na))
    for c in range(0, nt, 2000):
        T = inc[c : c + 2000] @ Xh
        norm = np.sqrt(np.asarray(T.multiply(T).sum(1))).ravel()
        shape[c : c + 2000] = np.asarray((T @ A_prof.T).todense()) / np.maximum(norm, 1e-12)[:, None]

    feats = {
        "cites": np.log1p(hist_count.sum(1))[:, None].repeat(na, 1),
        "recent": np.log1p(recent_count)[:, None].repeat(na, 1),
        "reach": (hist_count > 0).sum(1)[:, None].repeat(na, 1).astype(float),
        "size": np.log1p(size)[None, :].repeat(nt, 0),
        "flow": flow,
        "shape": shape,
    }
    cell = hist_count == 0
    for t in tools:
        if t in home:
            cell[ti[t], home[t]] = False
    tr, ar = np.nonzero(cell)
    return {
        "tools": tools, "areas": areas, "tool_row": tr, "area_col": ar,
        "X": np.column_stack([feats[f][tr, ar] for f in BASE + ["shape"]]),
        "pos": out_count[tr, ar] >= min_pos,
        "counts": {"history_papers": len(hist), "outcome_papers": len(outc),
                   "popular_tools": nt, "areas": na, "cells": int(len(tr)),
                   "positives": int((out_count[tr, ar] >= min_pos).sum())},
    }  # fmt: skip


def analyze(out: Path, smoke: bool) -> None:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        P = [json.loads(line) for line in f]
    with gzip.open(out / "refs.jsonl.gz", "rt") as f:
        for p, r in zip(P, map(json.loads, f), strict=True):
            assert p["id"] == r["id"]
            p["refs"], p["openalex"] = r["refs"], r["openalex"]
    report: dict = {"seed": SEED, "boot": BOOT, "smoke": smoke}
    yr = collections.Counter(p["year"] for p in P)
    yr_refs = collections.Counter(p["year"] for p in P if p["refs"])
    report["coverage_by_year"] = {y: {"papers": yr[y], "with_refs": yr_refs[y]} for y in sorted(yr)}
    report["coverage_by_area"] = {
        a: {"papers": n, "with_refs": sum(1 for p in P if p["area"] == a and p["refs"])}
        for a, n in collections.Counter(p["area"] for p in P).most_common()
    }
    log(f"{len(P):,} papers, {sum(1 for p in P if p['refs']):,} with references")

    min_cites, min_pos = (2, 1) if smoke else (MIN_CITES, MIN_POSITIVE)
    windows = {"fit": (2012, 2013, 2015), "test": (2015, 2016, 2016)} if smoke else WINDOWS
    res = {}
    for name, (H, o0, o1) in windows.items():
        texts = [p["title"] + ". " + p["abstract"] for p in P]
        vec = TfidfVectorizer(sublinear_tf=True, min_df=1 if smoke else 5, max_df=0.5,
                              stop_words="english")  # fmt: skip
        vec.fit([t for t, p in zip(texts, P) if p["year"] <= H])
        X = vec.transform(texts)
        res[name] = window_cells(P, H, o0, o1, X, min_cites, min_pos)
        report[f"counts_{name}"] = res[name]["counts"]
        log(f"{name}: {res[name]['counts']}")

    fit, test = res["fit"], res["test"]
    if not (fit["pos"].any() and test["pos"].any() and (~test["pos"]).any()):
        report["note"] = "too few positives to fit or score"
        (out / "phase11.json").write_text(json.dumps(report, indent=2) + "\n")
        log("too few positives; wrote counts only")
        return
    nb = len(BASE)
    models = {}
    for name, cols in (("BASE", slice(0, nb)), ("BASE+SHAPE", slice(0, nb + 1))):
        m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
        m.fit(fit["X"][:, cols], fit["pos"])
        models[name] = m.decision_function(test["X"][:, cols])
        report[f"coefficients_{name}"] = dict(
            zip(BASE + ["shape"], m[-1].coef_[0].tolist(), strict=False)
        )
    pos = test["pos"]
    s_base, s_shape = models["BASE"], models["BASE+SHAPE"]
    a_base, a_shape = auc(s_base, pos), auc(s_shape, pos)

    rng = np.random.default_rng(SEED)
    tool = test["tool_row"]
    nt = len(test["tools"])
    inv = {k: np.unique(s, return_inverse=True)[1] for k, s in models.items()}
    draws = np.empty((BOOT if not smoke else 20, 2))
    for d in range(len(draws)):
        w = np.bincount(rng.integers(0, nt, nt), minlength=nt)[tool].astype(float)
        for j, k in enumerate(("BASE", "BASE+SHAPE")):
            n = inv[k].max() + 1
            draws[d, j] = rank_auc(inv[k], np.bincount(inv[k], w * pos, n),
                                   np.bincount(inv[k], w * ~pos, n))  # fmt: skip
    diff = draws[:, 1] - draws[:, 0]
    lo, hi = np.percentile(diff, [2.5, 97.5])
    d_obs = a_shape - a_base
    if lo > 0:
        verdict = ("the demand profile adds to popularity and citation habits" if d_obs >= 0.01
                   else "detectable, too small to matter")  # fmt: skip
    elif hi < 0:
        verdict = "the demand profile hurts"
    else:
        verdict = "no measurable difference"
    report["H1"] = {"auc_BASE": a_base, "auc_BASE+SHAPE": a_shape, "difference": d_obs,
                    "ci95": [float(lo), float(hi)], "verdict": verdict}  # fmt: skip
    log(f"H1: BASE {a_base:.4f}, BASE+SHAPE {a_shape:.4f}, diff {d_obs:+.4f} "
        f"[{lo:+.4f}, {hi:+.4f}] -> {verdict}")  # fmt: skip

    names = BASE + ["shape"]
    report["auc_single_feature"] = {f: auc(test["X"][:, j], pos) for j, f in enumerate(names)}
    rate = pos.mean()
    report["top_k"] = {
        k: {str(n): int(pos[np.argsort(-s, kind="stable")[:n]].sum()) for n in (1000, 10000)}
        for k, s in models.items()
    }
    report["top_k"]["chance"] = {"1000": 1000 * rate, "10000": 10000 * rate}
    q = np.quantile(s_base, np.linspace(0, 1, 6))
    band = np.clip(np.searchsorted(q, s_base, side="right") - 1, 0, 4)
    report["H1_by_BASE_quintile"] = []
    for b in range(5):
        m = band == b
        if pos[m].any() and (~pos[m]).any():
            report["H1_by_BASE_quintile"].append(
                {"quintile": b + 1, "positives": int(pos[m].sum()), "cells": int(m.sum()),
                 "auc_BASE": auc(s_base[m], pos[m]), "auc_BASE+SHAPE": auc(s_shape[m], pos[m])}
            )  # fmt: skip

    # landmark cells
    by_id = {p["id"]: p for p in P}
    trow = {t: r for r, t in enumerate(test["tools"])}
    acol = {a: c for c, a in enumerate(test["areas"])}
    where = {(r, c): k for k, (r, c) in enumerate(zip(test["tool_row"], test["area_col"], strict=True))}
    pct = {k: (np.argsort(np.argsort(s)) + 0.5) / len(s) for k, s in models.items()}
    land = {}
    for aid, label in LANDMARKS.items():
        p = by_id.get(aid)
        if p is None or not p["refs"]:
            land[aid] = {"paper": label, "status": "missing" if p is None else "no references"}
            continue
        cells = []
        for t in p["refs"]:
            k = where.get((trow.get(t), acol.get(p["area"])))
            if k is not None:
                cells.append({"tool": t, "positive": bool(pos[k]),
                              **{f"percentile_{m}": float(pct[m][k]) for m in models}})  # fmt: skip
        land[aid] = {"paper": label, "area": p["area"], "references": len(p["refs"]),
                     "test_cells": sorted(cells, key=lambda c: -c["percentile_BASE+SHAPE"])}  # fmt: skip
    report["landmarks"] = land

    (out / "phase11.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out / 'phase11.json'}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("stage", choices=["harvest", "openalex", "snapshot", "analyze"])
    ap.add_argument("--files", type=Path, help="snapshot: parquet paths, one per line")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.stage == "harvest":
        harvest(args.out, args.smoke)
    elif args.stage == "openalex":
        openalex(args.out)
    elif args.stage == "snapshot":
        snapshot(args.out, args.files, args.smoke)
    else:
        analyze(args.out, args.smoke)
    return 0


if __name__ == "__main__":
    sys.exit(main())
