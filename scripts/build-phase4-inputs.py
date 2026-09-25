#!/usr/bin/env python3
"""build-phase4-inputs.py -- freeze what phase 4's encoders train on.

Two inputs, both 2024 data phase 3 already holds, neither touching the label:

    texts.json.gz          the union's 88,498 texts (states and statements), in
                           the order phase 3's embeddings use -- encoder B
    tactic-heads.jsonl.gz  per observed theorem, its tactic heads in source
                           order, by the rule in the phase 4 README -- encoder C

and a manifest with their digests, which the GPU worker checks before training.

    scripts/build-phase4-inputs.py --union outputs/phase-3-doubled-corpus/union \\
        --out outputs/phase-4-trained-encoder/inputs
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
from pathlib import Path

HEAD = re.compile(r"[A-Za-z_][A-Za-z0-9_'!?]*")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def heads_of(states: list[dict]) -> list[str]:
    """One head per source position, in source order, from single-line tactic nodes."""
    at: dict[tuple[int, int], str] = {}
    for s in states:
        text = s.get("tactic", "").strip()
        pos = s.get("pos")
        if pos is None or not text or "\n" in text or text == "·":
            continue
        if text.startswith("by") and (len(text) == 2 or not text[2].isalnum()):
            continue
        if text == "<failed to pretty print>":
            continue
        m = HEAD.search(text.lstrip("· "))
        if m and m.start() == 0:
            at.setdefault((pos["line"], pos["column"]), m.group())
    return [at[k] for k in sorted(at)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--union", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    texts = json.loads((args.union / "texts.json").read_text())
    with gzip.open(args.out / "texts.json.gz", "wt") as f:
        json.dump(texts, f, ensure_ascii=False)

    counts: collections.Counter[str] = collections.Counter()
    lengths, empty = [], 0
    with (
        gzip.open(args.union / "states-union.jsonl.gz", "rt") as f,
        gzip.open(args.out / "tactic-heads.jsonl.gz", "wt") as g,
    ):
        for line in f:
            r = json.loads(line)
            if r["object_kind"] != "observed":
                continue
            h = heads_of(r["states"])
            empty += not h
            lengths.append(len(h))
            counts.update(h)
            name = r["theorem_id"].split(":", 1)[1]
            g.write(json.dumps({"name": name, "heads": h}, ensure_ascii=False) + "\n")

    lengths.sort()
    manifest = {
        "texts": len(texts),
        "texts_sha256": sha256(args.out / "texts.json.gz"),
        "observed_theorems": len(lengths),
        "theorems_without_heads": empty,
        "heads_median": lengths[len(lengths) // 2],
        "heads_over_62": sum(n > 62 for n in lengths),
        "distinct_heads": len(counts),
        "distinct_heads_seen_5_or_more": sum(c >= 5 for c in counts.values()),
        "top_heads": counts.most_common(15),
        "tactic_heads_sha256": sha256(args.out / "tactic-heads.jsonl.gz"),
    }
    (args.out / "inputs-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
