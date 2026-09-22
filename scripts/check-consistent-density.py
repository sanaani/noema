"""Substitute certified equivalent inputs throughout every original proof trace."""

import json
from pathlib import Path

import numpy as np

from noema.comparison_encoders import save_json
from noema.encoder_invariance import radial_change
from noema.paths import result_path
from noema.state_consistency import RegisteredStateEncoder, digest

ROOT = Path(__file__).resolve().parents[1]
OUT = result_path("state-consistency-v1")


def main():
    records = json.loads((OUT / "records.json").read_text())
    encoder = RegisteredStateEncoder(OUT, "qwen")
    registry = encoder.registry
    replacements = {}
    for row in records:
        index = registry["key_to_class"][digest(row["payload"])]
        replacements.setdefault(index, []).append(row["payload"])
    fixture = [
        r
        for r in records
        if r["id"].split("/")[0]
        in {
            "and_swap",
            "and_assoc",
            "imp_comp",
            "or_swap",
            "eq_symm",
            "eq_trans",
            "nat_assoc",
            "list_assoc",
        }
        and r["shape"] != [0]
    ]
    results = []
    for name in sorted({r["id"].split("/")[0] for r in fixture}):
        rows = [r for r in fixture if r["id"].startswith(name + "/")]
        payloads = [r["payload"] for r in rows]
        other = []
        for payload in payloads:
            index = registry["key_to_class"][digest(payload)]
            candidates = replacements[index]
            other.append(next((p for p in candidates if p != payload), candidates[-1]))
        a = encoder.encode(payloads, environment_id=registry["environment_id"])
        b = encoder.encode(other, environment_id=registry["environment_id"])
        center_index = next(i for i, r in enumerate(rows) if r["id"] == f"{name}/0/0")
        result = radial_change(
            np.linalg.norm(a - a[center_index], axis=1), np.linalg.norm(b - b[center_index], axis=1)
        )
        assert np.array_equal(a, b) and result["wasserstein_1"] == 0
        results.append(
            {
                "theorem": name,
                "occurrences": len(rows),
                "different_normalized_payload_substitutions": sum(
                    x != y for x, y in zip(payloads, other, strict=True)
                ),
                "max_vector_drift": float(np.linalg.norm(a - b, axis=1).max()),
                **result,
            }
        )
    # Also exercise every genuinely different equivalent structural key. The
    # original traces above happen to share identical normalized payloads.
    all_rows = [r for r in records if r["shape"] != [0]]
    originals = [r["payload"] for r in all_rows]
    substitutes = []
    for payload in originals:
        index = registry["key_to_class"][digest(payload)]
        substitutes.append(next((p for p in replacements[index] if p != payload), payload))
    a = encoder.encode(originals, environment_id=registry["environment_id"])
    b = encoder.encode(substitutes, environment_id=registry["environment_id"])
    distances_a = np.linalg.norm(a[:, None] - a[None, :], axis=2)
    distances_b = np.linalg.norm(b[:, None] - b[None, :], axis=2)
    assert np.array_equal(a, b) and np.array_equal(distances_a, distances_b)
    panel = {
        "occurrences": len(a),
        "centers_checked": len(a),
        "different_normalized_payload_substitutions": sum(
            x != y for x, y in zip(originals, substitutes, strict=True)
        ),
        "max_pairwise_distance_drift": float(np.abs(distances_a - distances_b).max()),
    }
    assert panel["different_normalized_payload_substitutions"] > 0
    save_json(
        OUT / "density-checks.json",
        {
            "registry_id": registry["registry_id"],
            "rows": results,
            "full_registry_panel": panel,
            "interpretation": "lookup contract check; equivalence independently certified by Lean",
        },
    )
    print(
        f"All {len(results)} F_T curves exactly preserved, "
        f"{sum(r['occurrences'] for r in results)} occurrences."
    )


if __name__ == "__main__":
    main()
