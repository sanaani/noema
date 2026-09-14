"""Recompute all frozen matched results from archived vectors in a fresh process."""

import argparse
import gzip
import json
from pathlib import Path

import numpy as np

from noema.matched_experiment import design, evaluate, gate
from noema.statistics import benjamini_hochberg


def read(path):
    raw = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    return json.loads(raw)


class CachedOnly:
    def encode(self, texts):
        raise ValueError(f"archive lacks {len(texts)} required state vectors")


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--corpus", required=True, type=Path)
parser.add_argument("--result", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
manifest = read(args.corpus / "manifest.json")
plan = read(args.result / "acquisition-plan.json.gz")
frozen = read(args.result / "analysis-freeze.json.gz")
expected = read(args.result / "report.json.gz")
if design(plan, manifest, args.corpus) != frozen:
    raise ValueError("archived corpus/sampling/source freeze audit failed")
comparisons = []
for name in ("syntax", "truth", "minilm"):
    with np.load(args.result / f"{name}-embeddings.npz", allow_pickle=False) as saved:
        cache = dict(zip(saved["texts"].tolist(), saved["vectors"], strict=True))
    for selection in frozen["selections"]:
        comparisons.append(
            {
                "encoder": name,
                **evaluate(CachedOnly(), cache, manifest, selection, frozen["regime"]),
            }
        )
primary = [r for r in comparisons if r["primary"]]
for row, q in zip(primary, benjamini_hochberg([r["p_value"] for r in primary]), strict=True):
    row["q_value"] = q
if comparisons != expected["comparisons"]:
    raise ValueError("cached-vector reconstruction differs from archived results")
if gate(comparisons) != expected["gate"]:
    raise ValueError("recomputed gate differs")
validation = {
    "status": "passed",
    "comparison_count": len(comparisons),
    "primary_family_size": len(primary),
    "exact_match_all_fields": True,
    "scope": "same-implementation fresh-process cached-vector reproduction; "
    "not statistical replication",
}
with args.output.open("x") as handle:
    json.dump(validation, handle, indent=2)
    handle.write("\n")
print(json.dumps(validation))
