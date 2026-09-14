import numpy as np
import pytest

from noema.state_objects import assemble_object, hull_relation, sample_theorems, state_id


def test_sampling_is_only_theorems_and_insensitive_to_proof_counts():
    inv = {"theorems": [{"id": str(i), "proof_ids": []} for i in range(10)]}
    selected = sample_theorems(inv, 5, 123)["theorem_ids"]
    inv["theorems"][0]["proof_ids"] = [str(i) for i in range(400)]
    assert sample_theorems(inv, 5, 123)["theorem_ids"] == selected


def test_all_400_proofs_and_every_state_are_retained():
    theorem = {"id": "T", "proof_ids": [str(i) for i in range(400)]}
    proofs = [
        {
            "id": str(i),
            "theorem_id": "T",
            "trace_complete": True,
            "states": [{"text": f"state {j}", "kind": "before"} for j in range(i % 9 + 1)],
        }
        for i in range(400)
    ]
    vectors = {state_id(f"state {i}"): {"encoder_id": "fixed", "vector": [i, 1]} for i in range(9)}
    obj = assemble_object(theorem, proofs, vectors, "fixed")
    assert obj["inventory_complete"]
    assert len(obj["occurrences"]) == sum(len(p["states"]) for p in proofs)
    assert obj["vectors"].shape == (9, 2)
    assert not assemble_object(theorem, proofs[:-1], vectors, "fixed")["inventory_complete"]
    theorem["proof_ids"].append("newly_discovered_proof")
    assert not assemble_object(theorem, proofs, vectors, "fixed")["inventory_complete"]


def test_missing_state_and_failed_trace_are_not_complete():
    t = {"id": "T", "proof_ids": ["p"]}
    p = {
        "id": "p",
        "theorem_id": "T",
        "trace_complete": False,
        "states": [{"text": "A", "kind": "before"}],
    }
    assert not assemble_object(t, [p], {}, "fixed")["inventory_complete"]
    with pytest.raises(ValueError, match="mixed encoder"):
        assemble_object(t, [p], {state_id("A"): {"encoder_id": "other", "vector": [1]}}, "fixed")


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ([[0, 0], [1, 0], [0, 1]], [[2, 0], [3, 0], [2, 1]], "disjoint"),
        ([[0, 0], [1, 0], [0, 1]], [[1, 0], [2, 0], [1, 1]], "intersect"),
        ([[0, 0], [3, 0], [0, 3]], [[0.5, 0.5], [1, 0.5], [0.5, 1]], "intersect"),
        ([[1, 0], [-1, 0]], [[0, 1], [0, -1]], "intersect"),
        ([[0, 0], [0, 0]], [[1, 1]], "disjoint"),
    ],
)
def test_certificates(a, b, expected):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    result = hull_relation(a, b)
    assert result["relation"] == expected
    if expected == "intersect":
        assert np.allclose(np.array(result["alpha"]) @ a, np.array(result["beta"]) @ b)
    else:
        normal = np.array(result["normal"])
        assert np.min(a @ normal) > np.max(b @ normal)


def test_projection_does_not_decide_original_intersection():
    a = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
    b = a + [0, 0, 1]
    assert hull_relation(a, b)["relation"] == "disjoint"
    assert hull_relation(a[:, :2], b[:, :2])["relation"] == "intersect"


def test_more_than_eight_vertices_and_permutation_invariance():
    a = np.eye(32)
    b = np.ones((1, 32)) / 32
    for points in (a, a[::-1], np.repeat(a, 2, axis=0)):
        assert hull_relation(points, b)["relation"] == "intersect"
    assert hull_relation(a[:-1], b)["relation"] == "disjoint"


def test_contact_extent_keeps_shared_point_and_certifies_only_contact():
    from noema.state_objects import hull_contact_extent

    a = np.array([[0.0, 0], [1, 0], [0, 1]])
    b = np.array([[0.0, 0], [-1, 0], [0, -1]])
    r = hull_contact_extent(a, b, a[0])
    assert r["relation"] == "point_contact"
    normal = np.array(r["normal_coefficients_a"]) @ a + np.array(r["normal_coefficients_b"]) @ b
    assert np.min(a[1:] @ normal) > 0 > np.max(b[1:] @ normal)
    assert hull_relation(a, b)["relation"] == "intersect"


def test_contact_extent_finds_a_segment_without_shared_nonterminal_vertices():
    from noema.state_objects import hull_contact_extent

    a = np.array([[0.0, 0], [2, 0], [0, 2]])
    b = np.array([[0.0, 0], [1, 1], [3, 0]])
    r = hull_contact_extent(a, b, a[0])
    assert r["relation"] == "nontrivial_intersection"
    assert np.allclose(np.array(r["alpha"]) @ a, np.array(r["beta"]) @ b)
    assert r["distance_from_shared_point"] > 0
