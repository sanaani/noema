import numpy as np
import pytest

from noema.formal_experiment import proof_groups, ranking, theorem_permutation_test


def test_rank_ties_have_chance_score_not_arbitrary_first_match():
    result = ranking(np.zeros((8, 8)))
    assert result["pairwise_win_rate"] == 0.5
    assert result["top1_accuracy"] == 1 / 8
    assert result["mean_rank"] == 4.5
    assert theorem_permutation_test(np.zeros((8, 8)), permutations=99) == 1


def test_perfect_matches_and_whole_label_permutations():
    distance = np.ones((8, 8)) - np.eye(8)
    assert ranking(distance)["pairwise_win_rate"] == 1
    assert ranking(distance)["top1_accuracy"] == 1
    assert theorem_permutation_test(distance, permutations=999) <= 0.01
    # Fixed relabeling removes the designated true matching without altering point clouds.
    shifted = distance[:, np.roll(np.arange(8), 1)]
    assert ranking(shifted)["pairwise_win_rate"] < 0.5


def test_duplicate_proofs_fail_before_embedding():
    proof = {
        "proof_id": "same",
        "theorem_id": "t",
        "generator": "backward",
        "duplicate_sequence": False,
        "states": [None] * 4,
    }
    with pytest.raises(ValueError, match="shared proof"):
        proof_groups({"proofs": [proof, {**proof, "generator": "forward"}]})


def test_gate_requires_both_controls_incremental_signal_and_no_collapse():
    from noema.formal_experiment import feasibility_gate

    rows = [
        {
            "encoder": "minilm",
            "direction": "cross",
            "view": view,
            "q_value": 0.05,
            "gain_over_centroid": 0.05,
            "mean_unique_vectors_per_anchor": 2,
            "mean_unique_vectors_per_gallery": 2,
        }
        for view in ("full", "goal")
    ]
    assert feasibility_gate(rows)["status"] == "feasibility_pass"
    assert feasibility_gate(rows[:1])["status"] == "failed"
    rows[1]["gain_over_centroid"] = 0.049
    assert feasibility_gate(rows)["status"] == "failed"
    rows[1]["gain_over_centroid"] = 0.05
    rows[1]["mean_unique_vectors_per_gallery"] = 1
    assert feasibility_gate(rows)["status"] == "failed"
    rows[1]["mean_unique_vectors_per_gallery"] = 2
    rows[0]["q_value"] = 0.051
    assert feasibility_gate(rows)["status"] == "failed"


def test_analysis_resume_preserves_skips_and_never_passes_an_inadequate_corpus(
    tmp_path, monkeypatch
):
    import json

    from noema.formal_experiment import design, run

    class UnusedEncoder:
        manifest = {"model": "fixture"}

        def __init__(self, directory):
            pass

        def encode(self, states):
            pytest.fail("ineligible comparisons must not be embedded")

    monkeypatch.setattr("noema.formal_experiment.MiniLMEncoder", UnusedEncoder)
    monkeypatch.setattr("noema.formal_experiment.importlib.metadata.version", lambda _: "fixture")
    manifest = {"proofs": []}
    freeze = tmp_path / "freeze.json"
    freeze.write_text(json.dumps(design(manifest)))
    output = tmp_path / "analysis"
    result = run(manifest, root=tmp_path, output=output, freeze=freeze)
    assert result["gate"]["status"] == "failed"
    assert result["comparisons"] == []
    assert result["skipped"]
    with pytest.raises(ValueError, match="completed"):
        run(manifest, root=tmp_path, output=output, freeze=freeze, resume=True)
    (output / "report.json").unlink()
    (output / "FAILED").write_text("interrupted")
    resumed = run(manifest, root=tmp_path, output=output, freeze=freeze, resume=True)
    assert resumed["skipped"] == result["skipped"]
    assert resumed["fidelity"] == result["fidelity"]
    assert resumed["gate"] == result["gate"]
    assert not (output / "FAILED").exists()
