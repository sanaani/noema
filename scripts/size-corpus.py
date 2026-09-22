#!/usr/bin/env python3
"""size-corpus.py — how big does the 2024 corpus have to be?

Phase 1's forward test rests on 17 positives. The question this answers is how
many theorems, and therefore how many Mathlib files, a phase 2 capture needs
before that number is large enough to argue from.

The whole thing turns on one fact: **positives scale as the square of the
corpus fraction, not linearly.** A connector only counts when a later theorem
cites *two* corpus theorems. Doubling the corpus roughly doubles the chance
each citation lands inside it, and a pair needs two of them, so the yield goes
up about fourfold. That cuts both ways -- it is why 1,797 theorems produced
only 17 positives, and why a corpus a few times larger produces hundreds
rather than tens.

    positives(N) ~= P1 * R * (N / N1)^2

`P1` and `N1` are phase 1's measured positives and corpus size, both read from
the committed artifacts. `R` is the only free parameter: how much more the
exact dependency label sees than the grep label it replaces. R=1 assumes the
text search already found everything, which it cannot have -- it structurally
cannot see a citation made under an `open` namespace or one whose target was
renamed. R=2 is the pessimistic planning number used here.

Everything else is measured:

    scripts/size-corpus.py                # the table
    scripts/size-corpus.py --target 1000  # files needed for a given yield
"""

from __future__ import annotations

import argparse
import collections
import gzip
import json

import numpy as np

from noema.paths import result_path


def phase1() -> dict[str, float]:
    """Phase 1's measured corpus, its file footprint, and its yield."""
    corpus = {
        str(n)
        for n in np.load(result_path("mathlib-forward-v1/centroids.npz"), allow_pickle=False)[
            "names"
        ]
    }
    module: dict[str, str] = {}
    per_module: collections.Counter[str] = collections.Counter()
    with gzip.open(result_path("link-graph-v1/edges.jsonl.gz"), "rt") as f:
        for line in f:
            r = json.loads(line)
            module[r["theorem"]] = r.get("module", "")
            per_module[r.get("module", "")] += 1
    touched = {module[t] for t in corpus if module.get(t)}
    band = json.loads(result_path("mathlib-forward-v1/band-report.json").read_text())
    return {
        "corpus": len(corpus),
        "positives": band["positives"],
        "files_touched": len(touched),
        "theorems_in_touched": sum(per_module[m] for m in touched),
        "library_theorems": len(module),
        "library_files": len(per_module),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--ratio", type=float, default=2.0, help="label gain R (default: 2, pessimistic)"
    )
    ap.add_argument("--target", type=int, help="print the corpus needed for this many positives")
    args = ap.parse_args()

    p = phase1()
    n1, p1 = p["corpus"], p["positives"]
    # A uniformly sampled file, not a size-biased one. Phase 1's 567 files
    # average 80 theorems because a file is touched in proportion to its size;
    # a file drawn at random averages the library mean.
    per_file = p["library_theorems"] / p["library_files"]
    keep = n1 / p["theorems_in_touched"]

    print("phase 1, measured")
    print(f"  corpus theorems                 : {n1:,}")
    print(f"  positives (corrected grep label): {p1}")
    print(f"  Mathlib files the corpus touches: {p['files_touched']:,}")
    print(f"  theorems living in those files  : {p['theorems_in_touched']:,}")
    print(f"  ... of which phase 1 kept       : {keep:.1%}")
    print()
    print("2024 library (from the committed dependency graph)")
    print(
        f"  theorems {p['library_theorems']:,} in {p['library_files']:,} files"
        f"  ({per_file:.1f} per file)"
    )
    print()

    def corpus_for(target: float, ratio: float) -> float:
        return n1 * (target / (p1 * ratio)) ** 0.5

    if args.target:
        for ratio in (1.0, args.ratio, 4.0):
            n = corpus_for(args.target, ratio)
            print(
                f"  R={ratio:<4g} {args.target:>6,} positives needs "
                f"{n:>8,.0f} theorems = {n / per_file:>5.0f} files "
                f"({n / per_file / p['library_files']:.1%} of Mathlib)"
            )
        return 0

    print(f"projection at R={args.ratio:g}  (positives ~ N^2)")
    print(f"  {'positives':>10}  {'theorems':>9}  {'files':>6}  {'of Mathlib':>10}")
    for target in (50, 100, 250, 500, 1000, 2000):
        n = corpus_for(target, args.ratio)
        files = n / per_file
        print(f"  {target:>10,}  {n:>9,.0f}  {files:>6.0f}  {files / p['library_files']:>9.1%}")
    print()
    print("The file count assumes every theorem in a sampled file is captured.")
    print(f"Phase 1 kept {keep:.1%} of the theorems in the files it touched, so if the")
    print("capture yield stays near that, the file count is the one that has to rise.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
