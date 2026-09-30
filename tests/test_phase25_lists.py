"""Check Phase 25's per-area selection and lift."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("scipy")

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phase25", ROOT / "scripts/run-phase25.py")
p25 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p25)


def test_top_per_area_keeps_best_k_per_area():
    score = np.array([0.1, 0.9, 0.5, 0.7, 0.2, 0.8])
    target = np.array([0, 0, 0, 1, 1, 1])
    top = p25.top_per_area(score, target, 2, k=2)
    assert list(top[0]) == [1, 2]
    assert list(top[1]) == [5, 3]


def test_lift_is_share_over_base_rate():
    hit = np.array([True, False, False, False, True, False])
    assert p25.lift(hit, np.array([0, 4])) == pytest.approx(3.0)
    assert p25.lift(hit, np.array([1, 2])) == 0.0
    assert p25.lift(np.zeros(3, bool), np.array([0])) is None
