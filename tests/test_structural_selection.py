"""Lexical controls must be encoded, not merely ranked against."""

import pytest

from noema.comparison_encoders import partition_by_token_limit, select_structural_records


def make_selection():
    return {
        "background": ["bg1", "bg2"],
        "cases": [["label", "a1", "b1", "bridge1"]],
        "hard_controls": {"a1": ["lex1", "bg1"], "b1": ["lex2"]},
    }


def make_structural(names):
    return [{"name": name, "closed_payload": {"name": name}} for name in names]


def test_hard_controls_outside_background_are_selected():
    records, index = select_structural_records(
        make_selection(),
        make_structural(["a1", "b1", "bridge1", "bg1", "bg2", "lex1", "lex2"]),
    )
    assert set(index) == {"a1", "b1", "bridge1", "bg1", "bg2", "lex1", "lex2"}
    assert [record["name"] for record in records] == sorted(index)


def test_every_ranked_name_resolves_to_a_record():
    selection = make_selection()
    records, index = select_structural_records(
        selection,
        make_structural(["a1", "b1", "bridge1", "bg1", "bg2", "lex1", "lex2"]),
    )
    assert records  # records cover the index
    for _, a, b, bridge in selection["cases"]:
        assert index[bridge] is not None
        for anchor in (a, b):
            assert index[anchor] is not None
            for control in selection["hard_controls"][anchor]:
                assert index[control] is not None


def test_selection_name_missing_from_capture_raises():
    selection = make_selection()
    with pytest.raises(ValueError, match="missing from structural capture"):
        select_structural_records(selection, make_structural(["a1", "b1", "bg1"]))


def test_over_limit_lexical_control_is_rejected_not_truncated():
    records, _ = select_structural_records(
        make_selection(),
        make_structural(["a1", "b1", "bridge1", "bg1", "bg2", "lex1", "lex2"]),
    )
    lengths = [10 if record["name"] != "lex2" else 999 for record in records]
    fitting, rejected = partition_by_token_limit(
        records, lengths, 100, {"a1", "b1", "bridge1", "bg1", "bg2"}
    )
    assert rejected == {"lex2": 999}
    assert "lex2" not in {record["name"] for record in fitting}


def test_over_limit_critical_name_raises():
    records, _ = select_structural_records(
        make_selection(),
        make_structural(["a1", "b1", "bridge1", "bg1", "bg2", "lex1", "lex2"]),
    )
    lengths = [10 if record["name"] != "bg1" else 999 for record in records]
    with pytest.raises(ValueError, match="critical benchmark names exceed context"):
        partition_by_token_limit(records, lengths, 100, {"a1", "b1", "bridge1", "bg1", "bg2"})
