#!/usr/bin/env python3
"""Does the state geometry predict anything the cheap baselines do not?

On the unseeded corpus the angle scores 0.709, shared state vocabulary scores
0.736 and "same Mathlib area" scores 0.712. Two predictors that need no encoder
at all match or beat the geometry, so the headline AUC cannot be read as
evidence that the embedding sees structure. The question is whether it adds
anything once those two are held out.

This strips both. It reports the angle's AUC on the pairs that share no
subfield and almost no state vocabulary, and -- because a subset AUC can drift
for reasons that have nothing to do with the predictor -- it reports vocabulary
overlap's AUC on that same subset as the control. If the angle beats the
vocabulary baseline where vocabulary has been removed, the geometry has content
of its own. If both sink to chance, the phase 1 result was selection.

    scripts/analyze-forward-residual.py --centroids ... --connectors ... \
        --states ... --selection ... --out residual.json
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import itertools
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "forward", ROOT / "scripts/analyze-mathlib-forward.py"
)
forward = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forward)

TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_.']*")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--centroids", type=Path, required=True)
    ap.add_argument("--connectors", type=Path, required=True)
    ap.add_argument("--states", type=Path, required=True)
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--edges", type=Path, required=True)
    ap.add_argument("--vocab-threshold", type=float, default=0.05)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    cen = np.load(args.centroids, allow_pickle=False)
    names = [str(n) for n in cen["names"]]
    C = cen["centroids"]
    index = {n: i for i, n in enumerate(names)}

    area = {
        t["name"]: (t["module"].split(".")[1] if t["module"].count(".") else "")
        for t in json.loads(gzip.open(args.selection, "rt").read())["theorems"]
    }
    vocab: dict[str, frozenset[str]] = {}
    for line in gzip.open(args.states, "rt"):
        r = json.loads(line)
        name = r["theorem_id"].split(":", 1)[1]
        if name in index:
            words: set[str] = set()
            for s in r["states"]:
                words.update(TOKEN.findall(s["text"]))
            vocab[name] = frozenset(words)

    rare = forward.rare_landmarks(set(names), args.edges)
    D = np.degrees(np.arccos(np.clip(C @ C.T, -1, 1)))
    i, j = np.triu_indices(len(names), 1)
    eligible = np.fromiter(
        (not (rare[names[a]] & rare[names[b]]) for a, b in zip(i, j, strict=True)), bool, len(i)
    )
    pi, pj, angle = i[eligible], j[eligible], D[i, j][eligible]
    del D, i, j, eligible

    truth = {
        (min(index[a], index[b]), max(index[a], index[b]))
        for targets in json.loads(args.connectors.read_text()).values()
        for a, b in itertools.combinations(sorted(targets), 2)
        if a in index and b in index and not (rare[a] & rare[b])
    }
    label = np.fromiter(((a, b) in truth for a, b in zip(pi, pj, strict=True)), bool, len(pi))

    def jaccard(a: int, b: int) -> float:
        x, y = vocab.get(names[a], frozenset()), vocab.get(names[b], frozenset())
        u = len(x | y)
        return len(x & y) / u if u else 0.0

    overlap = np.fromiter((jaccard(a, b) for a, b in zip(pi, pj, strict=True)), float, len(pi))
    same = np.fromiter(
        (area.get(names[a], "") == area.get(names[b], "") for a, b in zip(pi, pj, strict=True)),
        bool,
        len(pi),
    )

    rows = []
    print(f"{'subset':<44}{'pairs':>14}{'pos':>7}{'angle':>8}{'vocab':>8}")
    for tag, mask in (
        ("all eligible", np.ones(len(label), bool)),
        ("cross-area only", ~same),
        (f"vocabulary overlap < {args.vocab_threshold:.0%}", overlap < args.vocab_threshold),
        (
            f"cross-area AND overlap < {args.vocab_threshold:.0%}",
            (~same) & (overlap < args.vocab_threshold),
        ),
    ):
        n, p = int(mask.sum()), int(label[mask].sum())
        if p < 2 or n - p < 2:
            print(f"{tag:<44}{n:>14,}{p:>7}   too few to score")
            continue
        a_ang = forward.auc(-angle[mask], label[mask])
        a_voc = forward.auc(overlap[mask], label[mask])
        print(f"{tag:<44}{n:>14,}{p:>7}{a_ang:>8.3f}{a_voc:>8.3f}")
        rows.append(
            {"subset": tag, "pairs": n, "positives": p, "auc_angle": a_ang, "auc_vocab": a_voc}
        )

    last = rows[-1]
    print(
        f"\nWith neither shared subfield nor shared vocabulary, the angle scores "
        f"{last['auc_angle']:.3f} on {last['positives']:,} positives.\n"
        f"Vocabulary on that same subset scores {last['auc_vocab']:.3f}; it has been "
        f"stripped, so it should be near chance,\nand it is the control that says the "
        f"subset is doing what it claims."
    )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(
                {
                    "subsets": rows,
                    "vocab_threshold": args.vocab_threshold,
                    "tokenizer": "identifier-like runs, set per theorem, Jaccard over pairs",
                },
                indent=2,
            )
            + "\n"
        )
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
