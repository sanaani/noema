import pytest

from noema.archive_validation import compare_archive


def test_archive_tolerance_retains_exact_outcomes_and_reports_float_drift():
    expected = {"distances": [0.25, 0.4], "outcomes": [1, 0], "passed": False}
    actual = {**expected, "distances": [0.25 + 1e-16, 0.4]}
    check = compare_archive(actual, expected)
    assert not check["all_fields_exact"]
    assert check["floating_differences"] == 1
    assert check["maximum_absolute_error"] < 1e-15
    for corrupted in (
        {**expected, "outcomes": [1, 1]},
        {**expected, "passed": True},
        {**expected, "distances": [0.251, 0.4]},
        {**expected, "distances": [float("nan"), 0.4]},
    ):
        with pytest.raises(ValueError, match="mismatch"):
            compare_archive(corrupted, expected)
