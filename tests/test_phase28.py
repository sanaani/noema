"""Check Phase 28's verdict table and its seeded pair draw."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(stem: str, path: str):
    spec = importlib.util.spec_from_file_location(stem, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_h1_verdict_rows_in_order():
    a28 = _load("a28", "scripts/analyze-phase28.py")
    assert a28.h1_verdict(0.062, 0.042, 0.080) == "far-pair training helps"
    assert a28.h1_verdict(0.020, 0.005, 0.035) == "real but small gain"
    assert a28.h1_verdict(0.000, -0.010, 0.020) == "no useful gain"
    assert a28.h1_verdict(0.010, -0.010, 0.040) == "inconclusive"
    # the threshold is inclusive and needs the interval above zero
    assert a28.h1_verdict(0.030, 0.001, 0.06) == "far-pair training helps"
    assert a28.h1_verdict(0.050, -0.001, 0.10) == "inconclusive"


def test_pair_key_is_seeded_and_stable():
    p28 = _load("p28", "scripts/phase28-pairs.py")
    assert p28.key("Lemma.x") == p28.key("Lemma.x")
    assert p28.key("Lemma.x") != p28.key("Lemma.y")
    assert len(p28.key("Lemma.x")) == 64
