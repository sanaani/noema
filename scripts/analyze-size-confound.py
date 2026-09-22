"""Proof size against both targets, which is the whole reason to trust one over the other.

The replication's headline 0.877 is mostly not the encoder. `min(state count)`
alone — no embedding at all — predicts "these two proofs share a rare lemma" at
AUC 0.740, because long proofs cite more lemmas and their centroids drift toward
the corpus mean direction. That is why the replication is read as its +0.164
margin over the shuffled control rather than as 0.877.

The forward label is chosen to not reward length, and the same predictor scores
0.498 on it — a coin flip. Both numbers are quoted across the READMEs; neither
was computed by anything committed until this script. They are the comparison
that says the forward test is the cleaner of the two, so they should be
rederivable rather than remembered.

Ranks are tie-averaged. `min(state count)` takes ~225 distinct values over 1.6M
pairs, so nearly every comparison is a tie and breaking them by sort position
makes the answer a property of the CPU — see forward.midranks.

Reproduce: `.venv/bin/python scripts/analyze-size-confound.py`
"""

import argparse
import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np

from noema.paths import result_path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "forward", ROOT / "scripts/analyze-mathlib-forward.py"
)
forward = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forward)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--centroids", type=Path, default=result_path("mathlib-forward-v1/centroids.npz")
    )
    ap.add_argument("--edges", type=Path, default=result_path("link-graph-v1/edges.jsonl.gz"))
    ap.add_argument(
        "--connectors", type=Path, default=result_path("mathlib-forward-v1/new-connectors.json")
    )
    ap.add_argument(
        "--report",
        type=Path,
        help="the state-bridge report.json of a replication run on this same corpus; when "
        "given, its encoder AUC and shuffled control are quoted beside the size AUC. Not "
        "given, nothing about a replication is claimed -- the first version of this quoted "
        "phase 1's 0.877 and 0.714 on every corpus, including one with no replication run.",
    )
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    cen, size = forward.centroids_from_archive(args.centroids)
    names = sorted(cen)
    index = {n: i for i, n in enumerate(names)}
    rare = forward.rare_landmarks(set(names), args.edges)
    i, j = np.triu_indices(len(names), 1)
    minsize = np.fromiter(
        (min(size[names[a]], size[names[b]]) for a, b in zip(i, j, strict=True)), float, len(i)
    )

    # Target 1: the replication label, over every pair.
    shares = np.fromiter(
        (bool(rare[names[a]] & rare[names[b]]) for a, b in zip(i, j, strict=True)), bool, len(i)
    )
    auc_replication = forward.auc(minsize, shares)

    # Target 2: the 2026 label, over the pairs the forward test is allowed.
    eligible = ~shares
    truth = {
        (min(index[a], index[b]), max(index[a], index[b]))
        for targets in json.loads(args.connectors.read_text()).values()
        for a, b in itertools.combinations(sorted(targets), 2)
        if a in index and b in index and not (rare[a] & rare[b])
    }
    pi, pj = i[eligible], j[eligible]
    connected = np.fromiter(((a, b) in truth for a, b in zip(pi, pj, strict=True)), bool, len(pi))
    auc_forward = forward.auc(minsize[eligible], connected)

    print(f"{'target':<44}{'pairs':>12}{'positives':>11}{'size AUC':>10}")
    print(
        f"{'shares a rare lemma (replication)':<44}{len(shares):>12,}"
        f"{int(shares.sum()):>11,}{auc_replication:>10.3f}"
    )
    print(
        f"{'cited together by 2026 (forward)':<44}{len(connected):>12,}"
        f"{int(connected.sum()):>11,}{auc_forward:>10.3f}"
    )
    gap = auc_forward - 0.5
    print(
        f"\nProof size alone predicts the replication label at {auc_replication:.3f} and the"
        f"\nforward label at {auc_forward:.3f}."
    )
    if abs(gap) <= 0.05:
        print("On the forward label that is a coin flip: the size confound does not transfer.")
    else:
        print(
            f"On the forward label that is {abs(gap):.3f} {'above' if gap > 0 else 'below'} "
            "chance, so proof size\nis a confound there too and the angle must be read "
            "against it."
        )
    published = None
    if args.report:
        rep = json.loads(args.report.read_text())
        enc = rep["replication_all"]["auc"]
        ctl = rep["control_replication_all"]["auc"]
        published = {"replication_encoder_auc": enc, "replication_shuffled_control_auc": ctl}
        print(
            f"\nThe replication's own encoder AUC is {enc:.3f}, of which the shuffled control"
            f"\nalready takes {ctl:.3f}; only the +{enc - ctl:.3f} margin is the embedding's,"
            f"\nand proof size alone reaches {auc_replication:.3f} of it."
        )

    if args.out:
        args.out.write_text(
            json.dumps(
                {
                    "auc_size_on_replication_label": auc_replication,
                    "auc_size_on_forward_label": auc_forward,
                    "replication_pairs": int(len(shares)),
                    "replication_positives": int(shares.sum()),
                    "forward_pairs": int(len(connected)),
                    "forward_positives": int(connected.sum()),
                    "distinct_size_values": int(len(np.unique(minsize))),
                    "published_replication": published,
                },
                indent=2,
            )
            + "\n"
        )
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
