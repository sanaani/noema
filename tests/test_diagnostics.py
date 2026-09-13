import numpy as np
import pytest

from noema.diagnostics import cluster_intervals, edge_auc, proof_edges, stricter_groups
from noema.formal_experiment import sampled_states, select_groups


def test_paired_theorem_bootstrap_preserves_self_matches_and_gain():
    matrix = np.ones((12, 12)) - np.eye(12)
    result = cluster_intervals(matrix, matrix, repeats=100)
    assert result["statistics"]["pairwise_win_rate"]["percentile_95"] == [1, 1]
    assert result["statistics"]["gain_over_centroid"]["percentile_95"] == [0, 0]
    assert result == cluster_intervals(matrix, matrix, repeats=100)
    with pytest.raises(ValueError):
        cluster_intervals(matrix, np.ones((2, 2)))


def test_graph_distance_auc_handles_ties_and_known_edges():
    vectors = np.array([[0.0], [0.1], [10.0]])
    assert edge_auc(vectors, [2, 3, 4], {(2, 3)})["auc"] == 1
    assert edge_auc(vectors * 0, [2, 3, 4], {(2, 3)})["auc"] == 0.5
    assert edge_auc(vectors, [2, 3, 4], set())["auc"] is None


def test_graph_alignment_uses_actual_tactics_and_rejects_mismatch():
    proof = {
        "generator": "backward",
        "canonical_tree": {"rule": "h1", "children": [{"rule": "h0", "children": []}]},
        "tactics": [{"tactic": "apply h1"}, {"tactic": "exact h0"}],
        "states": [{"step": 0}, {"step": 1}],
    }
    assert proof_edges(proof) == {(0, 1)}
    proof["tactics"][0]["tactic"] = "apply h2"
    with pytest.raises(ValueError, match="alignment"):
        proof_edges(proof)
    forward = {
        "generator": "forward",
        "tactics": [
            {"tactic": "have f0 : p1 := h0"},
            {"tactic": "have f1 : p2 := h1 f0"},
            {"tactic": "exact f1"},
        ],
        "states": [{"step": 1}, {"step": 2}],
    }
    assert proof_edges(forward) == {(1, 2)}


def test_stricter_diversity_removes_shared_signatures():
    def proof(identity, rule):
        return {"proof_id": identity, "canonical_tree": {"rule": rule, "children": []}}

    groups = {
        "t": {
            "backward": [proof("a", "h0"), proof("b", "h1"), proof("c", "h1")],
            "forward": [proof("d", "h0"), proof("e", "h2")],
        }
    }
    strict = stricter_groups(groups, "premise_set")
    assert [p["proof_id"] for p in strict["t"]["backward"]] == ["b"]
    assert [p["proof_id"] for p in strict["t"]["forward"]] == ["e"]


def test_proof_splits_precede_balanced_occurrence_sampling():
    proofs = [
        {"proof_id": str(i), "states": [{"step": j, "content_sha256": str(j)} for j in range(9)]}
        for i in range(64)
    ]
    groups = {"t": {"backward": proofs, "forward": []}}
    ids, anchors, galleries = select_groups(groups, "backward")
    assert ids == ["t"]
    assert not ({p["proof_id"] for p in anchors[0]} & {p["proof_id"] for p in galleries[0]})
    sampled = sampled_states(anchors[0])
    assert len({(s["proof_id"], s["step"]) for s in sampled}) == 128
    assert sorted((s["proof_id"], s["step"]) for s in sampled) == sorted(
        (s["proof_id"], s["step"]) for s in sampled_states(list(reversed(anchors[0])))
    )
    assert sampled != sampled_states(anchors[0], seed=316843)
