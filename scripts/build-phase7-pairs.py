#!/usr/bin/env python3
"""build-phase7-pairs.py -- phase 7's test population, fixed before any picker is trained.

Fixed in results/phase-7-lemma-selection/README.md. Walks the upper triangle
of phase 3's union and keeps every pair that is

    hard          eligible (no shared rare 2024 lemma), cross-area, and
                  state-vocabulary Jaccard < 5% -- phase 3's definitions
    new           not co-cited by any 2024 theorem
    placeable     both endpoints hold a 2024 statement vector

with flags per pair: positive (a 2026 connector cites both), generic endpoint
(cited by > 200 theorems in 2024), and pool (part 3's pool: neither endpoint
generic, not co-cited in 2026, both endpoints present in the 2026 graph).

Pairs stream to disk in row blocks, so the laptop holds one block at a time.

    scripts/build-phase7-pairs.py --vectors-2024 b-statements-2024.npz \
        --out outputs/phase-7-lemma-selection/population
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import forward_blocks as fb  # noqa: E402

_spec = importlib.util.spec_from_file_location("s6", ROOT / "scripts/select-phase6-pairs.py")
s6 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s6)

E24, E26, UNION, MAP_B = s6.E24, s6.E26, s6.UNION, s6.MAP_B
PILOT6 = ROOT / "results/phase-6-conjecture-placement/pilot/pairs.jsonl"
GENERIC = 200
BLOCK = 256


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--vectors-2024", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    corpus = fb.load_corpus(
        MAP_B / "centroids.npz", UNION / "new-connectors.json", UNION / "states-union.jsonl.gz",
        UNION / "selection-modules.json.gz", s6.a3.EDGES,
    )  # fmt: skip
    names, n = corpus.names, corpus.n
    index = {nm: i for i, nm in enumerate(names)}
    have_vec = set(str(x) for x in np.load(args.vectors_2024)["names"])
    placeable = np.array([nm in have_vec for nm in names])
    deg = s6.in_degree(E24, set(names))
    generic = np.array([deg[nm] > GENERIC for nm in names])
    with gzip.open(E26, "rt") as f:
        alive = {json.loads(line)["theorem"] for line in f}
    gone = np.array([nm not in alive for nm in names])
    co24 = s6.joined_codes(E24, index)
    co26 = s6.joined_codes(E26, index)
    positive = np.unique(corpus.pos_i.astype(np.int64) * n + corpus.pos_j)
    pilot6 = []
    with open(PILOT6) as f:
        for p in map(json.loads, f):
            i, j = sorted((index[p["a"]], index[p["b"]]))
            pilot6.append(i * n + j)
    pilot6 = np.unique(np.array(pilot6, np.int64))
    print(f"corpus {n:,} | placeable {placeable.sum():,} | generic {generic.sum():,} | "
          f"absent 2026 {gone.sum():,} | co-cited 2024 {len(co24):,} | 2026 {len(co26):,} | "
          f"eligible positives {len(positive):,}  [{time.time() - t0:.0f}s]",
          flush=True)  # fmt: skip

    no_vec = ~placeable
    fi = open(args.out / "i.int32", "wb")
    fj = open(args.out / "j.int32", "wb")
    ff = open(args.out / "flags.uint8", "wb")
    counts = dict(hard=0, hard_cocited_2024=0, hard_unplaceable=0)
    total = 0
    for a0 in range(0, n, BLOCK):
        a1 = min(a0 + BLOCK, n)
        ok = s6.pool_mask(corpus, np.zeros(n, bool), a0, a1)  # hard (eligible, cross, low)
        ok &= np.arange(n)[None, :] > np.arange(a0, a1)[:, None]
        r, c = np.nonzero(ok)
        r = (r + a0).astype(np.int64)
        c = c.astype(np.int64)
        counts["hard"] += len(r)
        code = r * n + c
        was = np.isin(code, co24)
        unpl = no_vec[r] | no_vec[c]
        counts["hard_cocited_2024"] += int(was.sum())
        counts["hard_unplaceable"] += int((unpl & ~was).sum())
        keep = ~was & ~unpl
        r, c, code = r[keep], c[keep], code[keep]
        pos = np.isin(code, positive)
        gen = generic[r] | generic[c]
        pool = ~gen & ~np.isin(code, co26) & ~gone[r] & ~gone[c] & ~np.isin(code, pilot6)
        flags = pos.astype(np.uint8) | (gen.astype(np.uint8) << 1) | (pool.astype(np.uint8) << 2)
        r.astype(np.int32).tofile(fi)
        c.astype(np.int32).tofile(fj)
        flags.tofile(ff)
        total += len(r)
        if (a0 // BLOCK) % 10 == 0:
            print(f"rows {a1:,}/{n:,}  kept {total:,}  [{time.time() - t0:.0f}s]", flush=True)
    for fh in (fi, fj, ff):
        fh.close()

    flags = np.fromfile(args.out / "flags.uint8", dtype=np.uint8)
    pos, gen, pool = flags & 1, (flags >> 1) & 1, (flags >> 2) & 1
    summary = {
        "seed_note": "no randomness; the population is fixed by the rules alone",
        "corpus": n, "placeable_endpoints": int(placeable.sum()),
        "generic_endpoints": int(generic.sum()), "absent_2026_endpoints": int(gone.sum()),
        **counts,
        "population": int(total), "positives": int(pos.sum()),
        "non_generic_population": int((gen == 0).sum()),
        "non_generic_positives": int(((gen == 0) & (pos == 1)).sum()),
        "pool": int(pool.sum()),
        "pool_positives_must_be_zero": int(((pool == 1) & (pos == 1)).sum()),
        "flags": "bit 0 positive, bit 1 generic endpoint, bit 2 part-3 pool",
    }  # fmt: skip
    assert summary["pool_positives_must_be_zero"] == 0
    (args.out / "names.json").write_text(json.dumps(names))
    (args.out / "population.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=1))
    print(f"done [{time.time() - t0:.0f}s]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
