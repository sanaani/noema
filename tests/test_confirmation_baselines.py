import numpy as np

from noema.confirmation_baselines import supplemental_scores, tactic_histogram


def test_tactic_counts_exclude_theorem_binders():
    program = (((), 1),)
    member = {
        "source": ((0, 1), 2),
        "target": (0, (1, 2)),
        "leaves": 3,
        "operator": "f",
        "names": ["x0", "x1", "x2"],
        "programs": [program],
        "sampled_programs": [program] * 4,
    }
    # Each body contains refine, Eq.trans, hf, rfl once. The hg binder is excluded.
    np.testing.assert_array_equal(tactic_histogram(member), [0.5, 0.5, 0, 0, 0.5, 0, 0.5])


def test_position_control_retains_alignment_that_a_mean_loses(monkeypatch):
    members = [
        {"texts": ["plus", "minus"] * 4, "sampled_programs": [1, 2, 3, 4]},
        {"texts": ["plus", "minus"] * 4, "sampled_programs": [1, 2, 3, 4]},
        {"texts": ["minus", "plus"] * 4, "sampled_programs": [5, 6, 7, 8]},
    ]
    monkeypatch.setattr("noema.confirmation_baselines.member_texts", lambda m: ("", m["texts"]))
    monkeypatch.setattr("noema.confirmation_baselines.tactic_histogram", lambda m: np.ones(7))
    plan = {
        "blocks": [
            {"members": members, "tie_positive": False, "used_premise_overlap": i} for i in (0, 1)
        ]
    }
    scores = supplemental_scores(
        plan, {"syntax": {"plus": np.array([1.0]), "minus": np.array([-1.0])}}
    )
    assert scores["syntax_single_proof_mean"]["ties"] == 2
    assert scores["syntax_position_means"]["accuracy"] == 1
    assert scores["sampled_complete_trajectories"]["accuracy"] == 1
    assert scores["tactic_component_histogram"]["ties"] == 2
