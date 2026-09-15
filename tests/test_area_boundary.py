import numpy as np
import pytest

from noema.area_boundary import area_boundary, conflict, exact_coordinates, simple


def test_boundary_visits_interior_point_and_minimizes_square_example():
    x = [[0, 0], [2, 0], [2, 2], [0, 2], [1, 1]]
    r = area_boundary(x)
    assert r["global_minimum_proven"]
    assert r["area"] == 3
    assert r["convex_area"] == 4
    assert len(r["order"]) == 5
    assert r["all_rows_on_boundary"]


def test_coincident_records_keep_separate_membership():
    r = area_boundary([[0, 0], [1, 0], [0, 1], [1, 0], [0, 0]])
    assert r["input_rows"] == 5
    assert len(r["row_to_location"]) == 5
    assert r["row_to_location"][0] == r["row_to_location"][4]
    assert r["area"] == 0.5
    assert not r["records_deduplicated"]


def test_exact_predicates_reject_crossing_touching_and_backtracking():
    assert conflict((0, 0), (2, 2), (0, 2), (2, 0))
    assert conflict((0, 0), (2, 0), (1, 0), (1, 1))
    assert conflict((0, 0), (2, 0), (2, 0), (1, 0))
    assert not conflict((0, 0), (2, 0), (2, 0), (3, 0))
    assert not simple([0, 1, 2, 3], [(0, 0), (2, 2), (0, 2), (2, 0)])


def test_heuristic_preserves_every_point_and_polygon_validity():
    x = np.random.default_rng(14).uniform(-1, 1, (14, 2))
    r = area_boundary(x)
    assert not r["global_minimum_proven"]
    assert r["status"] == "area_local_minimum_global_unproven"
    _, _, points, _ = exact_coordinates(r["vertices"])
    assert simple(r["order"], points)
    assert sorted(r["order"]) == list(range(14))
    assert 0 < r["area"] < r["convex_area"]


def test_translation_and_scale_preserve_exact_search_choice_of_area():
    x = np.array([[0, 0], [4, 0], [4, 4], [0, 4], [1, 2], [3, 2]], dtype=float)
    a, b = area_boundary(x), area_boundary(x * 4 + [10, -20])
    assert b["area"] == pytest.approx(a["area"] * 16)
    assert b["fraction_of_convex_area"] == a["fraction_of_convex_area"]


def test_point_and_collinear_cases_have_no_fabricated_area():
    p = area_boundary([[0.1, 0.3]] * 4)
    assert p["status"] == "point" and p["area"] == 0
    line = area_boundary([[0, 0], [1, 1], [2, 2], [1, 1]])
    assert line["status"] == "collinear_boundary" and line["area"] == 0
