"""Check Phase 22's within-stratum AUC and the grain rule."""

import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


p11 = load("phase11", "run-phase11.py")
p22 = load("phase22", "run-phase22.py")


def test_one_stratum_matches_plain_auc():
    rng = np.random.default_rng(0)
    s = rng.integers(0, 5, 200).astype(float)
    y = rng.random(200) < 0.3
    w = rng.integers(0, 3, 200).astype(float)
    z = np.zeros(200, int)
    assert np.isclose(p22.strat_auc(s, y, z, w), p11.auc(s, y, w))


def test_between_stratum_differences_earn_nothing():
    # stratum 1 has most positives and higher scores; within each stratum, scores are useless
    s = np.array([0.0, 0.0, 1.0, 1.0, 1.0, 1.0])
    y = np.array([False, True, True, True, True, False])
    g = np.array([0, 0, 1, 1, 1, 1])
    assert np.isclose(p22.strat_auc(s, y, g), 0.5)
    assert p11.auc(s, y) > 0.5


def test_pooled_by_comparisons():
    # stratum 0: 1 pos x 1 neg, ranked right; stratum 1: 1 pos x 3 neg, ranked wrong
    s = np.array([0, 1, 1, 1, 1, 0.0])
    y = np.array([False, True, False, False, False, True])
    g = np.array([0, 0, 1, 1, 1, 1])
    assert np.isclose(p22.strat_auc(s, y, g), 1 / 4)


def test_choose_grain():
    assert p22.choose_grain({"route": (12, 150), "target area": (20, 200)}) == "route"
    assert p22.choose_grain({"route": (8, 150), "target area": (20, 200)}) == "target area"
    assert p22.choose_grain({"route": (8, 150), "target area": (20, 90)}) is None
    y = np.array([True, False, True, True])
    assert p22.usable(y, np.array([0, 0, 1, 1])) == (1, 1)
