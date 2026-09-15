"""Measure literal whitespace sensitivity without altering any state or object."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.spatial.distance import cdist

from noema.state_objects import atomic_json
from noema.state_records import load_record_archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=Path("results/state-objects-admitted-v1"))
    parser.add_argument("--forms", type=Path, default=Path("results/theorem-forms-v1"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    _, records, x = load_record_archive(args.records)
    forms = json.loads((args.forms / "forms.json").read_text())
    by_id = {f["theorem_id"]: f for f in forms}
    groups = defaultdict(list)
    for i, row in enumerate(records):
        # This literal-text diagnostic is not Lean canonicalization or an identity key.
        groups[row["theorem_id"], " ".join(row["text"].split())].append(i)
    variants = []
    for (tid, folded), indices in sorted(groups.items()):
        if len({records[i]["text"] for i in indices}) < 2:
            continue
        d2 = cdist(x[indices], x[indices], metric="sqeuclidean")
        a, b = np.unravel_index(np.argmax(d2), d2.shape)
        distance = float(np.sqrt(d2[a, b]))
        variants.append(
            {
                "theorem_id": tid,
                "record_rows": indices,
                "literal_whitespace_folded_text": folded,
                "raw_display_variants": len({records[i]["text"] for i in indices}),
                "maximum_distance": distance,
                "distance_over_object_diameter": distance / by_id[tid]["diameter"],
                "witness_records": [
                    records[indices[a]]["record_id"],
                    records[indices[b]]["record_id"],
                ],
            }
        )
    theorem_maxima = {
        tid: max(v["distance_over_object_diameter"] for v in variants if v["theorem_id"] == tid)
        for tid in sorted({v["theorem_id"] for v in variants})
    }
    maxima = list(theorem_maxima.values())
    report = {
        "method": (
            "compare original vectors for displays with identical "
            "whitespace-split token lists within a theorem"
        ),
        "diagnostic_only": True,
        "no_semantic_identity_inferred": True,
        "no_reencoding": True,
        "deduplication": False,
        "records_checked": len(records),
        "objects_checked": len(forms),
        "variant_groups": len(variants),
        "theorems_with_variants": len(theorem_maxima),
        "records_in_variant_groups": sum(len(v["record_rows"]) for v in variants),
        "per_theorem_maximum_fraction_of_diameter": theorem_maxima,
        "affected_theorem_fraction_distribution": dict(
            zip(
                ["min", "q25", "median", "q75", "max"],
                np.quantile(maxima, [0, 0.25, 0.5, 0.75, 1]),
                strict=True,
            )
        ),
        "groups": variants,
        "source_checksums_sha256": hashlib.sha256(
            (args.records / "SHA256SUMS").read_bytes()
        ).hexdigest(),
        "scope": (
            "Existing displayed strings only. Whitespace inside string literals is not "
            "claimed semantically irrelevant. No state merging or replacement representation."
        ),
    }
    atomic_json(args.output or args.forms / "formatting-sensitivity.json", report)
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in {"groups", "per_theorem_maximum_fraction_of_diameter"}
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
