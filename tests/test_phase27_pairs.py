"""Check Phase 27's training pairs and verdict tables."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("scipy")
pytest.importorskip("sklearn")

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phase27", ROOT / "scripts/run-phase27.py")
p27 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p27)


def toy():
    # papers: three citers up to 1999 (two of W0, one of W1), one 2002 arrival of W0 in area 2,
    # and a 2007 arrival that falls outside the window
    year = np.array([1999, 1999, 1999, 2002, 2007])
    area = np.array([0, 0, 0, 2, 2])
    cp = np.array([0, 1, 2, 3, 4])
    cw = np.array([0, 0, 1, 0, 0])
    C = SimpleNamespace(
        year=year, area=area, cp=cp, cw=cw, works=["W0", "W1"], areas=["a", "b", "c"]
    )
    b = SimpleNamespace(
        work=np.array([0, 1]),
        target=np.array([2, 2]),
        later=np.array([1, 0]),
        book=np.array([False, False]),
        home=np.array([0, 0]),
    )
    return C, b


def test_one_pair_from_one_jump():
    C, b = toy()
    pairs = p27.jump_pairs(C, b, 2000, 2005, np.random.default_rng(0))
    assert len(pairs) == 1
    q = pairs[0]
    assert q["work"] == "W0" and q["target"] == "c"
    assert q["anchor"] == 3  # the 2002 arrival, never the 2007 one
    assert q["positive"] in (0, 1)  # a citer of W0 up to the cutoff
    assert q["negative"] == 2  # a citer of the other work from the same home area


def test_textbooks_and_non_jumps_give_no_pairs():
    C, b = toy()
    b.book = np.array([True, False])
    assert p27.jump_pairs(C, b, 2000, 2005, np.random.default_rng(0)) == []


def test_verdicts():
    assert p27.h1_verdict(1, 5) == "training helps"
    assert p27.h1_verdict(-2, 5) == "no measurable difference"
    assert p27.h1_verdict(-9, -1) == "training hurts"
    assert p27.h2_verdict(1, 5) == "trained beats TF-IDF"
    assert p27.h2_verdict(-9, -1) == "trained is worse than TF-IDF"


def test_difference_without_noise():
    x = {"_met_a": np.array([3, 3, 3])}
    y = {"_met_a": np.array([1, 1, 1])}
    d = p27.difference(x, y, 3, np.random.default_rng(0), draws=100)
    assert d["difference"] == 6
    assert d["ci95"] == [6.0, 6.0]
