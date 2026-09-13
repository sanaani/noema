#!/usr/bin/env python3
"""Recompute saved primary results from frozen splits and archived vector caches."""

import argparse
import gzip
import json
from pathlib import Path

import numpy as np

from noema.corpus import digest
from noema.formal_experiment import design, evaluate, feasibility_gate, theorem_permutation_test
from noema.statistics import benjamini_hochberg


def read(path):
    raw = path.read_bytes()
    return (gzip.decompress(raw) if path.suffix == ".gz" else raw).decode()


class CachedOnlyEncoder:
    def encode(self, states):
        raise ValueError(f"saved encoder cache is missing {len(states)} required states")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--embeddings", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(read(args.corpus))
    frozen_text = read(args.freeze)
    frozen = json.loads(frozen_text)
    result = json.loads(read(args.report))
    if design(manifest) != frozen or digest(frozen_text) != result["split_freeze_sha256"]:
        raise ValueError("corpus/split freeze mismatch")
    caches = {}
    for row in result["comparisons"]:
        name = row["encoder"]
        if name not in caches:
            with np.load(args.embeddings / f"{name}-embeddings.npz", allow_pickle=False) as saved:
                caches[name] = dict(zip(saved["texts"].tolist(), saved["vectors"], strict=True))
        selection = next(
            s
            for s in frozen["selections"]
            if all(s[k] == row[k] for k in ("policy", "direction", "seed"))
        )
        actual = evaluate(
            CachedOnlyEncoder(), caches[name], manifest, {**selection, "view": row["view"]}
        )
        for key, value in actual.items():
            if value != row[key]:
                raise ValueError(
                    f"reproduction mismatch for {name}/{row['view']}/{row['direction']}: {key}"
                )
        if theorem_permutation_test(np.array(actual["mmd_squared"])) != row["p_value"]:
            raise ValueError("whole-theorem permutation p-value mismatch")
        print(f"Reproduced {name}/{row['view']}/{row['direction']}", flush=True)
    expected_q = benjamini_hochberg([r["p_value"] for r in result["comparisons"]])
    if expected_q != [r["q_value"] for r in result["comparisons"]]:
        raise ValueError("multiple-comparison correction mismatch")
    if feasibility_gate(result["comparisons"]) != result["gate"]:
        raise ValueError("feasibility gate mismatch")
    print(
        f"All {len(result['comparisons'])} primary comparisons, uncertainty intervals, "
        "baselines, permutation p-values, BH correction, and gate reproduced exactly."
    )


if __name__ == "__main__":
    main()
