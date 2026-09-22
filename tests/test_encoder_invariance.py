"""Analytic controls and fail-closed checks for the invariance experiment."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from conftest import assert_reproduces

from noema.encoder_invariance import ARMS, analyze, radial_change, ranking_change
from noema.paths import result_path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "invariance", ROOT / "scripts/audit-encoder-invariance.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_exact_cdf_retains_multiplicity_and_radius_scale():
    result = radial_change([0, 0, 2, 2], [0, 1, 1, 2])
    assert result["cdf_sup"] == 0.25
    assert result["wasserstein_1"] == 0.5
    assert result["max_paired_radius_drift"] == 1
    # A large CDF jump alone is not evidence of large geometric movement.
    tiny = radial_change([1, 1, 1], [1 + 1e-12] * 3)
    assert tiny["cdf_sup"] == 1
    assert tiny["wasserstein_1"] < 2e-12
    for bad in ([], [np.nan], [-1]):
        with pytest.raises(ValueError):
            radial_change(bad, bad)


def test_rank_ties_are_sets_and_not_arbitrary_index_breaks():
    a = np.array([[0, 1, 1], [1, 0, 2], [1, 2, 0]], dtype=float)
    b = np.array([[0, 1.1, 0.9], [1.1, 0, 2], [0.9, 2, 0]])
    result = ranking_change(a, b, 1e-6)
    assert result[0]["before_nearest"] == [1, 2]
    assert result[0]["after_nearest"] == [2]
    assert result[0]["strict_order_reversals"] == 0
    assert result[0]["strict_comparable_pairs"] == 0


def test_joint_isometry_preserves_density_but_one_sided_change_does_not():
    records, vectors = [], []
    for t in range(3):
        for step in range(3):
            for arm in ARMS:
                records.append({"checkpoint": f"t{t}/0/{step}", "arm": arm, "text": str(step)})
                base = np.array([t * 10 + step, 0.0])
                vectors.append(base if arm == "original" else base + [0, 3])
    x = np.array(vectors)
    originals = x[[i for i, r in enumerate(records) if r["arm"] == "original"]]
    result = analyze(records, x, originals)
    assert result["repeat_encoding_max_drift"] == 0
    assert all(not r["radial_invariance_falsified"] for r in result["objects"])
    assert all(r["point_invariance_falsified"] for r in result["objects"])
    assert all(r["center_only"]["max_paired_radius_drift"] == 3 for r in result["objects"])
    assert all(r["nearest_center_sets_changed"] == 0 for r in result["summary"].values())


def test_lean_evidence_rejects_missing_rows_false_certificates_and_bad_axioms():
    root = result_path("encoder-invariance-v1")
    source, log = (root / "Fixtures.lean").read_text(), (root / "lean-output.log").read_text()
    states, proofs = audit.read_lean(source, log)
    assert len(proofs) == 16
    assert any(r["goal_count"] > 1 for r in states)
    assert len([r for r in states if r["arm"] == "original" and r["goal_count"]]) == 44
    lines = log.splitlines()
    state_line = next(i for i, line in enumerate(lines) if line.startswith("STATE "))
    with pytest.raises(ValueError, match="missing or duplicate"):
        audit.read_lean(source, "\n".join(lines[:state_line] + lines[state_line + 1 :]))
    for broken, message in (
        (log.replace('"defeq":true', '"defeq":false', 1), "defeq"),
        (log.replace('"axioms":[]', '"axioms":["sorryAx"]', 1), "axioms"),
        (log + "\nerror: rejected proof", "unexpected"),
    ):
        with pytest.raises(ValueError, match=message):
            audit.read_lean(source, broken)


def test_archive_numerical_results_reproduce():
    root = result_path("encoder-invariance-v1")
    result, syntax = audit.analyze_saved(root)
    assert_reproduces(result, json.loads((root / "analysis.json").read_text()))
    assert_reproduces(syntax, json.loads((root / "syntax-control.json").read_text()))
    vectors = np.load(root / "vectors.npy", allow_pickle=False)
    assert vectors.shape == (220, 1472)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1, rtol=0, atol=1e-12)
