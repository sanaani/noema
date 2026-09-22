"""Distinguish a representation fix, numerical invariance, and semantic collapse."""

import importlib.util
import json
from pathlib import Path

import numpy as np
from conftest import assert_reproduces

from noema.encoder_invariance import ARMS, radial_change
from noema.paths import result_path

ROOT = Path(__file__).resolve().parents[1]
OUT = result_path("encoder-comparison-v1")
spec = importlib.util.spec_from_file_location("comparison", ROOT / "scripts/compare-encoders.py")
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def fake_contrasts():
    records, vectors, tokens = [], [], []
    for p in range(12):
        for side in ("a", "b"):
            for arm in ARMS:
                records.append({"checkpoint": f"c{p:02}/{side}/0", "arm": arm})
                vectors.append([float(side == "b"), 0])
                tokens.append([int(side == "b")])
    return records, np.array(vectors), tokens


def test_constant_encoder_fails_distinctions_even_when_invariant():
    records, vectors, tokens = fake_contrasts()
    result = comparison.contrast_analysis(records, vectors * 0, tokens, 1e-6)
    assert result["collapsed_pairs"] == 12
    assert result["equivalent_closer"] == 0
    assert result["ties"] == 96
    assert result["worst_equivalent_shift_over_contrast"] is None
    retained = comparison.contrast_analysis(records, vectors, tokens, 1e-6)
    assert retained["collapsed_pairs"] == 0
    assert retained["equivalent_closer"] == 96
    assert retained["ties"] == 0


def test_token_collision_and_bad_equivalent_distance_are_separate():
    records, vectors, tokens = fake_contrasts()
    tokens[5] = tokens[0]
    vectors[1] = [2, 0]
    result = comparison.contrast_analysis(records, vectors, tokens, 1e-6)
    assert result["token_collisions"] == 1
    assert result["collapsed_pairs"] == 0
    assert result["equivalent_closer"] == 95
    assert result["worst_equivalent_shift_over_contrast"] == 2


def test_cdf_identity_is_not_paired_radius_identity():
    result = radial_change([0, 1, 2], [0, 2, 1])
    assert result["max_paired_radius_drift"] == 1
    assert result["wasserstein_1"] == result["cdf_sup"] == 0


def test_canonicalization_preserves_context_boundary_and_distinctions():
    inputs = json.loads((OUT / "inputs.json").read_text())
    assert len(inputs) == 340
    assert sum(r["kind"] == "fixture" for r in inputs) == 220
    assert sum(r["arm"] == "original" for r in inputs) == 68
    for checkpoint in {r["checkpoint"] for r in inputs}:
        variants = [r for r in inputs if r["checkpoint"] == checkpoint]
        assert {r["arm"] for r in variants} == set(ARMS)
        assert len({r["canonical_text"] for r in variants}) == 1
        assert len({r["structural_text"] for r in variants}) == 1
        assert all(g["canonical_defeq"] for r in variants for g in r["goals"])
    lookup = {(r["checkpoint"], r["arm"]): r for r in inputs}
    for key in ("canonical_text", "structural_text"):
        for p in range(12):
            a, b = (lookup[f"c{p:02}/{side}/0", "original"][key] for side in ("a", "b"))
            assert a != b
        # Introduction changes layout; closing a telescope must not erase it.
        assert lookup["and_swap/0/0", "original"][key] != lookup["and_swap/0/1", "original"][key]


def test_completed_archives_reproduce_and_keep_physical_occurrences():
    for name in comparison.MODELS:
        folder = OUT / name
        assert (folder / "execution.json").exists(), name
        measured = comparison.measure(name)
        assert_reproduces(measured, json.loads((folder / "analysis.json").read_text()))
        for representation, result in measured.items():
            vectors = np.load(folder / f"{representation}-vectors.npy", allow_pickle=False)
            assert len(vectors) == 340
            assert np.allclose(np.linalg.norm(vectors, axis=1), 1, rtol=0, atol=1e-10)
            assert result["contrasts"]["comparisons"] == 96
            assert not result["semantic_geometry_validated"]


def test_saved_symbol_diagnostic_explains_the_collision():
    diagnostic = json.loads((OUT / "tokenizer-symbol-diagnostic.json").read_text())
    assert diagnostic["exploratory"]
    for name, data in diagnostic["models"].items():
        symbols = {r["input"]: r for r in data["symbols"]}
        if name == "leansearch":
            assert symbols["≠"]["normalized"] == "≠"
            assert symbols["≠"]["ids"] != symbols["="]["ids"]
        else:
            assert symbols["≠"]["normalized"] == "="
            assert symbols["≠"]["ids"] == symbols["="]["ids"]


def test_reprover_reference_matches_original_frozen_rows():
    current = json.loads((OUT / "inputs.json").read_text())
    frozen = result_path("encoder-invariance-v1")
    original = json.loads((frozen / "inputs.json").read_text())
    selected = [i for i, r in enumerate(current) if r["kind"] == "fixture"]
    for i, row in zip(selected, original, strict=True):
        assert current[i]["text"] == row["text"]
        assert current[i]["checkpoint"] == row["checkpoint"]
        assert current[i]["arm"] == row["arm"]
    a = np.load(OUT / "reprover/raw-vectors.npy", allow_pickle=False)[selected]
    b = np.load(frozen / "vectors.npy", allow_pickle=False)
    assert np.allclose(a, b, atol=1e-12, rtol=0)
