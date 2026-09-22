#!/usr/bin/env python3
"""Which centroids are proof-state geometry at all, and does the answer change the AUC?

A theorem whose proof runs no tactic -- a term-mode one-liner, an instance
field, a `by simp` that closes at once -- produces no goal states. The capture
rescues it with one *synthetic* state: the declaration's own type printed as a
goal. Its centroid is then the encoder's reading of the statement, not of any
proof. On the unseeded corpus that is 6,792 of 11,489 theorems (59%); on phase
1's selected corpus it was 425 of 1,797 (24%), because phase 1 selected on
state count.

So the forward AUC is an average over three kinds of pair, and "proof-state
geometry" only names one of them:

    observed-observed    both centroids are means of real proof states
    observed-synthetic   one is, one is a statement embedding
    synthetic-synthetic  both are statement embeddings

This scores the angle and the vocabulary baseline on each kind, then repeats
the residual test (cross-area, vocabulary < 5%) and the top-k enrichment inside
the observed-observed pairs, so the claim about proof states is made on proof
states.

    scripts/analyze-forward-state-source.py --centroids ... --connectors ... \
        --states ... --selection ... --edges ... --out state-source.json
"""

from __future__ import annotations

import argparse
import collections
import gzip
import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


forward = load("analyze-mathlib-forward")
vocabmod = load("analyze-forward-vocabulary")

KINDS = ("observed-observed", "observed-synthetic", "synthetic-synthetic")


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

    # object_kind is written by the capture: "observed" when the replay saw
    # tactic states, "synthetic" when the only state is the InitialGoals rescue.
    kind: dict[str, str] = {}
    for line in gzip.open(args.states, "rt"):
        r = json.loads(line)
        name = r["theorem_id"].split(":", 1)[1]
        if name in index:
            kind[name] = r["object_kind"]
    missing = [n for n in names if n not in kind]
    if missing:
        raise SystemExit(f"{len(missing)} centroids have no state record, e.g. {missing[:3]}")
    counts = collections.Counter(kind.values())
    print(
        f"{len(names):,} theorems: {counts.get('observed', 0):,} observed "
        f"({counts.get('observed', 0) / len(names):.0%}), "
        f"{counts.get('synthetic', 0):,} synthetic (statement only)"
    )
    is_obs = np.fromiter((kind[n] == "observed" for n in names), bool, len(names))

    area = {
        t["name"]: (t["module"].split(".")[1] if t["module"].count(".") else "")
        for t in json.loads(gzip.open(args.selection, "rt").read())["theorems"]
    }
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
    n_obs = is_obs[pi].astype(int) + is_obs[pj].astype(int)
    pair_kind = {
        "observed-observed": n_obs == 2,
        "observed-synthetic": n_obs == 1,
        "synthetic-synthetic": n_obs == 0,
    }
    hard = (~same) & (overlap < args.vocab_threshold)

    rows = []

    def score(tag: str, mask: np.ndarray) -> None:
        n, p = int(mask.sum()), int(label[mask].sum())
        if p < 2 or n - p < 2:
            print(f"{tag:<48}{n:>14,}{p:>7}   too few to score")
            rows.append({"subset": tag, "pairs": n, "positives": p})
            return
        a_ang = forward.auc(-angle[mask], label[mask])
        a_voc = forward.auc(overlap[mask], label[mask])
        print(f"{tag:<48}{n:>14,}{p:>7}{a_ang:>8.3f}{a_voc:>8.3f}")
        rows.append(
            {"subset": tag, "pairs": n, "positives": p, "auc_angle": a_ang, "auc_vocab": a_voc}
        )

    print(f"\n{'subset':<48}{'pairs':>14}{'pos':>7}{'angle':>8}{'vocab':>8}")
    score("all eligible", np.ones(len(label), bool))
    for k in KINDS:
        score(k, pair_kind[k])
    print()
    for k in KINDS:
        score(f"{k}, cross-area AND overlap < {args.vocab_threshold:.0%}", pair_kind[k] & hard)

    # Enrichment at the top of the ranking, inside the observed-observed pairs
    # only: the shortlist question asked of proof-state centroids alone.
    print(f"\n{'subset (observed-observed)':<48}{'k':>8}{'hits':>7}{'base':>9}{'lift':>8}")
    tops = []
    for tag, mask in (
        ("all eligible", pair_kind["observed-observed"]),
        (
            f"cross-area AND overlap < {args.vocab_threshold:.0%}",
            pair_kind["observed-observed"] & hard,
        ),
    ):
        sub_angle, sub_label = angle[mask], label[mask]
        base = float(sub_label.mean()) if len(sub_label) else 0.0
        order = np.argsort(sub_angle)
        for k in (100, 1000, 10000):
            if k > len(order):
                continue
            hits = int(sub_label[order[:k]].sum())
            lift = (hits / k) / base if base else float("nan")
            print(f"{tag:<48}{k:>8,}{hits:>7}{base:>9.5f}{lift:>7.0f}x")
            tops.append(
                {"subset": tag, "k": k, "hits": hits, "base_rate": base, "lift": float(lift)}
            )

    by = {r["subset"]: r for r in rows}
    oo, ss = by["observed-observed"], by["synthetic-synthetic"]
    if "auc_angle" in oo and "auc_angle" in ss:
        d = oo["auc_angle"] - ss["auc_angle"]
        print(
            f"\nOn pairs of real proof-state centroids the angle scores {oo['auc_angle']:.3f} "
            f"({oo['positives']:,} positives);\non pairs of statement-only centroids "
            f"{ss['auc_angle']:.3f} ({ss['positives']:,})."
        )
        if min(oo["positives"], ss["positives"]) < 50:
            print(
                "Too few positives in one of the two to say whether the proof states add anything."
            )
        elif d > 0.02:
            print(f"The proof states add {d:+.3f} over what the statement alone gives.")
        elif d < -0.02:
            print(f"The statement alone does better, by {-d:.3f}.")
        else:
            print("The proof states add nothing measurable over the statement alone.")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(
                {
                    "theorems": {k: int(v) for k, v in counts.items()},
                    "subsets": rows,
                    "top_k_observed_observed": tops,
                    "vocab_threshold": args.vocab_threshold,
                },
                indent=2,
            )
            + "\n"
        )
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
