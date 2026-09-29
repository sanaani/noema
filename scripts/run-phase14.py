#!/usr/bin/env python3
"""run-phase14.py -- did the predicted jumps do real work, or were they passing mentions?

Everything is fixed in results/phase-14-did-hits-do-work/README.md. Cells and
scores are Phase 13's (scripts/run-phase13.py), recomputed with its seed.

    sample   cells, citing papers, arXiv sources, citation contexts -> contexts.jsonl.gz
    batches  blinded, shuffled judging batches                       -> judge/batch-*.json
    score    H1, H2 and the reported numbers from both judges' labels -> phase14.json

    scripts/run-phase14.py sample  --out DIR [--smoke]  (reads papers, refs, authors .jsonl.gz)
    scripts/run-phase14.py batches --out DIR
    scripts/run-phase14.py score   --out DIR
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import io
import json
import re
import sys
import tarfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


p11, p12, p13 = load("run-phase11"), load("run-phase12"), load("run-phase13")
log = p11.log

SEED = 20261005
PER_GROUP = 60
PAPERS_PER_CELL = 3
TOP = 1000
EXPECTED_TOP_HITS = 213  # Phase 13's BASE+SHAPE top 1,000 cold cells
MIN_JUDGED_G1 = 30
BOOT = 2000
MAX_CONTEXTS = 5
BEFORE, AFTER = 600, 400
BATCH = 45
EPRINT = "https://export.arxiv.org/e-print/"
OPENALEX = "https://api.openalex.org/works"
STOP = {
    "a",
    "an",
    "and",
    "the",
    "of",
    "on",
    "in",
    "to",
    "for",
    "with",
    "its",
    "their",
    "by",
    "at",
    "from",
    "into",
    "some",
    "via",
    "de",
    "la",
    "et",
    "des",
    "und",
    "der",
    "die",
}


# ---------------------------------------------------------------- text helpers
def words(s: str) -> list[str]:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\\[a-zA-Z]+", " ", s)  # TeX commands
    return re.findall(r"[a-z]+", s)


def title_words(title: str) -> list[str]:
    return [w for w in words(title) if w not in STOP and len(w) >= 2]


def matches(entry: str, tw: list[str], surname: list[str]) -> bool:
    ew = set(words(entry))
    if len(tw) < 2 or not surname or not all(s in ew for s in surname):
        return False
    return sum(w in ew for w in tw) >= 0.8 * len(tw)


def unpack(blob: bytes) -> tuple[str, list[str]] | None:
    """(body of all .tex, bibliography texts) from an arXiv e-print, or None if no source."""
    if blob[:4] == b"%PDF":
        return None
    try:
        blob = gzip.decompress(blob)
    except OSError:
        pass
    if blob[:4] == b"%PDF":
        return None
    tex, bib = [], []
    try:
        with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name.lower()
                if name.endswith((".tex", ".bbl", ".bib", ".ltx")):
                    text = tf.extractfile(m).read().decode("utf-8", "replace")
                    (bib if name.endswith((".bbl", ".bib")) else tex).append(text)
    except tarfile.TarError:
        tex.append(blob.decode("utf-8", "replace"))
    if not tex:
        return None
    body = "\n".join(re.sub(r"(?<!\\)%.*", "", t) for t in tex)
    return body, bib


def bib_entries(body: str, bib: list[str]) -> list[tuple[str, str]]:
    """(key, text) for every \\bibitem and every @entry."""
    out = []
    for text in [body, *bib]:
        parts = re.split(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", text)
        for k in range(1, len(parts), 2):
            out.append((parts[k].strip(), parts[k + 1][:1500]))
        parts = re.split(r"@\w+\s*\{\s*([^,\s]+)\s*,", text)
        for k in range(1, len(parts), 2):
            out.append((parts[k].strip(), parts[k + 1][:1500]))
    return out


CITE = re.compile(r"\\[a-zA-Z]*cite[a-zA-Z]*\*?(?:\[[^\]]*\]){0,2}\{([^}]*)\}")
SECTION = re.compile(r"\\(?:sub)*section\*?\{([^}]*)\}")


def contexts(body: str, keys: set[str]) -> list[dict]:
    heads = [(m.start(), m.group(1)) for m in SECTION.finditer(body)]
    out = []
    for m in CITE.finditer(body):
        if not keys & {k.strip() for k in m.group(1).split(",")}:
            continue
        head = [h for pos, h in heads if pos < m.start()]
        text = body[max(0, m.start() - BEFORE) : m.end() + AFTER]
        out.append(
            {
                "section": head[-1].strip() if head else "(before the first section)",
                "text": re.sub(r"\s+", " ", text).strip(),
            }
        )
        if len(out) == MAX_CONTEXTS:
            break
    return out


def fetch(url: str) -> bytes | None:
    """GET, None on 403/404; the server's Retry-After (capped) on 429/503."""
    req = urllib.request.Request(url, headers={"User-Agent": "noema-research/0.1"})
    for k in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return None
            wait = int(e.headers.get("Retry-After") or 0) or 10 * 2**k
            if wait > p11.MAX_WAIT:
                raise RuntimeError(f"http {e.code} asks for {wait}s") from e
            log(f"http {e.code}, waiting {wait}s")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            wait = 10 * 2**k
            log(f"{type(e).__name__}, waiting {wait}s")
        time.sleep(wait)
    return None


