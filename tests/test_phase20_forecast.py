"""Check Phase 20's matrix span and co-citation against Phase 18's, and the tier rule."""

import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


p18 = load("phase18", "run-phase18.py")
p20 = load("phase20", "run-phase20.py")


def test_matches_phase18():
    sets = [{0}, {0, 1}, {1}, {2}, {1, 2}]
    used = np.zeros((len(sets), 3))
    for k, s in enumerate(sets):
        used[k, list(s)] = 1
    F = p20.cocitation_matrix(used)
    assert np.allclose(F, p18.cocitation(sets, 3))
    counts = np.array([[4.0, 0, 0], [2, 2, 0]])
    S = p20.span_matrix(counts, F)
    for w in range(2):
        for a in range(3):
            assert np.isclose(S[w, a], p18.span(counts[w], a, F))


def test_choose_tier():
    assert p20.choose_tier({0.01: 120, 0.05: 400, 0.10: 700}) == (0.01, False)
    assert p20.choose_tier({0.01: 40, 0.05: 150, 0.10: 300}) == (0.05, False)
    assert p20.choose_tier({0.01: 4, 0.05: 20, 0.10: 60}) == (0.10, True)
