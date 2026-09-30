"""Check the hit-labelling rule of the Phase 22 follow-up."""

import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hits", ROOT / "scripts/phase22-hits.py")
hits = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hits)


def test_nearest_areas_skip_self():
    F = np.array([[1.0, 0.2, 0.9, 0.5], [0.3, 1, 0.1, 0.2], [0.4, 0.4, 1, 0.1], [0, 0, 0, 1]])
    assert hits.nearest_areas(F, 0, 2) == [2, 3]
    assert hits.nearest_areas(F, 2, 2) == [0, 1]


def test_label_order():
    assert hits.label(True, True) == "knocking"
    assert hits.label(False, True) == "next door"
    assert hits.label(False, False) == "surprising"
