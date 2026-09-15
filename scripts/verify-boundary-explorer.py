"""Verify every plotted row, exact boundary predicates, area, axes and zero."""

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from noema.area_boundary import area_boundary, exact_coordinates, simple
from noema.state_records import load_record_archive
from noema.theorem_admission import load_admission


def main():
    out = Path("results/theorem-boundaries-v2")
    summary = json.loads((out / "summary.json").read_text())
    root = Path(summary["source_archive"])
    assert (
        hashlib.sha256((root / "SHA256SUMS").read_bytes()).hexdigest()
        == summary["source_checksums_sha256"]
    )
    manifest, records, vectors = load_record_archive(root)
    corpus = json.load(gzip.open(Path(manifest["source_archive"]) / "corpus.json.gz"))
    objects = json.loads((out / "construction.json").read_text())
    assert {o["theorem_id"] for o in objects} == load_admission(corpus, root)
    assert sorted(i for o in objects for i in o["record_rows"]) == list(range(len(records)))
    expected = [i for i, r in enumerate(records) if r["text"] != "no goals"]
    assert sorted(i for o in objects for i in o["vector_rows"]) == expected
    boundaries = json.loads((out / "boundaries.json").read_text())
    verified = 0
    with np.load(out / "projections.npz", allow_pickle=False) as z:
        assert z["retained_rows"].tolist() == expected
        basis = z["common_axes"]
        assert np.allclose(basis.T @ basis, np.eye(2), atol=1e-12)
        common = np.einsum("ij,jk->ik", vectors, basis, optimize=False)
        # Saving a reversed-stride basis changes its memory layout. NumPy may
        # then reduce products in a different order; verify the linear map at
        # a floating-point dot-product error bound, not bitwise equality.
        projection_guard = 8 * vectors.shape[1] * np.finfo(float).eps
        maximum_projection_error = float(np.max(np.abs(common - z["common"])))
        assert maximum_projection_error < projection_guard
        assert np.array_equal(np.zeros(vectors.shape[1]) @ basis, np.zeros(2))
        assert np.linalg.norm(common, axis=1).max() <= 1 + 1e-12
        for j, o in enumerate(objects):
            rows = o["vector_rows"]
            raw = o["record_rows"]
            x = vectors[rows]
            assert all(records[i]["theorem_id"] == o["theorem_id"] for i in raw)
            assert o["original_matrix_sha256"] == hashlib.sha256(x.tobytes()).hexdigest()
            axes = z["local_axes"][j]
            assert np.allclose(axes @ axes.T, np.eye(2), atol=1e-12)
            local_error = float(
                np.max(
                    np.abs(
                        np.einsum("ij,kj->ik", vectors[raw], axes, optimize=False) - z["local"][raw]
                    )
                )
            )
            maximum_projection_error = max(maximum_projection_error, local_error)
            assert local_error < projection_guard
            for mode in ["common", "local"]:
                boundary = boundaries[o["theorem_id"]][mode]
                xy = z[mode][rows]
                assert boundary["input_rows"] == len(rows)
                sites, mapping, points, denominator = exact_coordinates(xy)
                assert boundary["vertices"] == [list(p) for p in sites]
                assert boundary["row_to_location"] == mapping
                order = boundary["order"]
                assert sorted(order) == list(range(len(sites)))
                area = abs(
                    sum(
                        points[a][0] * points[b][1] - points[a][1] * points[b][0]
                        for a, b in zip(order, order[1:] + order[:1], strict=True)
                    )
                )
                assert str(area) == boundary["area_exact_numerator"]
                assert str(2 * denominator) == boundary["area_exact_denominator"]
                assert boundary["area"] == area / (2 * denominator)
                assert boundary["area"] <= boundary["convex_area"]
                if area:
                    assert simple(order, points)
                if boundary["global_minimum_proven"]:
                    exact = area_boundary(xy)
                    assert exact["global_minimum_proven"]
                    assert exact["area_exact_numerator"] == boundary["area_exact_numerator"]
                verified += 1
    print(
        json.dumps(
            {
                "objects": len(objects),
                "frames_and_boundaries_verified": verified,
                "plotted_rows": len(expected),
                "original_records_preserved": len(records),
                "all_plotted_records_on_boundary": True,
                "no_empty_display_in_geometry": True,
                "original_origin_projects_to_zero": True,
                "exact_boundary_area_and_non_crossing_checks": True,
                "maximum_projection_recomputation_error": maximum_projection_error,
                "projection_roundoff_guard": projection_guard,
            }
        )
    )


if __name__ == "__main__":
    main()
