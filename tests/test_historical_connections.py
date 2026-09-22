"""Check interpretable ranking and the saved initial-State pilot evidence."""

import importlib.util
from pathlib import Path

import pytest

from noema.paths import result_path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "historical_connections", ROOT / "scripts/historical-connections.py"
)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def test_rank_has_explicit_tie_semantics():
    result = pilot.rank_stats(0.5, [0.1, 0.5, 0.7, 0.9])
    assert result["rank"] == 2
    assert result["farther_fraction"] == 0.625
    assert result["controls"] == 4


def test_unicode_lexical_control_is_label_free():
    left = pilot.tokens("⊢ ∀ x : ℝ, Real.sin x = Real.sin x")
    right = pilot.tokens("⊢ ∀ x : ℂ, Complex.exp x = Complex.exp x")
    assert "ℝ" in left and "ℂ" in right
    assert pilot.jaccard(left, right) == pytest.approx(6 / 7)


def test_saved_pilot_has_all_presentations_for_every_selected_theorem():
    import json

    import numpy as np

    folder = result_path("historical-connections-v1")
    records = pilot.tagged(folder / "lean-output.log", "CENTER ")
    inputs = json.loads((folder / "inputs.json").read_text())
    selection = json.loads((folder / "selection.json").read_text())
    assert selection["protocol_sha256"] == pilot.digest(folder / "protocol.md")
    assert {r["name"] for r in records} == {r["name"] for r in selection["theorems"]}
    assert len(inputs) == 3 * len(records)
    for r in records:
        assert set(r["axioms"]) <= {"Classical.choice", "propext", "Quot.sound"}
        assert r["typed_roundtrip_defeq"]
        for v in ("typed", "closed", "introduced"):
            matches = [i for i in inputs if i["name"] == r["name"] and i["variant"] == v]
            assert len(matches) == 1 and matches[0]["text"] == r[v]
    vectors = np.load(folder / "vectors.npy", allow_pickle=False)
    assert vectors.shape == (len(inputs), 1472)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-12, rtol=0)
    saved = np.load(folder / "distances.npy", allow_pickle=False)
    for i in range(len(inputs)):
        assert np.allclose(
            saved[i], np.linalg.norm(vectors - vectors[i], axis=1), atol=1e-12, rtol=0
        )
    lookup = {(r["name"], r["variant"]): i for i, r in enumerate(inputs)}
    analysis = json.loads((folder / "analysis.json").read_text())
    for case in analysis["cases"]:
        for variant, result in case["variants"].items():
            a, b = lookup[case["a"], variant], lookup[case["b"], variant]
            assert result["distance"] == pytest.approx(saved[a, b], abs=1e-12)
            for direction in result["directions"]:
                i, j = lookup[direction["anchor"], variant], lookup[direction["target"], variant]
                ids = [lookup[n, variant] for n in selection["background"]]
                assert direction["background"]["rank"] == 1 + sum(
                    saved[i, k] < saved[i, j] - 1e-12 for k in ids
                )
