#!/usr/bin/env python3
"""build-phase5-draw.py -- what phase 5 prints, and how each connector is classed.

From committed data only, before any 2026 statement exists:

    labels.jsonl    per connector: class (bridge / within / excluded), hard
                    flag, corpus theorems cited, 2026 module
    sample.txt      10,000 new 2026 theorems citing no corpus theorem, seed 20260927
    names.txt       every name to print: connectors, the sample, and the corpus
                    theorems that keep their name in 2026
    modules.txt     their 2026 modules, for Statements2026.lean
    draw.json       the counts

    scripts/build-phase5-draw.py --union outputs/phase-3-doubled-corpus/union \\
        --out results/phase-5-conjecture-map/draw
"""

from __future__ import annotations

import argparse
import collections
import gzip
import importlib.util
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import forward_blocks as fb  # noqa: E402

SEED = 20260927
SAMPLE = 10_000
GENERATED = re.compile(r"\.proof_\d+$")
E24 = ROOT / "results/phase-1-recognition/link-graph-v1/edges.jsonl.gz"
E26 = ROOT / "results/phase-2-dependency-labels/link-graph-2026-v1/edges-2026.jsonl.gz"

_spec = importlib.util.spec_from_file_location("a4", ROOT / "scripts/analyze-phase4.py")
a4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a4)


def theorem_modules(path: Path) -> dict[str, str]:
    with gzip.open(path, "rt") as f:
        return {r["theorem"]: r.get("module", "") for r in map(json.loads, f)}


def citing_any(path: Path, targets: set[str]) -> set[str]:
    """Theorems whose recorded dependencies include any of `targets`."""
    with gzip.open(path, "rt") as f:
        return {
            r["theorem"] for r in map(json.loads, f) if targets.intersection(r.get("deps") or ())
        }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--union", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    class U:
        union = args.union

    corpus, feat = a4.side(U, args.union / "centroids.npz")
    masks = fb.subset_masks(feat)
    names = corpus.names
    pair = {}
    for k in range(len(corpus.pos_i)):
        a, b = names[corpus.pos_i[k]], names[corpus.pos_j[k]]
        pair[(a, b) if a < b else (b, a)] = (
            bool(masks["cross-area only"][k]),
            bool(masks["cross-area AND vocab<5%"][k]),
        )

    mod26 = theorem_modules(E26)
    old = set(theorem_modules(E24))
    conn = json.loads((args.union / "new-connectors.json").read_text())
    counts: collections.Counter[str] = collections.Counter()
    connector_names = set()
    with open(args.out / "labels.jsonl", "w") as f:
        for key, cited in sorted(conn.items()):
            name = key.split("::", 1)[1]
            connector_names.add(name)
            joined = []
            for i in range(len(cited)):
                for j in range(i + 1, len(cited)):
                    a, b = sorted((cited[i], cited[j]))
                    if (a, b) in pair:
                        joined.append((a, b, *pair[(a, b)]))
            if not joined:
                cls = "excluded"
            elif any(x[2] for x in joined):
                cls = "bridge"
            else:
                cls = "within"
            hard = any(x[3] for x in joined)
            counts[cls] += 1
            counts["hard bridge"] += hard
            row = {
                "name": name,
                "class": cls,
                "hard": hard,
                "cited": len(cited),
                "module": mod26[name],
                "pairs": [[a, b] for a, b, *_ in joined],
            }
            f.write(json.dumps(row) + "\n")

    cites_corpus = citing_any(E26, set(names))
    new = sorted(
        n for n in mod26 if n not in old and n not in cites_corpus and not GENERATED.search(n)
    )
    sample = sorted(random.Random(SEED).sample(new, SAMPLE))
    (args.out / "sample.txt").write_text("".join(n + "\n" for n in sample))
    survivors = sorted(n for n in names if n in mod26)

    to_print = sorted(connector_names | set(sample) | set(survivors))
    (args.out / "names.txt").write_text("".join(n + "\n" for n in to_print))
    modules = sorted({mod26[n] for n in to_print})
    (args.out / "modules.txt").write_text("".join(m + "\n" for m in modules))

    draw = {
        "seed": SEED,
        "connectors": len(conn),
        "classes": {k: counts[k] for k in ("bridge", "within", "excluded", "hard bridge")},
        "new_2026_theorems_citing_no_corpus_theorem": len(new),
        "sample": len(sample),
        "corpus_theorems": len(names),
        "corpus_survivors_2026": len(survivors),
        "names_to_print": len(to_print),
        "modules": len(modules),
    }
    (args.out / "draw.json").write_text(json.dumps(draw, indent=2) + "\n")
    print(json.dumps(draw, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
