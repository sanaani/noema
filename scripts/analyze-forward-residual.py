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
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "forward", ROOT / "scripts/analyze-mathlib-forward.py"
)
forward = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forward)
vspec = importlib.util.spec_from_file_location(
    "vocabulary", ROOT / "scripts/analyze-forward-vocabulary.py"
)
vocabmod = importlib.util.module_from_spec(vspec)
vspec.loader.exec_module(vocabmod)


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
    # Same tokenizer, same state filter as analyze-forward-vocabulary.py, imported
    # rather than copied. The first version of this re-implemented the tokenizer
    # and left out that script's `no goals` exclusion, so on the same corpus its
    # "all eligible" vocabulary AUC read 0.729 against vocabulary.json's 0.736,
    # and its <5% subset held 588 positives where vocabulary.json counted 640.
    vocab = {n: frozenset(t) for n, t in vocabmod.vocabularies(args.states).items() if n in index}

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

    # AUC over sixty million pairs is dominated by the bulk, and the bulk is not
    # what a discovery tool returns. What matters is whether the top of the
    # ranking is enriched: take the closest k pairs that share no vocabulary and
    # no subfield, and ask how many are real connections against base rate.
    print(f"\n{'subset':<44}{'k':>8}{'hits':>7}{'base':>9}{'lift':>8}")
    tops = []
    for tag, mask in (
        ("all eligible", np.ones(len(label), bool)),
        (
            f"cross-area AND overlap < {args.vocab_threshold:.0%}",
            (~same) & (overlap < args.vocab_threshold),
        ),
    ):
        sub_angle, sub_label = angle[mask], label[mask]
        base = float(sub_label.mean())
        order = np.argsort(sub_angle)
        for k in (100, 1000, 10000):
            if k > len(order):
                continue
            hits = int(sub_label[order[:k]].sum())
            lift = (hits / k) / base if base else float("nan")
            print(f"{tag:<44}{k:>8,}{hits:>7}{base:>9.5f}{lift:>7.0f}x")
            tops.append(
                {"subset": tag, "k": k, "hits": hits, "base_rate": base, "lift": float(lift)}
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
                    "top_k": tops,
                    "vocab_threshold": args.vocab_threshold,
                    "tokenizer": "analyze-forward-vocabulary.py: identifier-like runs per state, "
                    "`no goals` excluded, set per theorem, Jaccard over pairs",
                },
                indent=2,
            )
            + "\n"
        )
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
