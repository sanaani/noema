"""Construct and describe every admitted theorem hull using every physical row."""

import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from noema.state_objects import atomic_json
from noema.state_records import load_record_archive
from noema.theorem_admission import load_admission
from noema.theorem_forms import certify_shared_segment, measure_form


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(values):
    a = np.asarray(values, dtype=float)
    return dict(
        zip(
            ("min", "q25", "median", "q75", "max"),
            np.quantile(a, [0, 0.25, 0.5, 0.75, 1]),
            strict=True,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=Path("results/state-objects-admitted-v1"))
    parser.add_argument("--output", type=Path, default=Path("results/theorem-forms-v1"))
    args = parser.parse_args()
    root, out = args.records, args.output
    out.mkdir(parents=True, exist_ok=True)
    # Validate every frozen active artifact, not merely the arrays' dimensions.
    for line in (root / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if sha(root / name.lstrip("*")) != digest:
            raise ValueError(f"active archive checksum mismatch: {name}")
    manifest, records, vectors = load_record_archive(root)
    corpus = json.load(gzip.open(Path(manifest["source_archive"]) / "corpus.json.gz"))
    admitted = load_admission(corpus, root)
    objects = json.loads((root / "objects.json").read_text())
    if {o["theorem_id"] for o in objects} != admitted:
        raise ValueError("shape analysis contains objects outside current admission")
    by_proof = {p["id"]: p for p in corpus["proofs"]}
    lookup = {r["record_id"]: i for i, r in enumerate(records)}
    if len(lookup) != len(records):
        raise ValueError("duplicated record identity")
    common_axes = np.load(root / "projection-axes.npy", allow_pickle=False)
    all_local_xy = np.zeros((len(records), 2))
    origins, axes_list, forms, construction, arrays = [], [], [], [], {}
    all_rows = []
    for obj in objects:
        tid = obj["theorem_id"]
        indices = [lookup[rid] for rid in obj["vector_record_ids"]]
        rows = [records[i] for i in indices]
        if any(
            r["theorem_id"] != tid or r["vector_row"] != i
            for r, i in zip(rows, indices, strict=True)
        ):
            raise ValueError("object-to-row association mismatch")
        all_rows.extend(indices)
        x = vectors[indices]
        arrays[tid] = x
        empty = [r["text"] == "no goals" for r in rows]
        form, local_xy, axes, origin, distances2 = measure_form(x, empty)
        all_local_xy[indices] = local_xy
        origins.append(origin)
        axes_list.append(axes)
        proofs = sorted({r["proof_id"] for r in rows})
        if len(proofs) != obj["known_proofs"]:
            raise ValueError("source proof coverage does not match object")
        coordinate_proofs = defaultdict(set)
        for r, v in zip(rows, x, strict=True):
            coordinate_proofs[v.tobytes()].add(r["proof_id"])
        proof_forms = []
        for pid in proofs:
            positions = [i for i, r in enumerate(rows) if r["proof_id"] == pid]
            proof_forms.append(
                {
                    "proof_id": pid,
                    "rows": len(positions),
                    "diameter": float(np.sqrt(distances2[np.ix_(positions, positions)].max())),
                    "has_coordinate_absent_from_other_source_proofs": any(
                        coordinate_proofs[x[i].tobytes()] == {pid} for i in positions
                    ),
                }
            )
        centered = x - origin
        total_spread = float(np.sum(centered**2))
        traces = {r["trace_id"] for r in rows}
        trace_types = Counter(
            t.get("granularity", t["source"])
            for pid in proofs
            for t in by_proof[pid]["state_traces"]
            if t["id"] in traces
        )
        form.update(
            {
                "theorem_id": tid,
                "name": obj["name"],
                "family": obj["family"],
                "source_proof_records": len(proofs),
                "distinct_source_scripts_diagnostic": len(
                    {by_proof[pid]["body"] for pid in proofs}
                ),
                "proof_forms": proof_forms,
                "source_trace_types": dict(trace_types),
                "source_environments": dict(Counter(r["environment"] for r in rows)),
                "printed_text_characters_median": float(np.median([len(r["text"]) for r in rows])),
                "nonempty_text_characters_median": float(
                    np.median([len(r["text"]) for r in rows if r["text"] != "no goals"])
                ),
                "printed_elision_rows": sum("⋯" in r["text"] for r in rows),
                "common_projection_within_object_spread_fraction": (
                    float(np.sum((centered @ common_axes) ** 2) / total_spread)
                    if total_spread
                    else 0
                ),
                "diameter_witness_records": [
                    rows[i]["record_id"] for i in form["diameter_row_indices"]
                ],
                "maximum_single_source_proof_diameter": max(p["diameter"] for p in proof_forms),
            }
        )
        construction.append(
            {
                "theorem_id": tid,
                "definition": "filled convex hull of all referenced physical vector rows",
                "vector_rows": indices,
                "record_ids": [r["record_id"] for r in rows],
                "matrix_sha256": hashlib.sha256(x.tobytes()).hexdigest(),
                "shape": list(x.shape),
                "deduplication": False,
            }
        )
        forms.append(form)
        print(
            json.dumps(
                {"object": len(forms), "theorem": tid, "rank": form["numerical_affine_rank"]}
            ),
            flush=True,
        )
    if sorted(all_rows) != list(range(len(records))):
        raise ValueError("physical rows omitted or assigned to multiple objects")
    pairs = [json.loads(s) for s in (root / "pair-results.jsonl").read_text().splitlines()]
    segments = []
    for pair in pairs:
        if pair["relation"] != "nontrivial_intersection":
            continue
        endpoints = vectors[[lookup[rid] for rid in pair["witness_records"][:2]]]
        certificate = certify_shared_segment(arrays[pair["a"]], arrays[pair["b"]], endpoints)
        segments.append(
            {
                "a": pair["a"],
                "b": pair["b"],
                **certificate,
                "endpoint_record_ids": pair["witness_records"][:2],
                "endpoint_texts": [
                    records[lookup[rid]]["text"] for rid in pair["witness_records"][:2]
                ],
                "segment_length": float(np.linalg.norm(endpoints[0] - endpoints[1])),
            }
        )
    measured = [
        "rows_used",
        "coordinate_locations_diagnostic",
        "numerical_affine_rank",
        "diameter",
        "lateral_extent_over_diameter",
        "row_spread_first_axis_fraction",
        "row_spread_first_two_axes_fraction",
        "row_spread_participation_dimension",
        "empty_display_fraction",
        "empty_vs_nonempty_between_group_spread_fraction",
        "common_projection_within_object_spread_fraction",
    ]
    correlations = {}
    for a, b in [
        ("rows_used", "numerical_affine_rank"),
        ("source_proof_records", "diameter"),
        ("nonempty_text_characters_median", "diameter"),
        ("empty_display_fraction", "row_spread_first_axis_fraction"),
    ]:
        correlations[f"{a} / {b}"] = float(
            spearmanr([f[a] for f in forms], [f[b] for f in forms]).statistic
        )
    ordered = sorted(forms, key=lambda f: (f["diameter"], f["theorem_id"]))
    widest = sorted(forms, key=lambda f: (-f["lateral_extent_over_diameter"], f["theorem_id"]))[0]
    summary = {
        "theorems": len(forms),
        "physical_rows": len(records),
        "source_proof_records": sum(f["source_proof_records"] for f in forms),
        "families": dict(Counter(f["family"] for f in forms)),
        "empty_display_rows": sum(f["empty_display_rows"] for f in forms),
        "objects_with_empty_display": sum(f["empty_display_rows"] > 0 for f in forms),
        "diameter_witnesses_using_empty_display": sum(
            f["diameter_witness_uses_empty_display"] for f in forms
        ),
        "objects_with_all_locations_exposed": sum(
            f["all_locations_exposed_by_own_direction"] for f in forms
        ),
        "objects_with_maximal_affine_rank": sum(
            f["maximal_rank_for_observed_locations"] for f in forms
        ),
        "rank_changes_at_relative_1e_8": sum(
            f["numerical_affine_rank"] != f["rank_relative_1e_8"] for f in forms
        ),
        "rank_changes_at_relative_1e_6": sum(
            f["numerical_affine_rank"] != f["rank_relative_1e_6"] for f in forms
        ),
        "objects_with_diameter_exceeding_every_source_proof": sum(
            f["diameter"] > f["maximum_single_source_proof_diameter"] + 1e-12 for f in forms
        ),
        "distributions": {key: describe([f[key] for f in forms]) for key in measured},
        "axes_for_recorded_spread": {
            str(p): describe([f["row_spread_axes"][str(p)] for f in forms]) for p in (90, 95, 99)
        },
        "descriptive_spearman_no_independence_or_causality_claim": correlations,
        "example_selection": {
            "minimum_diameter": ordered[0]["theorem_id"],
            "lower_median_diameter": ordered[(len(ordered) - 1) // 2]["theorem_id"],
            "maximum_diameter": ordered[-1]["theorem_id"],
            "largest_lateral_extent_ratio": widest["theorem_id"],
        },
        "pair_relations": dict(Counter(p["relation"] for p in pairs)),
        "semantic_geometry_validated": False,
        "deduplication": False,
        "source_archive": str(root),
        "source_checksums_sha256": sha(root / "SHA256SUMS"),
        "analysis_code_sha256": sha(Path(__file__)),
        "geometry_code_sha256": sha(Path("src/noema/theorem_forms.py")),
    }
    atomic_json(out / "construction.json", construction)
    atomic_json(out / "forms.json", forms)
    atomic_json(out / "summary.json", summary)
    atomic_json(out / "segment-certificate.json", segments)
    examples = []
    for rule, tid in summary["example_selection"].items():
        form = next(f for f in forms if f["theorem_id"] == tid)
        witnesses = [records[lookup[rid]] for rid in form["diameter_witness_records"]]
        examples.append(
            {
                "selection_rule": rule,
                "theorem_id": tid,
                "diameter_witnesses": witnesses,
                "source_proofs": [
                    {"proof_id": pid, "body": by_proof[pid]["body"]}
                    for pid in sorted({r["proof_id"] for r in witnesses})
                ],
            }
        )
    atomic_json(out / "examples.json", examples)
    np.savez(out / "local-projections.npz", xy=all_local_xy, axes=axes_list, origins=origins)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
