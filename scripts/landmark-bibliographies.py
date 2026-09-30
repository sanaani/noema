#!/usr/bin/env python3
"""landmark-bibliographies.py -- each landmark paper's references, tagged with zbMATH MSC codes.

References come from OpenAlex: the union of the paper's arXiv-DOI and journal-DOI
records, as saved in Phase 11's refs.jsonl.gz. Huang's paper has none in
OpenAlex, so its references are parsed from its arXiv LaTeX bibliography. Each
cited work is matched in zbMATH Open by DOI, else by title and year; its MSC
codes are the reviewers' own classification.

    scripts/landmark-bibliographies.py REFS.jsonl.gz OUT.json
"""

from __future__ import annotations

import gzip
import io
import json
import re
import sys
import tarfile
import time
import urllib.parse
import urllib.request

LANDMARKS = {
    "1603.04246": "Viazovska, sphere packing in dimension 8",
    "1603.06518": "Cohn, Kumar, Miller, Radchenko, Viazovska, dimension 24",
    "1605.01506": "Croot, Lev, Pach",
    "1605.09223": "Ellenberg, Gijswijt",
    "1907.00847": "Huang, sensitivity conjecture",
}
OA = "https://api.openalex.org/works/"
ZB = "https://api.zbmath.org/v1/document/_search?"


def get(url: str) -> dict | None:
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers={"accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(3 * (k + 1))
        except OSError:
            time.sleep(3 * (k + 1))
    return None


def zb(query: str) -> list[dict]:
    d = get(ZB + urllib.parse.urlencode({"search_string": query, "results_per_page": 3}))
    time.sleep(0.5)
    return (d or {}).get("result") or []


def words(s: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", (s or "").lower()))


def match(work: dict) -> dict | None:
    doi = (work.get("doi") or "").replace("https://doi.org/", "")
    if doi:
        r = zb(f"doi:{doi}")
        if r:
            return r[0]
    title = work.get("display_name") or ""
    tw = words(title)
    if len(tw) < 2:
        return None
    q = " ".join(f"ti:{w}" for w in sorted(tw, key=len, reverse=True)[:5])
    for r in zb(q):
        rw = words((r.get("title") or {}).get("title"))
        if rw and len(tw & rw) >= 0.8 * len(tw):
            return r
    return None


def arxiv_bib(aid: str) -> list[dict]:
    """Titles from an arXiv paper's bibliography (\\bibitem ... \\emph{title} or "title")."""
    req = urllib.request.Request(
        "https://export.arxiv.org/e-print/" + aid, headers={"User-Agent": "noema-research"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        blob = r.read()
    try:
        blob = gzip.decompress(blob)
    except OSError:
        pass
    texts = []
    try:
        with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
            for m in tf.getmembers():
                if m.isfile() and m.name.endswith((".tex", ".bbl")):
                    texts.append(tf.extractfile(m).read().decode("utf-8", "replace"))
    except tarfile.TarError:
        texts.append(blob.decode("utf-8", "replace"))
    out = []
    for item in re.split(r"\\bibitem", "\n".join(texts))[1:]:
        m = (
            re.search(r"\\newblock\s*\{([^}]*)\}", item)
            or re.search(r"\\(?:emph|textit|it)\s*\{([^}]*)\}", item)
            or re.search(r"``([^']*)''", item)
        )
        yr = re.search(r"\b(19|20)\d{2}\b", item)
        out.append(
            {
                "display_name": m.group(1) if m else re.sub(r"\s+", " ", item)[:120],
                "publication_year": int(yr.group(0)) if yr else None,
            }
        )
    return out


def main() -> int:
    saved = {}
    with gzip.open(sys.argv[1], "rt") as f:
        for line in f:
            r = json.loads(line)
            if r["id"] in LANDMARKS:
                saved[r["id"]] = r["refs"]
    out = {}
    for aid, label in LANDMARKS.items():
        refs = saved.get(aid) or []
        own = zb(f"arxiv:{aid}")
        own = next((r for r in own if aid in json.dumps(r.get("links"))), own[0] if own else {})
        rows = []
        metas = [
            (w, get(OA + w + "?select=id,doi,display_name,publication_year,type") or {})
            for w in refs
        ]
        if not refs:
            metas = [(None, m) for m in arxiv_bib(aid)]
        for wid, meta in metas:
            z = match(meta)
            rows.append(
                {
                    "openalex": wid,
                    "title": meta.get("display_name"),
                    "year": meta.get("publication_year"),
                    "type": meta.get("type"),
                    "zbmath": z.get("identifier") if z else None,
                    "msc": [m["code"] for m in (z or {}).get("msc") or []],
                }
            )
        out[aid] = {
            "paper": label,
            "msc": [m["code"] for m in (own or {}).get("msc") or []],
            "references": rows,
        }
        tagged = sum(1 for r in rows if r["msc"])
        print(f"{aid} {label}: {len(rows)} references, {tagged} with MSC", flush=True)
    with open(sys.argv[2], "w") as f:
        json.dump(out, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
