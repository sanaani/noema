import numpy as np
import pytest

from noema.associahedron import apply_step
from noema.strategy_transfer import (
    assignments,
    member_texts,
    paired_test,
    parse_goal,
    score_distances,
    token_distance,
    unpack_record,
)


def test_matched_population_has_independent_replay_labels_and_no_identity_matches():
    plan = assignments("development", 8)
    assert plan == assignments("development", 8)
    members = [m for b in plan["blocks"] for m in b["members"]]
    assert len({m["population_index"] for m in members}) == 24
    assert sorted(b["used_premise_overlap"] for b in plan["blocks"]) == [0] * 4 + [1] * 4
    for block in plan["blocks"]:
        anchor, positive, negative = map(unpack_record, block["members"])
        for candidate, required in ((positive, 0.75), (negative, 0.0)):
            success = 0
            for program in anchor["programs"]:
                current = candidate["source"]
                try:
                    for step in program:
                        current = apply_step(current, step)
                except ValueError:
                    continue
                success += current == candidate["target"]
            fraction = success / len(anchor["programs"])
            assert fraction >= required if required else fraction == 0
            assert (anchor["operator"] == candidate["operator"]) == bool(
                block["used_premise_overlap"]
            )
        texts = [member_texts(m) for m in block["members"]]
        assert all(len(points) == 8 and statement not in points for statement, points in texts)
        assert token_distance(texts[0][0], texts[1][0]) == token_distance(texts[0][0], texts[2][0])


def test_lean_equation_parser_preserves_structure_and_removes_only_layout():
    assert parse_goal("(f (f x0 x1) x2) = (f x0 (f x1 x2))") == parse_goal(
        "f (f x0 x1) x2 =\n f x0 (f x1 x2)"
    )
    assert parse_goal("f (f x0 x1) x2 = x3") != parse_goal("f x0 (f x1 x2) = x3")
    with pytest.raises(ValueError):
        parse_goal("g x0 x1 = sorry")


def test_exact_paired_test_and_ceiling_gate():
    gain, p = paired_test(np.ones(10), np.zeros(10))
    assert gain == 1 and p == 1 / 1024
    assert paired_test(np.ones(10), np.ones(10))[1] == 1
    plan = {
        "blocks": [{"tie_positive": bool(i % 2), "used_premise_overlap": i % 2} for i in range(32)]
    }
    ties = score_distances([[0, 0]] * 32, plan)
    assert ties["accuracy"] == ties["tie_adjusted_accuracy"] == 0.5
    assert ties["upper_95"] < 0.90
    perfect = score_distances([[0, 1]] * 32, plan)
    assert perfect["accuracy"] == perfect["upper_95"] == 1
