#!/usr/bin/env python3
"""build-dependency-label.py — the 2026 label from Lean's own dependency graph.

Phase 1 asked "did anyone later write a theorem citing both halves of this
pair?" by searching the 2026 Mathlib source for theorem names. Phase 2 asks
Lean. Both edge lists come from the same elaborator over the same definition of
"depends on", so the two graphs are directly comparable:

    phase-1-recognition/link-graph-v1/edges.jsonl.gz    Mathlib f0957a7 (2024)
    phase-2-dependency-labels/link-graph-2026-v1/...     Mathlib 09712d48 (2026)

A *connector* is a theorem present in 2026 and absent in 2024 whose proof term
cites at least two distinct corpus theorems. A pair of corpus theorems is a
positive when some connector cites both.

Three things this fixes, all of which the grep label got wrong or could not see:

* **No name matching.** Dependencies are resolved constants, so `Foo.bar` can
  never be credited for `Foo.bar_baz`, and a name written under an `open`
  namespace is recorded under its full name like any other.
* **Full names on both sides.** "New since 2024" is decided against the 2024
  edge list's theorem names, not against a list of last components, so a
  theorem is no longer called new merely because something was renamed.
* **Proof terms, not text.** A mention in a docstring is not a dependency, and
  a declaration does not cite itself.

It also sees strictly more: every citation Lean resolved, including the ones a
text search structurally cannot find.

`--include-edited` additionally counts a theorem that existed in 2024 but whose
2026 dependency set gained two corpus theorems. That is a real "someone later
connected these" event, but it is not what the phase 1 label measured, so it is
off by default and reported separately.

    scripts/build-dependency-label.py \
        --edges-2026 .../link-graph-2026-v1/edges-2026.jsonl.gz \
        --out .../new-connectors.json
"""

from __future__ import annotations

import argparse
import collections
import gzip
import itertools
import json
from pathlib import Path

import numpy as np

from noema.paths import result_path


def read_edges(path: Path) -> dict[str, set[str]]:
    """theorem -> set of constants its proof term uses. Oversize rows carry no
    dependency list and are recorded as present-but-unknown."""
    deps: dict[str, set[str]] = {}
    with gzip.open(path, "rt") as f:
        for line in f:
            r = json.loads(line)
            deps[r["theorem"]] = set(r.get("deps") or ())
    return deps


def module_of(path: Path) -> dict[str, str]:
    mods: dict[str, str] = {}
    with gzip.open(path, "rt") as f:
        for line in f:
            r = json.loads(line)
            mods[r["theorem"]] = r.get("module", "")
    return mods


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--edges-2024", type=Path, default=result_path("link-graph-v1/edges.jsonl.gz"))
    ap.add_argument("--edges-2026", type=Path, required=True)
    ap.add_argument(
        "--centroids", type=Path, default=result_path("mathlib-forward-v1/centroids.npz")
    )
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--include-edited", action="store_true")
    args = ap.parse_args()

    corpus = {str(n) for n in np.load(args.centroids, allow_pickle=False)["names"]}
    old = read_edges(args.edges_2024)
    new = read_edges(args.edges_2026)
    mods = module_of(args.edges_2026)

    missing = corpus - set(old)
    if missing:
        print(f"warning: {len(missing)} corpus theorems absent from the 2024 graph")

    connectors: dict[str, list[str]] = {}
    edited: dict[str, list[str]] = {}
    for name, deps in new.items():
        cited = sorted((deps & corpus) - {name})
        if len(cited) < 2:
            continue
        if name not in old:
            connectors[f"{mods.get(name, '')}::{name}"] = cited
        elif args.include_edited:
            gained = sorted(set(cited) - (old[name] & corpus))
            if len(gained) >= 2:
                edited[f"{mods.get(name, '')}::{name}"] = cited

    chosen = {**connectors, **edited} if args.include_edited else connectors
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(chosen, indent=2, ensure_ascii=False) + "\n")

    pairs: set[tuple[str, str]] = set()
    degree: collections.Counter[str] = collections.Counter()
    for targets in chosen.values():
        for a, b in itertools.combinations(sorted(targets), 2):
            pairs.add((a, b))
        degree.update(targets)

    print(f"2024 theorems {len(old):,} | 2026 theorems {len(new):,}")
    print(f"new since 2024                      : {len(set(new) - set(old)):,}")
    print(f"connectors (new, cite >=2 corpus)   : {len(connectors):,}")
    if args.include_edited:
        print(f"edited theorems that gained a pair  : {len(edited):,}")
    print(f"distinct corpus pairs connected      : {len(pairs):,}")
    print(f"corpus theorems appearing as endpoint: {len(degree):,}")
    for name, count in degree.most_common(5):
        print(f"    {count:>4}  {name}")
    print(f"\nwrote {args.out}")
    print("eligibility (no shared rare lemma in 2024) is applied by the analysis scripts,")
    print("so the positive count they report will be lower than the pair count above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
