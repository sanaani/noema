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
