"""Check Phase 19's design matrix and that the Poisson fit recovers an interaction."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("sklearn")

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phase19", ROOT / "scripts/run-phase19.py")
p19 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p19)


def test_interaction_recovered():
    rng = np.random.default_rng(0)
    n = 4000
    C = {
        "prior": rng.integers(5, 50, n),
        "year": rng.integers(1995, 2006, n),
        "area": rng.integers(0, 3, n),
        "span": rng.normal(3, 1, n),
        "sim": rng.normal(0.3, 0.1, n),
    }
    size = np.full((3, 2030), 100.0)
    learn = np.ones(n, bool)
    X = p19.design(C, size, learn)
    assert abs(X[:, 3].mean()) < 1e-9 and abs(X[:, 4].std() - 1) < 1e-9
    y = rng.poisson(np.exp(0.5 - 0.3 * X[:, 3] + 0.2 * X[:, 4] + 0.25 * X[:, 5]))
    _, b = p19.poisson_coefs(X, y)
    assert abs(b[5] - 0.25) < 0.08 and abs(b[4] - 0.2) < 0.08


def test_verdict():
    assert p19.verdict(0.1, 0.3, "up", "none", "down") == "up"
    assert p19.verdict(-0.1, 0.3, "up", "none", "down") == "none"
    assert p19.verdict(-0.3, -0.1, "up", "none", "down") == "down"
