"""How much of the forward result could plain word overlap account for?

The angle separates the 2026-connected pairs from the rest, but the encoder reads
text, so the obvious deflationary story is that it is counting shared identifiers.
This measures that directly: token Jaccard over each theorem's captured state
texts, positives against every eligible pair, using the same eligibility filter
and the same `no goals` exclusion as `analyze-mathlib-forward.py`.

The honest claim this supports is "still separates when vocabulary gives little",
not "vocabulary-independent" — the positives do share more words than a random
pair. The number that matters is how many hits sit in the low-overlap tail, since
those are the ones plain lexical matching could not have produced.

Reproduce: `.venv/bin/python scripts/analyze-forward-vocabulary.py`
"""

import argparse
import collections
import gzip
import importlib.util
import itertools
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_.']*")
EXCLUDED_STATE = "no goals"

spec = importlib.util.spec_from_file_location(
    "forward", ROOT / "scripts/analyze-mathlib-forward.py"
)
forward = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forward)


def vocabularies(states):
    """Identifier tokens per theorem, over the same states the centroids use."""
    out = {}
    for line in gzip.open(states, "rt"):
        record = json.loads(line)
        name = record["theorem_id"].split(":", 1)[1]
        tokens = set()
        for state in record["states"]:
            if state["text"].strip() == EXCLUDED_STATE:
                continue
            tokens.update(TOKEN.findall(state["text"]))
        out[name] = tokens
    return out


def jaccard_matrix(names, vocab):
    """Dense Jaccard over 1,797 theorems, via an indicator matrix."""
    index = {}
    for name in names:
        for token in vocab.get(name, ()):
            index.setdefault(token, len(index))
    M = np.zeros((len(names), len(index)), dtype=np.float32)
    for i, name in enumerate(names):
        for token in vocab.get(name, ()):
            M[i, index[token]] = 1
    inter = M @ M.T
    sizes = np.diag(inter).copy()
    union = sizes[:, None] + sizes[None, :] - inter
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(union > 0, inter / union, 0.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--states", type=Path, default=ROOT / "results/state-bridge-v1/states-augmented.jsonl.gz"
    )
    ap.add_argument(
        "--centroids", type=Path, default=ROOT / "results/mathlib-forward-v1/centroids.npz"
    )
    ap.add_argument("--edges", type=Path, default=ROOT / "results/link-graph-v1/edges.jsonl.gz")
    ap.add_argument(
        "--connectors", type=Path, default=ROOT / "results/mathlib-forward-v1/new-connectors.json"
    )
    ap.add_argument("--threshold", type=float, default=0.05)
    ap.add_argument("--out", type=Path, default=ROOT / "results/mathlib-forward-v1/vocabulary.json")
    args = ap.parse_args()

    cen, _ = forward.centroids_from_archive(args.centroids)
    names = sorted(cen)
    index = {n: i for i, n in enumerate(names)}
    rare = forward.rare_landmarks(set(names), args.edges)
    J = jaccard_matrix(names, vocabularies(args.states))

    i, j = np.triu_indices(len(names), 1)
    eligible = np.fromiter(
        (not (rare[names[a]] & rare[names[b]]) for a, b in zip(i, j, strict=True)), bool, len(i)
    )
    pi, pj = i[eligible], j[eligible]
    overlap = J[pi, pj]

    truth = {
        (min(index[a], index[b]), max(index[a], index[b]))
        for targets in json.loads(args.connectors.read_text()).values()
        for a, b in itertools.combinations(sorted(targets), 2)
        if a in index and b in index and not (rare[a] & rare[b])
    }
    label = np.fromiter(((a, b) in truth for a, b in zip(pi, pj, strict=True)), bool, len(pi))

    hits, rest = overlap[label], overlap[~label]
    low = int((hits < args.threshold).sum())
    report = {
        "positives": int(label.sum()),
        "eligible_pairs": int(label.size),
        "threshold": args.threshold,
        "mean_overlap_positives": float(hits.mean()),
        "median_overlap_positives": float(np.median(hits)),
        "mean_overlap_eligible": float(rest.mean()),
        "median_overlap_eligible": float(np.median(rest)),
        "positives_below_threshold": low,
        "auc_vocabulary_overlap": forward.auc(overlap, label),
    }
    width = max(len(k) for k in report)
    for key, value in report.items():
        print(
            f"{key:<{width}} : {value:.4f}"
            if isinstance(value, float)
            else f"{key:<{width}} : {value}"
        )
    print(
        f"\n{low} of {int(label.sum())} connected pairs share under "
        f"{args.threshold:.0%} of their state vocabulary."
    )

    counts = collections.Counter(np.digitize(hits, [0.05, 0.10, 0.20, 0.40]))
    labels = ["<5%", "5-10%", "10-20%", "20-40%", ">=40%"]
    print("\nconnected pairs by vocabulary overlap:")
    for k, name in enumerate(labels):
        print(f"  {name:>7}  {counts.get(k, 0)}")
    report["positive_histogram"] = {labels[k]: counts.get(k, 0) for k in range(len(labels))}

    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
