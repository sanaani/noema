#!/usr/bin/env python3
"""bibliography-spread.py -- how far do a paper's references reach, by MSC code?

For each landmark: its references' MSC codes (from landmarks.json), and a
baseline of ordinary zbMATH papers with the same primary 2-digit MSC area and
publication year, whose reference lists zbMATH has already coded.

Per paper, over references with an MSC code (a reference's area = its first code):
  far_share   share of references whose 2-digit area is none of the paper's own
  diversity   mean pairwise distance between references: 0 same 3-character
              code, 0.5 same 2-digit area, 1 different area (Rao-Stirling, equal weights)
  areas       distinct 2-digit areas among the references

    scripts/bibliography-spread.py landmarks.json OUT.json
"""

from __future__ import annotations

import itertools
import json
import sys
import time
import urllib.parse
import urllib.request

ZB = "https://api.zbmath.org/v1/document/_search?"
BASELINE_PAGES = 3  # 100 papers a page
MIN_REFS = 5
YEAR = {  # journal publication year in zbMATH
    "1603.04246": 2017,
    "1603.06518": 2017,
    "1605.01506": 2017,
    "1605.09223": 2017,
    "1907.00847": 2019,
}


def get(url):
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers={"accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except OSError:
            time.sleep(5 * (k + 1))
    return {}


def dist(a, b):
    if a[:3] == b[:3]:
        return 0.0
    return 0.5 if a[:2] == b[:2] else 1.0


def spread(own, codes):
    own2 = {c[:2] for c in own}
    if len(codes) < MIN_REFS or not own2:
        return None
    pairs = list(itertools.combinations(codes, 2))
    return {
        "references": len(codes),
        "far_share": sum(c[:2] not in own2 for c in codes) / len(codes),
        "diversity": sum(dist(a, b) for a, b in pairs) / len(pairs),
        "areas": len({c[:2] for c in codes}),
    }


def baseline(area, year):
    rows = []
    for page in range(BASELINE_PAGES):
        q = {"search_string": f"cc:{area} py:{year}", "results_per_page": 100, "page": page}
        d = get(ZB + urllib.parse.urlencode(q))
        res = d.get("result") or []
        for r in res:
            own = [m["code"] for m in r.get("msc") or []]
            if not own or own[0][:2] != area:
                continue
            codes = [
                ((x.get("zbmath") or {}).get("msc") or [None])[0] for x in r.get("references") or []
            ]
            s = spread(own, [c for c in codes if c])
            if s:
                rows.append(s)
        time.sleep(1)
        if len(res) < 100:
            break
    return rows


def main() -> int:
    lm = json.load(open(sys.argv[1]))
    out = {}
    for aid, v in lm.items():
        own = v["msc"]
        if aid == "1907.00847" and not own:
            own = ["05C50"]
        codes = [r["msc"][0] for r in v["references"] if r["msc"]]
        s = spread(own, codes)
        area = own[0][:2]
        base = baseline(area, YEAR[aid])
        pct = {
            k: sum(b[k] < s[k] for b in base) / len(base) if base else None
            for k in ("far_share", "diversity", "areas")
        }
        refs_by_area = {}
        for r in v["references"]:
            if r["msc"]:
                refs_by_area.setdefault(r["msc"][0][:2], []).append(r["title"])
        out[aid] = {
            "paper": v["paper"],
            "own_msc": own,
            "landmark": s,
            "baseline_papers": len(base),
            "baseline_median": {
                k: sorted(b[k] for b in base)[len(base) // 2] if base else None
                for k in ("far_share", "diversity", "areas")
            },
            "percentile_vs_baseline": pct,
            "references_by_area": refs_by_area,
        }
        print(
            f"{v['paper']}: own {own}; far {s['far_share']:.2f} (pct {pct['far_share']}), "
            f"diversity {s['diversity']:.2f} (pct {pct['diversity']}), areas {s['areas']} "
            f"(pct {pct['areas']}), baseline n={len(base)}",
            flush=True,
        )
    json.dump(out, open(sys.argv[2], "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