def tool_meta(ids: list[str]) -> dict[str, dict]:
    meta = {}
    for k in range(0, len(ids), 40):
        q = urllib.parse.urlencode(
            {
                "filter": "openalex_id:" + "|".join(ids[k : k + 40]),
                "per_page": 50,
                "select": "id,display_name,publication_year,authorships",
            }
        )
        for w in json.loads(p11.get(OPENALEX + "?" + q))["results"]:
            au = w.get("authorships") or []
            name = (au[0].get("author") or {}).get("display_name") if au else None
            meta[w["id"].rsplit("/", 1)[-1]] = {
                "title": w.get("display_name") or "",
                "year": w.get("publication_year"),
                "first_author": name,
            }
        time.sleep(1)
    return meta


# ---------------------------------------------------------------- sample
def sample(out: Path, smoke: bool) -> None:
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
    H, o0, o1 = (2012, 2013, 2016) if smoke else p13.WINDOW
    min_cites, min_pos = (2, 1) if smoke else (p11.MIN_CITES, p11.MIN_POSITIVE)
    texts = [p["title"] + ". " + p["abstract"] for p in P]
    vec = TfidfVectorizer(
        sublinear_tf=True, min_df=1 if smoke else 5, max_df=0.5, stop_words="english"
    )
    vec.fit([t for t, p in zip(texts, P, strict=True) if p["year"] <= H])
    w = p11.window_cells(P, H, o0, o1, vec.transform(texts), min_cites, min_pos)
    rung, _ = p12.ladder(P, H, w)
    cold = np.nonzero(rung == 5)[0]
    jump = w["pos"][cold]
    nt = len(w["tools"])
    scores = p13.oof_scores(
        w["X"][cold], jump, w["tool_row"][cold], nt, np.random.default_rng(p13.SEED)
    )
    top = np.zeros(len(cold), bool)
    top[np.argsort(-scores[1], kind="stable")[:TOP]] = True
    hits = int((top & jump).sum())
    log(f"{len(cold):,} cold cells, {int(jump.sum())} cold jumps, {hits} in the top {TOP}")
    if not smoke and hits != EXPECTED_TOP_HITS:
        raise RuntimeError(f"top-{TOP} hits {hits}, Phase 13 had {EXPECTED_TOP_HITS}")

    rng = np.random.default_rng(SEED)
    n = 2 if smoke else PER_GROUP
    pools = {
        "G1": cold[top & jump],
        "G2": cold[~top & jump],
        "G3": np.nonzero((rung == 1) & w["pos"])[0],
    }
    cells = []
    for g, pool in pools.items():
        for k in rng.permutation(pool)[:n]:
            cells.append(
                {
                    "group": g,
                    "tool": w["tools"][w["tool_row"][k]],
                    "area": w["areas"][w["area_col"][k]],
                    "outcome_papers": int(w["outcome"][k]),
                }
            )
    for c in cells:
        citing = [
            i
            for i, p in enumerate(P)
            if p["area"] == c["area"] and o0 <= p["year"] <= o1 and c["tool"] in p["refs"]
        ]
        c["papers"] = [P[i]["id"] for i in rng.permutation(citing)[:PAPERS_PER_CELL]]
    meta = tool_meta(sorted({c["tool"] for c in cells}))
    by_id = {p["id"]: p for p in P}
    del P, w, texts, vec

    n_papers = sum(len(c["papers"]) for c in cells)
    log(f"{len(cells)} cells, {n_papers} citing papers to fetch")
    done = 0
    with gzip.open(out / "contexts.jsonl.gz", "wt") as f:
        for ci, c in enumerate(cells):
            m = meta.get(c["tool"], {})
            tw = title_words(m.get("title", ""))
            surname = words((m.get("first_author") or "").split(" ")[-1])
            for aid in c["papers"]:
                row = {
                    "cell": ci,
                    **{k: c[k] for k in ("group", "tool", "area", "outcome_papers")},
                    "tool_title": m.get("title"),
                    "tool_year": m.get("year"),
                    "tool_first_author": m.get("first_author"),
                    "paper": aid,
                    "paper_title": by_id[aid]["title"],
                }
                blob = fetch(EPRINT + aid)
                time.sleep(3)
                src = unpack(blob) if blob else None
                if src is None:
                    row["status"] = "no source"
                else:
                    body, bib = src
                    keys = {k for k, e in bib_entries(body, bib) if matches(e, tw, surname)}
                    ctx = contexts(body, keys) if keys else []
                    row["status"] = "ok" if ctx else ("no citation" if keys else "no match")
                    row["contexts"] = ctx
                f.write(json.dumps(row) + "\n")
                done += 1
                if done % 25 == 0:
                    log(f"fetched {done} / {n_papers}")
    log(f"wrote {out / 'contexts.jsonl.gz'}")


