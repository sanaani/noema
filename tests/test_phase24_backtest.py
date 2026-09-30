"""Check Phase 24's percentile and verdict tables."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("scipy")

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phase24", ROOT / "scripts/run-phase24.py")
p24 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p24)


def test_percentile_counts_ties_half():
    s = np.array([1.0, 2.0, 2.0, 3.0])
    assert p24.percentile(s, 0) == pytest.approx(12.5)
    assert p24.percentile(s, 1) == pytest.approx(50.0)
    assert p24.percentile(s, 3) == pytest.approx(87.5)


def test_verdict():
    assert p24.verdict(99.5, 12) == "points at known breakthroughs"
    assert p24.verdict(95.0, 12) == "flags them, not sharply"
    assert p24.verdict(70.0, 12) == "weak"
    assert p24.verdict(30.0, 12) == "misses them"
    assert p24.verdict(99.9, 7) == "underpowered"


def test_sign_verdict():
    assert p24.sign_verdict(10, 2, 0.04) == "similarity lifts known breakthroughs"
    assert p24.sign_verdict(2, 10, 0.04) == "similarity lowers them"
    assert p24.sign_verdict(8, 4, 0.39) == "no clear effect"
