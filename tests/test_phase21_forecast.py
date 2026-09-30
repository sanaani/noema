"""Check Phase 21's fixed settings and the rule that picks the forward-test population."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


p21 = load("phase21", "run-phase21.py")


def test_forward_population():
    assert p21.forward_population(100) == "new works"
    assert p21.forward_population(99) == "all works"


def test_outcome_windows_end_by_2021():
    assert p21.CUTOFFS["train"] + p21.WINDOW <= p21.LAST_OUTCOME
    assert p21.CUTOFFS["forward"] + p21.WINDOW <= p21.LAST_OUTCOME
    assert p21.CUTOFFS["live"] + p21.WINDOW > p21.LAST_OUTCOME
    assert p21.CUTOFFS["train"] + p21.WINDOW > p21.CUTOFFS["forward"]  # the stated overlap
