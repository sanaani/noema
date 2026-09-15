import numpy as np
import pytest

from noema.theorem_forms import certify_shared_segment, measure_form


def test_square_extent_and_distribution_are_different_measurements():
    square = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    form, *_ = measure_form(square, [True, False, False, False])
    repeated, *_ = measure_form(np.vstack([square, np.tile(square[0], (100, 1))]), [False] * 104)
    assert form["diameter"] == pytest.approx(np.sqrt(2))
    assert form["empty_vs_nonempty_between_group_spread_fraction"] == pytest.approx(1 / 3)
    assert form["lateral_extent_over_diameter"] == pytest.approx(0.5)
    assert form["numerical_affine_rank"] == repeated["numerical_affine_rank"] == 2
    assert form["diameter"] == repeated["diameter"]
    assert repeated["rows_used"] == 104
    assert repeated["row_spread_first_axis_fraction"] > form["row_spread_first_axis_fraction"]


def test_rotation_and_translation_preserve_extent():
    x = np.array([[0.0, 0.0], [3.0, 0.0], [0.0, 4.0]])
    angle = 0.713
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    a, *_ = measure_form(x, [True, False, False])
    b, *_ = measure_form(x @ rotation + [2.0, -4.0], [True, False, False])
    for key in ["diameter", "lateral_extent", "row_spread_first_axis_fraction"]:
        assert a[key] == pytest.approx(b[key])
    assert a["diameter"] == 5
    assert not a["diameter_witness_uses_empty_display"]


def test_identical_rows_form_a_point_without_roundoff_rank():
    x = np.tile([0.1, 0.3], (71, 1))
    form, xy, *_ = measure_form(x, [True] * len(x))
    assert form["rows_used"] == 71
    assert form["numerical_affine_rank"] == 0
    assert form["diameter"] == 0
    assert not xy.any()
    assert form["row_spread_axes"]["95"] == 0


def test_unit_points_have_exposing_directions_even_with_repeated_rows():
    x = np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [1.0, 0.0]])
    form, *_ = measure_form(x, [False] * len(x))
    assert form["all_locations_exposed_by_own_direction"]
    assert form["minimum_exposing_gap"] == 1
    assert form["coordinate_locations_diagnostic"] == 3
    assert form["rows_used"] == 4


def test_segment_extent_certificate_uses_opposite_sides():
    endpoints = np.array([[0.0, 0.0], [1.0, 0.0]])
    a = np.vstack([endpoints, [0.5, 1.0], endpoints])
    b = np.vstack([endpoints, [0.5, -1.0]])
    result = certify_shared_segment(a, b, endpoints)
    assert result["extent"] == "exact_shared_segment"
    assert result["a_rows_checked"] == 5
    assert result["b_rows_checked"] == 3
    assert result["lower_a_other_rows"] > 0
    assert result["upper_b_other_rows"] < 0


def test_segment_witness_alone_does_not_exclude_area_overlap():
    endpoints = np.array([[0.0, 0.0], [1.0, 0.0]])
    a = np.vstack([endpoints, [0.5, 1.0]])
    result = certify_shared_segment(a, a, endpoints)
    assert result["extent"] == "at_least_shared_segment"


def test_different_empty_encodings_and_missing_endpoints_are_rejected():
    with pytest.raises(ValueError, match="empty displays"):
        measure_form([[0.0, 0.0], [1.0, 0.0]], [True, True])
    with pytest.raises(ValueError, match="generating row"):
        certify_shared_segment([[0.0, 0.0]], [[0.0, 0.0]], [[0.0, 0.0], [1.0, 0.0]])
