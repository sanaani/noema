from noema.matching import depth_matched_states, maximum_common_support


def test_mixed_lengths_improve_common_support_without_cherry_picking_geometry():
    rows = [
        {
            "theorem_id": "a",
            "counts": {"backward": {"12": 9, "13": 8}, "forward": {"12": 7, "13": 6}},
        },
        {
            "theorem_id": "b",
            "counts": {"backward": {"12": 5, "13": 9}, "forward": {"12": 7, "13": 7}},
        },
        {"theorem_id": "c", "counts": {"backward": {"12": 6}, "forward": {"12": 9}}},
    ]
    result = maximum_common_support(rows, minimum_theorems=2)
    assert result["maximum_proofs_per_generator"] == 11
    assert result["length_allocation"] == {"12": 5, "13": 6}
    assert result["theorem_ids"] == ["a", "b"]
    assert result["subsets_examined"] == result["expected_subsets"] == 3


def test_no_shared_support_is_reported_as_zero():
    rows = [
        {"theorem_id": str(i), "counts": {"backward": {str(i): 20}, "forward": {str(i): 20}}}
        for i in range(3)
    ]
    assert maximum_common_support(rows, minimum_theorems=2)["maximum_proofs_per_generator"] == 0


def test_depth_sampling_has_exactly_equal_positions_at_fixed_lengths():
    proof = {"tactics": [{}] * 13, "states": [{"step": i} for i in range(1, 13)]}
    assert depth_matched_states(proof, n=4) == [{"step": i} for i in (3, 6, 9, 12)]