# ---------------------------------------------------------------- batches
def batches(out: Path) -> None:
    with gzip.open(out / "contexts.jsonl.gz", "rt") as f:
        rows = [json.loads(line) for line in f]
    ok = [r for r in rows if r["status"] == "ok"]
    order = np.random.default_rng(SEED + 1).permutation(len(ok))
    d = out / "judge"
    d.mkdir(exist_ok=True)
    key = {}
    items = []
    for j, i in enumerate(order):
        r = ok[i]
        item = f"i{j:04d}"
        key[item] = {"paper": r["paper"], "cell": r["cell"]}
        items.append(
            {
                "item": item,
                "tool": r["tool_title"],
                "tool_first_author": r["tool_first_author"],
                "tool_year": r["tool_year"],
                "citing_paper": r["paper_title"],
                "citing_area": r["area"],
                "contexts": r["contexts"],
            }
        )
    for b in range(0, len(items), BATCH):
        (d / f"batch-{b // BATCH:02d}.json").write_text(json.dumps(items[b : b + BATCH], indent=1))
    (d / "key.json").write_text(json.dumps(key, indent=1))
    log(f"{len(items)} items in {(len(items) + BATCH - 1) // BATCH} batches")


# ---------------------------------------------------------------- score
def kappa(a: list[str], b: list[str]) -> float:
    labels = sorted(set(a) | set(b))
    po = np.mean([x == y for x, y in zip(a, b, strict=True)])
    pe = sum((a.count(c) / len(a)) * (b.count(c) / len(b)) for c in labels)
    return float((po - pe) / (1 - pe)) if pe < 1 else 1.0


