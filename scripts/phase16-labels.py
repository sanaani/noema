#!/usr/bin/env python3
"""phase16-labels.py -- OpenAlex metadata for Phase 15's tools and topics.

Metadata only (titles, types, fields); no citation outcomes are read.

    scripts/phase16-labels.py DATA_DIR OUT_DIR
"""

from __future__ import annotations

import collections
import gzip
import json
import sys
import time
import urllib.request
from pathlib import Path

API = "https://api.openalex.org"
MIN_CITES, HISTORY_END = 20, 2006


def fetch(kind, ids, select):
    got = {}
    for i in range(0, len(ids), 100):
        chunk = ids[i : i + 100]
        key = "openalex" if kind == "works" else "id"
        url = f"{API}/{kind}?per_page=100&select={select}&filter={key}:" + "|".join(chunk)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    d = json.load(r)
                break
            except OSError:
                time.sleep(2 * (attempt + 1))
        else:
            raise SystemExit(f"failed: {url[:120]}")
        for x in d["results"]:
            got[x["id"].rsplit("/", 1)[1]] = x
        time.sleep(0.2)
    return got


def main() -> int:
    data, out = Path(sys.argv[1]), Path(sys.argv[2])
    citers = collections.Counter()
    topics = set()
    with (
        gzip.open(data / "papers.jsonl.gz", "rt") as f,
        gzip.open(data / "refs.jsonl.gz", "rt") as g,
        gzip.open(data / "topics.jsonl.gz", "rt") as h,
    ):
        for p, r, t in zip(*(map(json.loads, x) for x in (f, g, h)), strict=True):
            if not t["topics"]:
                continue
            topics.update(t["topics"])
            if p["year"] <= HISTORY_END:
                citers.update(r["refs"])
    tools = sorted(t for t, c in citers.items() if c >= MIN_CITES)
    print(f"{len(tools)} tools, {len(topics)} topics", flush=True)
    w = fetch("works", tools, "id,display_name,type,publication_year,authorships")
    rows = {
        t: {
            "found": t in w,
            "title": w[t]["display_name"] if t in w else None,
            "type": w[t]["type"] if t in w else None,
            "year": w[t]["publication_year"] if t in w else None,
            "authors": len(w[t]["authorships"]) if t in w else None,
        }
        for t in tools
    }
    (out / "tools.json").write_text(json.dumps(rows, indent=1) + "\n")
    tp = fetch("topics", sorted(topics), "id,display_name,subfield,field,domain")
    rows = {
        t: {
            "name": x["display_name"],
            "subfield": x["subfield"]["display_name"],
            "field": x["field"]["display_name"],
            "domain": x["domain"]["display_name"],
        }
        for t, x in tp.items()
    }
    (out / "topic-fields.json").write_text(json.dumps(rows, indent=1) + "\n")
    print(
        f"{sum(r['found'] for r in json.loads((out / 'tools.json').read_text()).values())} "
        f"tools found, {len(rows)} topics found"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
