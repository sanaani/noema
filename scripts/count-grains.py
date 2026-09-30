#!/usr/bin/env python3
"""count-grains.py -- how many cold jumps at a finer grain than arXiv's 28 areas? (sizing)

No model scores. Phase 13's window (history <= 2006, outcome 2007-2021), cells
and ladder, with a paper's area taken from four labellings in turn:

    arxiv        primary arXiv category (Phase 13, 28 areas; a check: 728 / 126)
    msc2         first MSC code, two digits (papers without MSC are dropped)
    oa_subfield  OpenAlex primary topic's subfield (papers without topics dropped)
    oa_topic     OpenAlex primary topic (about 4,500 topics across all science)

A paper's secondary labels (for the shared-paper rung) are its other codes or
topics at the same grain. For each grain: areas, popular tools, cells per rung,
cold jumps (>= 2 outcome papers) and cold cells that took hold (>= 5), and for
each landmark paper, which of its references form a cell and on which rung.

A grain is large enough for a Phase 13 rerun if it has at least 600 cold
jumps and 150 that took hold (Phase 13's power targets, 400 and 100, plus 50%).

    topics  OpenAlex topics from the parquet snapshot -> topics.jsonl.gz
    count   the table above                           -> grains.json

    scripts/count-grains.py topics --out DIR --files works-files.txt [--smoke]
    scripts/count-grains.py count  --out DIR [--smoke]
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


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


p11, p12 = load("run-phase11"), load("run-phase12")
log = p11.log
H, O0, O1 = 2006, 2007, 2021
ENOUGH_JUMPS, ENOUGH_HOLD = 600, 150
GRAINS = ("arxiv", "msc2", "oa_subfield", "oa_topic")
MSC = re.compile(r"\b(\d{2})[A-Z\-]")


# ---------------------------------------------------------------- topics
def topics(out: Path, files: Path, smoke: bool) -> None:
    import duckdb

    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        papers = [json.loads(line) for line in f]
    owner: dict[str, int] = {}
    arxiv_doi = set()
    for i, p in enumerate(papers):
        d = "10.48550/arxiv." + p["id"].lower()
        owner[d] = i
        arxiv_doi.add(d)
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
    found: dict[int, dict] = {}
    for k in range(0, len(paths), 20):
        urls = [p11.SNAPSHOT + p for p in paths[k : k + 20]]
        rows = con.execute(
            "SELECT lower(w.doi), list_transform(w.topics, x -> x.id), "
            "list_transform(w.topics, x -> x.subfield.id) "
            "FROM read_parquet(?, union_by_name = true) w JOIN want ON lower(w.doi) = want.doi",
            [urls],
        ).fetchall()
        for doi, tids, sids in rows:
            d = doi.replace("https://doi.org/", "")
            i = owner[d]
            tids = [t.rsplit("/", 1)[-1] for t in tids or () if t]
            sids = [s.rsplit("/", 1)[-1] for s in sids or () if s]
            if not tids:
                continue
            # the arXiv record's topics win over the journal record's
            if i not in found or d in arxiv_doi:
                found[i] = {"topics": tids, "subfields": sids}
        log(f"topics {min(k + 20, len(paths)):,} / {len(paths):,} files, {len(found):,} papers")
    if smoke and not found:
        raise RuntimeError("smoke: the join found no topics in the newest snapshot files")
    with gzip.open(out / "topics.jsonl.gz", "wt") as f:
        for i, p in enumerate(papers):
            f.write(json.dumps({"id": p["id"], **found.get(i, {"topics": [], "subfields": []})}))
            f.write("\n")
    log(f"topics done: {len(found):,} of {len(papers):,} papers with topics")


# ---------------------------------------------------------------- count
def relabel(P: list[dict], grain: str) -> list[dict]:
    """Papers with an area at this grain, area and categories replaced; the rest dropped."""
    if grain == "arxiv":
        return P
    out = []
    for p in P:
        if grain == "msc2":
            codes = list(dict.fromkeys(MSC.findall(p["msc"] or "")))
        elif grain == "oa_subfield":
            codes = list(dict.fromkeys(p["subfields"]))
        else:
            codes = p["topics"]
        if codes:
            out.append({**p, "area": codes[0], "categories": codes})
    return out


def count(out: Path, smoke: bool) -> None:
    import scipy.sparse as sp

    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        P = [json.loads(line) for line in f]
    for p in P:
        p.pop("abstract")
    with (
        gzip.open(out / "refs.jsonl.gz", "rt") as f,
        gzip.open(out / "authors.jsonl.gz", "rt") as g,
        gzip.open(out / "topics.jsonl.gz", "rt") as h,
    ):
        for p, r, a, t in zip(P, *(map(json.loads, x) for x in (f, g, h)), strict=True):
            assert p["id"] == r["id"] == a["id"] == t["id"]
            p["refs"], p["openalex"], p["authors"] = r["refs"], r["openalex"], a["authors"]
            p["topics"], p["subfields"] = t["topics"], t["subfields"]
    if smoke:
        P = [p for k, p in enumerate(P) if k % 20 == 0]
    by_id = {p["id"]: p for p in P}
    report: dict = {"window": [H, O0, O1], "smoke": smoke, "grains": {}}
    for grain in GRAINS:
        Q = relabel(P, grain)
        hist = sum(p["year"] <= H for p in Q)
        if hist < 2:
            log(f"{grain}: {hist} history papers, skipped")
            continue
        w = p11.window_cells(
            Q,
            H,
            O0,
            O1,
            sp.csr_matrix((len(Q), 1)),
            2 if smoke else p11.MIN_CITES,
            p11.MIN_POSITIVE,
        )
        if not len(w["tool_row"]):
            log(f"{grain}: no cells, skipped")
            continue
        rung, lad = p12.ladder(Q, H, w)
        outc = w["outcome"]
        cold = rung == 5
        rep = {
            "papers": len(Q),
            "history_papers": hist,
            "areas": len(w["areas"]),
            "popular_tools": len(w["tools"]),
            "cells": int(len(rung)),
            "rungs": {
                f"{k} {p12.RUNGS[k]}": {
                    "cells": int((rung == k).sum()),
                    "jumps": int(((rung == k) & (outc >= 2)).sum()),
                    "took_hold": int(((rung == k) & (outc >= 5)).sum()),
                }
                for k in p12.RUNGS
            },
            "cold_jumps": int((cold & (outc >= 2)).sum()),
            "cold_took_hold": int((cold & (outc >= 5)).sum()),
            "ladder": lad,
        }
        rep["large_enough"] = bool(
            rep["cold_jumps"] >= ENOUGH_JUMPS and rep["cold_took_hold"] >= ENOUGH_HOLD
        )
        ti = {t: r for r, t in enumerate(w["tools"])}
        ai = {a: c for c, a in enumerate(w["areas"])}
        cell = {
            (r, c): k for k, (r, c) in enumerate(zip(w["tool_row"], w["area_col"], strict=True))
        }
        qid = {p["id"]: p for p in Q}
        land = {}
        for aid, label in p11.LANDMARKS.items():
            p = qid.get(aid)
            if p is None:
                land[aid] = {
                    "paper": label,
                    "status": "no label at this grain" if aid in by_id else "missing",
                }
                continue
            cells = []
            for t in p["refs"]:
                k = cell.get((ti.get(t), ai.get(p["area"])))
                if k is not None:
                    cells.append({"tool": t, "rung": int(rung[k]), "outcome_papers": int(outc[k])})
            land[aid] = {
                "paper": label,
                "area": p["area"],
                "references": len(p["refs"]),
                "popular_references": sum(t in ti for t in p["refs"]),
                "cells": sorted(cells, key=lambda c: c["rung"]),
            }
        rep["landmarks"] = land
        report["grains"][grain] = rep
        log(
            f"{grain}: {rep['areas']:,} areas, {rep['popular_tools']:,} tools, "
            f"{rep['cells']:,} cells; cold jumps {rep['cold_jumps']}, took hold "
            f"{rep['cold_took_hold']}; large enough: {rep['large_enough']}; landmark cells "
            + ", ".join(
                f"{a}: {collections.Counter(c['rung'] for c in v.get('cells', []))}"
                for a, v in land.items()
            )
        )
    (out / "grains.json").write_text(json.dumps(report, indent=1) + "\n")
    log(f"wrote {out / 'grains.json'}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("stage", choices=["topics", "count"])
    ap.add_argument("--files", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    topics(a.out, a.files, a.smoke) if a.stage == "topics" else count(a.out, a.smoke)
    return 0


if __name__ == "__main__":
    sys.exit(main())
