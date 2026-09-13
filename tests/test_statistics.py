import itertools

import numpy as np
import pytest

from noema.metrics import mmd_squared
from noema.statistics import benjamini_hochberg, permutation_mmd, wilson_interval


def test_permutation_matches_direct_monte_carlo_reference():
    a = np.array([[0.0], [1.0], [2.0]])
    b = np.array([[3.0], [4.0], [5.0]])
    observed = mmd_squared(a, b)
    pooled = np.vstack((a, b))
    rng = np.random.default_rng(11)
    exceedances = 0
    for _ in range(137):
        order = rng.permutation(6)
        statistic = mmd_squared(pooled[order[:3]], pooled[order[3:]])
        exceedances += statistic >= observed - 1e-12
    result = permutation_mmd(a, b, seed=11, permutations=137)
    assert result["p_value"] == (exceedances + 1) / 138
    assert result == permutation_mmd(a[::-1], b[::-1], seed=11, permutations=137)


def test_permutation_agrees_with_small_exact_distribution():
    a = np.zeros((3, 1))
    b = np.ones((3, 1)) * 8
    pooled = np.vstack((a, b))
    observed = mmd_squared(a, b)
    exact = []
    for selected in itertools.combinations(range(6), 3):
        other = sorted(set(range(6)) - set(selected))
        exact.append(mmd_squared(pooled[list(selected)], pooled[other]) >= observed - 1e-12)
    result = permutation_mmd(a, b, seed=98, permutations=9999)
    assert result["p_value"] == pytest.approx(np.mean(exact), abs=0.015)


def test_degenerate_null_never_rejected_and_p_never_zero():
    a = np.zeros((12, 3))
    assert permutation_mmd(a, a, seed=4, permutations=39)["p_value"] == 1
    assert permutation_mmd(a, a + 10, seed=4, permutations=39)["p_value"] >= 1 / 40


def test_bh_known_values_and_original_order():
    assert benjamini_hochberg([0.04, 0.001, 0.03, 0.2]) == pytest.approx(
        [0.0533333333, 0.004, 0.0533333333, 0.2]
    )
    assert benjamini_hochberg([]) == []
    with pytest.raises(ValueError):
        benjamini_hochberg([np.nan])


def test_wilson_reference_and_extremes():
    assert wilson_interval(50, 100) == pytest.approx([0.40383153, 0.59616847])
    assert wilson_interval(0, 100)[0] == pytest.approx(0)
    assert wilson_interval(100, 100)[1] == pytest.approx(1)


def test_iid_null_calibration_and_separated_power():
    rng = np.random.default_rng(85)
    null_rejections = 0
    alternative_rejections = 0
    for i in range(100):
        a, b = rng.normal(size=(2, 24, 2))
        null_rejections += permutation_mmd(a, b, seed=i, permutations=99)["p_value"] <= 0.05
        alternative_rejections += (
            permutation_mmd(a, b + 4, seed=i, permutations=99)["p_value"] <= 0.05
        )
    # Broad regression bounds; these are not scientific qualification thresholds.
    assert 0 < null_rejections < 15
    assert alternative_rejections >= 95
