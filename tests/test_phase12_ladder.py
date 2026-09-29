"""Check that Phase 12 puts each cell on the lowest rung it meets."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("scipy")

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phase12", ROOT / "scripts/run-phase12.py")
p12 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p12)


def paper(pid, area, refs=(), authors=(), cats=(), year=2005):
    return {
        "id": pid,
        "year": year,
        "area": area,
        "categories": [area, *cats],
        "openalex": ["W" + pid],
        "refs": list(refs),
        "authors": list(authors),
    }


def test_ladder_rungs():
    P = [
        paper("0", "math.AG", refs=["T"], authors=["x"], cats=["math.NT"]),  # uses T
        paper("1", "math.CO", refs=["W0"]),  # cites a T-citer: second-hand
        paper("2", "math.DS", authors=["x"]),  # x also wrote a T-citer: shared author
        paper("3", "math.PR"),
        paper("4", "math.GT"),
        paper("5", "math.GT", refs=["T"], year=2012),  # after history: ignored
    ]
    areas = ["math.AG", "math.CO", "math.DS", "math.GT", "math.NT", "math.PR"]
    cells = ["math.NT", "math.CO", "math.DS", "math.PR", "math.GT"]
    flow = [0.3, 0.1, 0.2, 0.9, 0.05]  # 75th percentile 0.3: NT and PR reach rung 4
    X = np.zeros((len(cells), len(p12.p11.BASE) + 1))
    X[:, p12.p11.BASE.index("flow")] = flow
    w = {
        "areas": areas,
        "tools": ["T"],
        "tool_row": np.zeros(len(cells), int),
        "area_col": np.array([areas.index(a) for a in cells]),
        "X": X,
        "xlist": np.array([1, 0, 0, 0, 0]),
    }
    rung, info = p12.ladder(P, 2010, w)
    assert rung.tolist() == [1, 3, 2, 4, 5]
    assert info["history_papers"] == 5 and info["authors"] == 1