def score(out: Path) -> None:
    with gzip.open(out / "contexts.jsonl.gz", "rt") as f:
        rows = [json.loads(line) for line in f]
    d = out / "judge"
    key = json.loads((d / "key.json").read_text())
    lab = {}
    for judge in ("A", "B"):
        lab[judge] = {}
        for p in sorted(d.glob(f"labels-{judge}-*.json")):
            for x in json.loads(p.read_text()):
                lab[judge][x["item"]] = x["label"]
    items = sorted(key)
    missing = [i for i in items if i not in lab["A"] or i not in lab["B"]]
    if missing:
        raise RuntimeError(f"{len(missing)} items lack a label from both judges")
    by_paper = {(key[i]["cell"], key[i]["paper"]): i for i in items}

    cells: dict[int, dict] = {}
    for r in rows:
        c = cells.setdefault(r["cell"], {"group": r["group"], "papers": [], "row": r})
        c["papers"].append(r)
    report: dict = {"seed": SEED, "boot": BOOT, "coverage": {}, "labels": {}}
    real: dict[str, list[bool]] = {"G1": [], "G2": [], "G3": []}
    examples = []
    for g in real:
        cs = [c for c in cells.values() if c["group"] == g]
        papers = [p for c in cs for p in c["papers"]]
        report["coverage"][g] = {
            "cells": len(cs),
            "papers": len(papers),
            **{s: sum(p["status"] == s for p in papers) for s in ("ok", "no source", "no match")},
            "no citation": sum(p["status"] == "no citation" for p in papers),
        }
        counts = {"used": 0, "passing": 0, "unclear": 0, "judges disagree": 0}
        for c in cs:
            judged = [p for p in c["papers"] if p["status"] == "ok"]
            if not judged:
                continue
            used = False
            for p in judged:
                i = by_paper[(p["cell"], p["paper"])]
                a, b = lab["A"][i], lab["B"][i]
                if a != b:
                    counts["judges disagree"] += 1
                else:
                    counts[a] += 1
                if a == b == "used":
                    used = True
                    if g == "G1" and len(examples) < 5:
                        examples.append(
                            {
                                "tool": p["tool_title"],
                                "area": p["area"],
                                "paper": p["paper"],
                                "paper_title": p["paper_title"],
                                "context": p["contexts"][0],
                            }
                        )
            real[g].append(used)
        report["coverage"][g]["judged_cells"] = len(real[g])
        report["labels"][g] = counts
    share = {g: float(np.mean(v)) if v else None for g, v in real.items()}
    report["share_real_work"] = share

    n1 = len(real["G1"])
    if n1 < MIN_JUDGED_G1:
        v1 = "underpowered"
    elif share["G1"] >= 0.5:
        v1 = "the hits mostly did real work"
    elif share["G1"] >= 0.25:
        v1 = "mixed: a real minority"
    else:
        v1 = "mostly passing mentions"
    report["H1"] = {"share": share["G1"], "judged_cells": n1, "verdict": v1}

    rng = np.random.default_rng(SEED + 2)

    def diff(g, h):
        x, y = np.array(real[g], float), np.array(real[h], float)
        draws = [rng.choice(x, len(x)).mean() - rng.choice(y, len(y)).mean() for _ in range(BOOT)]
        lo, hi = np.percentile(draws, [2.5, 97.5])
        return {"difference": float(x.mean() - y.mean()), "ci95": [float(lo), float(hi)]}

    report["H2"] = diff("G1", "G2")
    lo, hi = report["H2"]["ci95"]
    report["H2"]["verdict"] = (
        "G1 higher" if lo > 0 else "G1 lower" if hi < 0 else "no measurable difference"
    )
    report["G1_minus_G3"] = diff("G1", "G3")
    a = [lab["A"][i] for i in items]
    b = [lab["B"][i] for i in items]
    report["agreement"] = {
        "items": len(items),
        "share": float(np.mean([x == y for x, y in zip(a, b, strict=True)])),
        "kappa": kappa(a, b),
    }
    report["examples_G1_real_work"] = examples
    (out / "phase14.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"H1 {report['H1']}; H2 {report['H2']}; agreement {report['agreement']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("stage", choices=["sample", "batches", "score"])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    {"sample": lambda: sample(args.out, args.smoke), "batches": lambda: batches(args.out)}.get(
        args.stage, lambda: score(args.out)
    )()
    return 0


if __name__ == "__main__":
    sys.exit(main())
