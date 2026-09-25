"""Names and modules for phase 6's 2024 statement print: every theorem in the 2024 graph.

    python scripts/build-phase6-names.py

Writes results/phase-6-conjecture-placement/print-2024/{names,modules}.txt.
"""

import gzip
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EDGES = REPO / "results/phase-1-recognition/link-graph-v1/edges.jsonl.gz"
OUT = REPO / "results/phase-6-conjecture-placement/print-2024"


def main() -> None:
    names, modules = [], set()
    with gzip.open(EDGES, "rt") as f:
        for line in f:
            r = json.loads(line)
            names.append(r["theorem"])
            modules.add(r["module"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "names.txt").write_text("\n".join(names) + "\n")
    (OUT / "modules.txt").write_text("\n".join(sorted(modules)) + "\n")
    print(f"names {len(names):,} | unique {len(set(names)):,} | modules {len(modules):,}")


if __name__ == "__main__":
    main()
