"""Check Phase 23's verdict table."""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("scipy")

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phase23", ROOT / "scripts/run-phase23.py")
p23 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p23)


def test_verdict():
    assert p23.verdict(None) == "underpowered"
    assert p23.verdict({"ci95": [0.01, 0.09], "difference": 0.05}).startswith(
        "similarity forecasts"
    )
    assert p23.verdict({"ci95": [0.001, 0.02], "difference": 0.01}) == "detectable, small"
    assert p23.verdict({"ci95": [-0.01, 0.02], "difference": 0.01}) == "no measurable help"
    assert p23.verdict({"ci95": [-0.05, -0.01], "difference": -0.03}) == "similarity hurts"
