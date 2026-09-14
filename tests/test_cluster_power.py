import numpy as np
import pytest

from noema.cluster_power import block_tests, envelopes, sample_blocks, summarize
from noema.metrics import energy, mmd_squared


def test_block_statistics_match_frozen_estimators_and_ignore_state_duplication():
    rng = np.random.default_rng(24)
    x, y = rng.normal(size=(2, 8, 3, 5))
    result = block_tests(x, y, permutations=199, seed=43)
    for metric, reference in (("mmd_squared", mmd_squared), ("energy_statistic", energy)):
        assert result[metric]["statistic"] == pytest.approx(
            reference(x.reshape(-1, 5), y.reshape(-1, 5)), abs=1e-12
        )
    repeated = block_tests(
        np.repeat(x, 2, axis=1), np.repeat(y, 2, axis=1), permutations=199, seed=43
    )
    for metric in result:
        assert repeated[metric]["statistic"] == pytest.approx(result[metric]["statistic"])
        assert repeated[metric]["p_value"] == result[metric]["p_value"]


def test_permutations_use_whole_proofs():
    rng = np.random.default_rng(12)
    x, y = rng.normal(size=(2, 4, 2, 3))
    result = block_tests(x, y, permutations=19, seed=55)
    blocks = np.concatenate((x, y))
    rng = np.random.default_rng(55)
    statistics = []
    for _ in range(19):
        left = rng.permutation(8)[:4]
        right = np.array([i for i in range(8) if i not in left])
        statistics.append(energy(blocks[left].reshape(-1, 3), blocks[right].reshape(-1, 3)))
    observed = energy(x.reshape(-1, 3), y.reshape(-1, 3))
    expected = (1 + sum(value >= observed - 1e-12 for value in statistics)) / 20
    assert result["energy_statistic"]["p_value"] == expected


def test_correlated_sampler_and_qualification_require_null_controls():
    row = dict(m=8, n=4, d=256, noise=0.02, family="separated", effect=1.0)
    x, y = sample_blocks(row, seed=132, within_noise=0.1)
    assert x.shape == y.shape == (8, 4, 256)
    assert np.mean((x[:, 0] - x[:, 1]) ** 2) < np.mean((x[0] - x[1]) ** 2)
    trials = [{k: {"p_value": 0.001} for k in ("mmd_squared", "energy_statistic")}] * 100
    alternative = summarize(row, trials)
    assert all(item["minimum"] is None for item in envelopes([alternative]))
    controls = [
        summarize(
            {**row, "family": family},
            [{k: {"p_value": 0.5} for k in trials[0]}] * 100,
        )
        for family in ("gaussian_null", "ring_null")
    ]
    assert all(
        item["minimum"] == dict(m=8, n=4, points=32) for item in envelopes([alternative, *controls])
    )
