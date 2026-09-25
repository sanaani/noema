#!/usr/bin/env python3
"""draw-corpus-sample.py -- draw the unseeded phase 2 corpus, once, from a fixed seed.

This is a pre-registration step. The draw is stratified by Mathlib area and
depends on nothing but the seed and the committed 2024 edge list, so it can be
reproduced exactly, and the result is committed before any capture runs. The
corpus is then used whatever it yields.

Because a pair's label depends only on which theorem *names* are in the corpus,
the positive count of this specific draw is known before a single proof is
replayed. That number is written here so it cannot be chosen after the fact.

    scripts/draw-corpus-sample.py --edges-2026 <edges-2026.jsonl.gz> --files 350

To grow an existing corpus rather than replace it, pass the modules it already
drew as --exclude-modules and the names it kept as --base-names: the new files
are drawn from the rest of Mathlib, and the prediction is for the union.
"""

from __future__ import annotations

import argparse
import collections
import gzip
import itertools
import json
import random
import re
from pathlib import Path

from noema.paths import result_path

DF_LO, DF_HI = 2, 200
GENERATED = re.compile(r"\.proof_\d+$")


def read_lines(path: Path) -> list[str]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as f:
        return [line.strip() for line in f if line.strip()]


def area_of(module: str) -> str:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 else module


def stratified(rng: random.Random, by_area: dict[str, list[str]], total: int, k: int) -> list[str]:
    """Largest-remainder allocation across areas, so small areas are not rounded away."""
    areas = sorted(by_area)
    quota = {a: len(by_area[a]) * k / total for a in areas}
    base = {a: int(quota[a]) for a in areas}
    left = k - sum(base.values())
    for a in sorted(areas, key=lambda a: quota[a] - base[a], reverse=True)[:left]:
        base[a] += 1
    picked: list[str] = []
    for a in areas:
        n = min(base[a], len(by_area[a]))
        if n:
            picked.extend(rng.sample(by_area[a], n))
    return sorted(picked)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--edges-2024", default=result_path("link-graph-v1/edges.jsonl.gz"))
    ap.add_argument("--edges-2026", required=True)
    ap.add_argument("--files", type=int, default=350)
    ap.add_argument("--seed", type=int, default=20260922)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--exclude-modules", type=Path, help="modules an earlier draw already took")
    ap.add_argument("--base-names", type=Path, help="names already in the corpus, predicted with")
    ap.add_argument(
        "--drop-generated", action="store_true", help="drop compiler-generated .proof_N names"
    )
    args = ap.parse_args()
    excluded = set(read_lines(args.exclude_modules)) if args.exclude_modules else set()
    base = set(read_lines(args.base_names)) if args.base_names else set()
    if args.drop_generated:
        base = {n for n in base if not GENERATED.search(n)}

    df: collections.Counter[str] = collections.Counter()
    by_file: dict[str, list[str]] = collections.defaultdict(list)
    mod_of: dict[str, str] = {}
    deps_of: dict[str, frozenset[str]] = {}
    with gzip.open(args.edges_2024, "rt") as f:
        for line in f:
            r = json.loads(line)
            deps = frozenset(r.get("deps") or ())
            df.update(deps)
            name = r["theorem"]
            by_file[r.get("module", "")].append(name)
            mod_of[name] = r.get("module", "")
            deps_of[name] = deps
    rare = {c for c, k in df.items() if DF_LO <= k <= DF_HI}
    rare_of = {n: frozenset(d & rare) for n, d in deps_of.items()}
    del df, deps_of
    if args.drop_generated:
        for m in by_file:
            by_file[m] = [n for n in by_file[m] if not GENERATED.search(n)]
    files = sorted(m for m in by_file if m not in excluded)

    by_area: dict[str, list[str]] = collections.defaultdict(list)
    for m in files:
        by_area[area_of(m)].append(m)

    picked = stratified(random.Random(args.seed), by_area, len(files), args.files)
    drawn = {n for m in picked for n in by_file[m]}
    corpus = drawn | base

    names_2024 = set(rare_of)
    pairs: set[tuple[str, str]] = set()
    connectors = 0
    with gzip.open(args.edges_2026, "rt") as f:
        for line in f:
            r = json.loads(line)
            if r["theorem"] in names_2024:
                continue
            inside = sorted({d for d in (r.get("deps") or ()) if d in corpus})
            if len(inside) < 2:
                continue
            connectors += 1
            pairs.update(itertools.combinations(inside, 2))
    none: frozenset[str] = frozenset()
    elig = [(a, b) for a, b in pairs if not (rare_of.get(a, none) & rare_of.get(b, none))]
    xa = sum(1 for a, b in elig if area_of(mod_of.get(a, "")) != area_of(mod_of.get(b, "")))

    sample = {
        "seed": args.seed,
        "strategy": "stratified by Mathlib area, largest-remainder allocation",
        "requested_files": args.files,
        "edges_2024": str(args.edges_2024),
        "edges_2026": str(args.edges_2026),
        "excluded_modules": len(excluded),
        "base_names": len(base),
        "drop_generated": args.drop_generated,
        "files": picked,
        "area_counts": dict(sorted(collections.Counter(area_of(m) for m in picked).items())),
        "drawn_theorems": len(drawn),
        "theorems": len(corpus),
        "predicted": {
            "connectors": connectors,
            "pairs": len(pairs),
            "positives": len(elig),
            "cross_area_positives": xa,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(sample, indent=2) + "\n")

    (args.out.parent / "modules.txt").write_text("".join(m + "\n" for m in picked))
    (args.out.parent / "names.txt").write_text(
        "".join(n + "\n" for m in picked for n in sorted(by_file[m]))
    )
    print(f"{len(picked)} files, {len(by_area)} areas, {len(drawn):,} theorems drawn")
    if base:
        print(f"with {len(base):,} base names: {len(corpus):,} theorems in the union")
    print(f"predicted: {connectors:,} connectors, {len(pairs):,} pairs, {len(elig):,} positives")
    print(f"           {xa:,} of them cross-area")
    print(f"wrote {args.out}, modules.txt, names.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
