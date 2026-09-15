"""Prevent whole-proof wrappers and ambiguous nested observations posing as endpoints."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "endpoint_audit", Path(__file__).parents[1] / "scripts/audit-proof-endpoints.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def pair(index, start, end, before="goal", after="no goals", tactic="exact h"):
    base = {
        "tactic_index": index,
        "pos": {"line": start, "column": 0},
        "endPos": {"line": end, "column": 0},
        "tactic": tactic,
    }
    return [
        {**base, "kind": "state_before", "text": before},
        {**base, "kind": "state_after", "text": after},
    ]


def test_inner_final_tactic_selected_over_whole_proof_wrapper():
    states = pair(0, 1, 8, tactic="by ...") + pair(1, 2, 3) + pair(2, 7, 8)
    selected, status = audit.closing_candidate(states)
    assert status == "selected"
    assert selected[0]["tactic_index"] == 2


def test_local_completion_does_not_count_as_final_if_later_node_remains():
    states = pair(0, 1, 2) + pair(1, 3, 4, after="still an obligation")
    selected, status = audit.closing_candidate(states)
    assert selected is None
    assert status == "no_nonempty_closing_tactic_at_last_source_end"


def test_conflicting_observations_at_final_position_are_not_arbitrarily_selected():
    states = pair(0, 3, 4, before="goal A") + pair(1, 3, 4, before="goal B")
    selected, status = audit.closing_candidate(states)
    assert selected is None
    assert status == "ambiguous_terminal_before_state"
