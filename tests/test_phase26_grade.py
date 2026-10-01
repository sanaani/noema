"""Check Phase 26's textbook filter, area bootstrap and verdict tables."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("scipy")

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phase26", ROOT / "scripts/run-phase26.py")
p26 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p26)


def test_textbook_mask_takes_the_broadest_tenth():
    breadth = np.arange(1, 21)
    assert p26.textbook_mask(breadth).sum() == 2
    assert p26.textbook_mask(breadth)[-1]


def test_area_bootstrap_without_resampling_noise():
    met = np.array([2, 2, 2])
    n = np.array([20, 20, 20])
    prec = p26.area_bootstrap(met, n, 50, np.random.default_rng(0))
    assert np.allclose(prec, 0.1)


def test_verdicts():
    assert p26.h1_verdict(12, 3) == "far better than chance"
    assert p26.h1_verdict(4, 1.5) == "better than chance"
    assert p26.h1_verdict(4, 0.9) == "no better than chance"
    assert p26.h2_verdict(1, 5) == "embedding is better"
    assert p26.h2_verdict(-5, 3) == "no measurable difference"
    assert p26.h2_verdict(-5, -1) == "embedding is worse"
