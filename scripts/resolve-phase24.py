#!/usr/bin/env python3
"""resolve-phase24.py -- pre-2005 eligibility of the curated breakthrough list.

results/phase-24-curated-backtest/openalex-ids.json holds each curated work's OpenAlex ids: works
whose title matches (normalised prefix of 30 characters, or the whole title if
shorter) within 3 years of the curated year, from OpenAlex title search. The
work used is the matching id with the most corpus citers up to 2005.

Uses papers up to 2005 only (no outcomes, no scores). Eligible: at least 5
citers up to 2005 and none whose primary area is the target. Writes
results/phase-24-curated-backtest/eligible.json.

    scripts/resolve-phase24.py [DATA_DIR]
"""

from __future__ import annotations

import collections
import gzip
import json
import sys
from pathlib import Path

CUTOFF = 2005
MIN_CITERS = 5


def main() -> int:
    data = Path(sys.argv[1] if len(sys.argv) > 1 else "outputs/phase-11-tool-area-grid/data")
    curated = json.loads(Path("results/phase-24-curated-backtest/curated.json").read_text())
    ids = json.loads(Path("results/phase-24-curated-backtest/openalex-ids.json").read_text())
    want = {w for v in ids.values() for w in v}
    year, area = {}, {}
    with gzip.open(data / "papers.jsonl.gz", "rt") as f:
        for line in f:
            p = json.loads(line)
            year[p["id"]], area[p["id"]] = p["year"], p["area"]
    cit = collections.defaultdict(list)
    with gzip.open(data / "refs.jsonl.gz", "rt") as f:
        for line in f:
            r = json.loads(line)
            if year[r["id"]] <= CUTOFF:
                for w in r["refs"]:
                    if w in want:
                        cit[w].append(area[r["id"]])
    out = []
    for x in curated:
        c = ids[x["work"]]
        best = max(c, key=lambda w: len(cit[w]), default=None)
        n = len(cit[best]) if best else 0
        tgt = sum(a == x["target"] for a in cit[best]) if best else 0
        ok = n >= MIN_CITERS and tgt == 0
        print(
            f"{'ELIGIBLE' if ok else 'out':8} {best} {n:4} {tgt:2}",
            f"{x['work'][:50]} -> {x['target']}",
        )
        out.append(
            x
            | {"openalex": best, "citers_to_2005": n, "target_citers_to_2005": tgt, "eligible": ok}
        )
    Path("results/phase-24-curated-backtest/eligible.json").write_text(
        json.dumps(out, indent=1) + "\n"
    )
    print(sum(o["eligible"] for o in out), "eligible of", len(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
