import numpy as np
import pytest
from scipy.stats import wasserstein_distance

from noema.clouds import cloud, match_sizes
from noema.metrics import energy, measure, mmd_squared, radius_coverage, sliced_wasserstein


@pytest.mark.parametrize("values", [[], [1, 2], [[1]], [[1], [np.nan]], [[1], [np.inf]]])
def test_invalid_cloud(values):
    with pytest.raises(ValueError):
        cloud(values)


def test_size_matching_preserves_unordered_distribution_and_duplicates():
    a = np.arange(80).reshape(20, 4)
    b = np.arange(48).reshape(12, 4)
    first = match_sizes(a, b, seed=7)
    shuffled = match_sizes(a[::-1], b[::-1], seed=7)
    for x, y in zip(first, shuffled, strict=True):
        np.testing.assert_array_equal(x, y)
        assert len(x) == 12
        assert len(np.unique(x, axis=0)) == 12
    duplicate, _ = match_sizes(np.ones((5, 2)), np.ones((5, 2)), seed=1)
    assert len(duplicate) == 5
    with pytest.raises(ValueError):
        match_sizes(a, b, seed=1, size=13)


def test_exact_distribution_and_translation_values():
    a = np.array([[0.0], [1.0]])
    b = a + 3
    assert energy(a, b) == pytest.approx(5.0)
    assert sliced_wasserstein(a, b) == pytest.approx(wasserstein_distance(a[:, 0], b[:, 0]))
    assert radius_coverage(a, b, radius=0.1) == 0
    assert radius_coverage(a, a, radius=0.1) == 1
    for metric in (energy, mmd_squared, sliced_wasserstein):
        assert metric(a, a) == pytest.approx(0, abs=1e-12)
        assert metric(a, b) == pytest.approx(metric(b, a))
        assert metric(a, b) == pytest.approx(metric(a + 100, b + 100))


def test_all_metrics_ignore_row_order():
    rng = np.random.default_rng(15)
    a, b = rng.normal(size=(2, 32, 8))
    result = measure(a, b, projection_seed=7, projections=16)
    shuffled = measure(
        a[rng.permutation(32)], b[rng.permutation(32)], projection_seed=7, projections=16
    )
    assert result == shuffled


def test_isometric_embedding_preserves_exact_distance_metrics():
    rng = np.random.default_rng(42)
    a, b = rng.normal(size=(2, 20, 2))
    basis, _ = np.linalg.qr(rng.normal(size=(12, 2)))
    for metric in (energy, mmd_squared):
        assert metric(a, b) == pytest.approx(metric(a @ basis.T, b @ basis.T))


def test_mmd_detects_shape_beyond_identical_centroids():
    a = np.array([[-1.0], [1.0]] * 16)
    b = np.zeros_like(a)
    assert np.linalg.norm(a.mean(axis=0) - b.mean(axis=0)) == 0
    assert mmd_squared(a, b) > 0.1


def test_identical_degenerate_cloud_and_unequal_sizes():
    a = np.zeros((8, 3))
    assert all(np.isfinite(v) for v in measure(a, a, projection_seed=0, projections=4).values())
    with pytest.raises(ValueError, match="equal sample"):
        energy(a, a[:4])
