#!/usr/bin/env python3
"""pilot-corpus-sim.py — how many positives would a randomly sampled corpus yield?

The phase 2 sizing table extrapolates from phase 1's corpus, which was selected
theorem-by-theorem. Phase 2 plans to sample *files* uniformly instead, and a
random corpus may not connect like a selected one: random files carry a lot of
plumbing that nothing later cites.

That question does not need a capture. Whether a pair is a positive depends only
on which theorem *names* are in the corpus, so it can be answered from the two
committed edge lists alone -- no replay, no encoder, no GPU.

    positives = pairs (A,B) of corpus theorems, sharing no rare lemma in 2024,
                such that some theorem new in 2026 cites both.

Eligibility is checked only for pairs that are actually connected, which is a
few hundred checks rather than N^2. The eligible-pair denominator is estimated
from phase 1's measured ratio, since it is used only for the base rate.

    scripts/pilot-corpus-sim.py --trials 5
"""

from __future__ import annotations

import argparse
import collections
import gzip
import itertools
import json
import random

import numpy as np

from noema.paths import result_path

# Phase 1: 1,530,134 eligible of C(1797,2)=1,614,006.
ELIGIBLE_FRACTION = 1530134 / (1797 * 1796 / 2)
DF_LO, DF_HI = 2, 200


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--edges-2024", default=result_path("link-graph-v1/edges.jsonl.gz"))
    ap.add_argument("--edges-2026", required=True)
    ap.add_argument("--files", type=int, nargs="+", default=[25, 50, 100, 156, 250])
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument(
        "--stratify",
        action="store_true",
        help="allocate files across Mathlib areas in proportion to each area's file count, "
        "which cuts the draw-to-draw variance and guarantees cross-area coverage. It selects "
        "on file location only, never on the outcome, so it does not bias the label.",
    )
    ap.add_argument("--seed", type=int, default=20260922)
    ap.add_argument("--out")
    args = ap.parse_args()

    print("pass 1: citation frequencies over the 2024 library")
    df: collections.Counter[str] = collections.Counter()
    n2024 = 0
    with gzip.open(args.edges_2024, "rt") as f:
        for line in f:
            r = json.loads(line)
            df.update(set(r.get("deps") or ()))
            n2024 += 1
    rare = {c for c, k in df.items() if DF_LO <= k <= DF_HI}
    print(
        f"  {n2024:,} theorems, {len(df):,} cited constants, "
        f"{len(rare):,} rare (df {DF_LO}-{DF_HI})"
    )
    del df

    print("pass 2: per-theorem rare sets, and the file each theorem lives in")
    by_file: dict[str, list[str]] = collections.defaultdict(list)
    mod_of: dict[str, str] = {}
    rare_of: dict[str, frozenset[str]] = {}
    with gzip.open(args.edges_2024, "rt") as f:
        for line in f:
            r = json.loads(line)
            name = r["theorem"]
            by_file[r.get("module", "")].append(name)
            mod_of[name] = r.get("module", "")
            rare_of[name] = frozenset(set(r.get("deps") or ()) & rare)
    names_2024 = set(rare_of)
    files = sorted(by_file)
    print(f"  {len(files):,} files, {sum(len(v) for v in by_file.values()):,} theorems")

    print("pass 3: 2026 theorems new since 2024, keeping only their 2024-theorem citations")
    connectors: list[list[str]] = []
    with gzip.open(args.edges_2026, "rt") as f:
        for line in f:
            r = json.loads(line)
            if r["theorem"] in names_2024:
                continue
            cited = [d for d in (r.get("deps") or ()) if d in names_2024]
            if len(cited) >= 2:
                connectors.append(sorted(set(cited)))
    print(f"  {len(connectors):,} new theorems citing >=2 theorems that existed in 2024")

    def area_of(module: str) -> str:
        parts = module.split(".")
        return parts[1] if len(parts) > 1 else module

    by_area: dict[str, list[str]] = collections.defaultdict(list)
    for m in files:
        by_area[area_of(m)].append(m)

    def draw(rng: random.Random, k: int) -> list[str]:
        if not args.stratify:
            return rng.sample(files, min(k, len(files)))
        picked: list[str] = []
        areas = sorted(by_area)
        # Largest-remainder allocation, so small areas are not rounded away.
        quota = {a: len(by_area[a]) * k / len(files) for a in areas}
        base = {a: int(quota[a]) for a in areas}
        left = k - sum(base.values())
        for a in sorted(areas, key=lambda a: quota[a] - base[a], reverse=True)[:left]:
            base[a] += 1
        for a in areas:
            n = min(base[a], len(by_area[a]))
            if n:
                picked.extend(rng.sample(by_area[a], n))
        return picked

    rng = random.Random(args.seed)
    rows = []
    print(
        f"\n{'files':>6} {'theorems':>9} {'connectors':>11} {'pairs':>7} {'positives':>10} "
        f"{'cross-area':>11}"
    )
    for k in args.files:
        for t in range(args.trials):
            picked = draw(rng, k)
            corpus = {n for m in picked for n in by_file[m]}
            conn = 0
            pairs: set[tuple[str, str]] = set()
            for cited in connectors:
                inside = [c for c in cited if c in corpus]
                if len(inside) < 2:
                    continue
                conn += 1
                pairs.update(itertools.combinations(sorted(inside), 2))
            elig = [(a, b) for a, b in pairs if not (rare_of[a] & rare_of[b])]
            pos = len(elig)
            xa = sum(1 for a, b in elig if area_of(mod_of[a]) != area_of(mod_of[b]))
            n = len(corpus)
            rows.append(
                {
                    "files": k,
                    "trial": t,
                    "theorems": n,
                    "connectors": conn,
                    "pairs": len(pairs),
                    "positives": pos,
                    "cross_area": xa,
                }
            )
            print(f"{k:>6} {n:>9,} {conn:>11,} {len(pairs):>7,} {pos:>10,} {xa:>11,}")

    print("\nsummary over trials -- plan against the worst draw, not the mean")
    print(
        f"{'files':>6} {'theorems':>9} {'pos mean':>9} {'pos min':>8} "
        f"{'xarea mean':>11} {'xarea min':>10}"
    )
    for k in args.files:
        sel = [r for r in rows if r["files"] == k]
        n = float(np.mean([r["theorems"] for r in sel]))
        pp = [r["positives"] for r in sel]
        xx = [r["cross_area"] for r in sel]
        print(
            f"{k:>6} {n:>9,.0f} {np.mean(pp):>9,.0f} {min(pp):>8,} "
            f"{np.mean(xx):>11,.0f} {min(xx):>10,}"
        )

    k1 = 53 / (1797.0**2)
    print(f"\nphase 1 (selected corpus, dependency label): k = {k1:.3e}")
    print("If the random-file k is lower, a uniformly sampled corpus connects less")
    print("densely than phase 1's, and the file counts in the sizing table are too low.")

    if args.out:
        from pathlib import Path

        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(
                {"rows": rows, "phase1_k": k1, "eligible_fraction": ELIGIBLE_FRACTION}, indent=2
            )
            + "\n"
        )
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
