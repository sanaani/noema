import pytest

from noema.corpus_pilot import state_metadata, support


def test_depth_metadata_uses_raw_tactic_positions():
    proof = {"tactics": [{}] * 5, "states": [{"step": 1}, {"step": 4}]}
    assert state_metadata(proof) == [{"L": 5, "i": 1, "u": 0.25}, {"L": 5, "i": 4, "u": 1.0}]
    with pytest.raises(ValueError, match="outside"):
        state_metadata({**proof, "states": [{"step": 5}]})


def test_support_requires_both_provers_on_sufficient_theorems():
    rows = [
        {"theorem_id": "a", "counts": {"backward": {"12": 80}, "forward": {"12": 30}}},
        {"theorem_id": "b", "counts": {"backward": {"12": 70}, "forward": {"12": 20}}},
        {"theorem_id": "c", "counts": {"backward": {"12": 90}, "forward": {"13": 99}}},
    ]
    assert support(rows, 2)[0]["common_capacity"] == 20
    assert support(rows, 3)[0]["common_capacity"] == 0
