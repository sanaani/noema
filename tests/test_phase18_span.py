"""Check Phase 18's co-citation table, span and arrival cells on toy data."""

import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phase18", ROOT / "scripts/run-phase18.py")
p18 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p18)


def test_cocitation():
    # works used by {0}, {0, 1}, {1}, {2}
    F = p18.cocitation([{0}, {0, 1}, {1}, {2}], 3)
    assert F[0, 0] == F[1, 1] == F[2, 2] == 1
    assert F[1, 0] == 0.5  # of area 0's two works, area 1 also uses one
    assert F[2, 0] == 0


def test_span_discounts_generic_works():
    F = p18.cocitation([{0}, {0, 1}, {1}, {2}, {1, 2}], 3)
    far = p18.span(np.array([4.0, 0, 0]), 2, F)  # used only in area 0; area 2 never shares
    near = p18.span(np.array([0, 4.0, 0]), 2, F)
    spread = p18.span(np.array([2.0, 2.0, 0]), 2, F)
    assert far > spread > near


def test_cells_of_work():
    yrs = np.array([2000, 2000, 2001, 2001, 2002, 2003, 2003, 2004, 2005, 2006])
    ars = np.array([0, 0, 0, 1, 0, 0, 2, 2, 2, 1])
    cells = {
        a: (y, pos, list(arr), list(later))
        for a, y, pos, arr, later in p18.cells_of_work(yrs, ars, 5)
    }
    assert set(cells) == {2}  # area 1 arrives with 2 prior citers; area 0 has none
    y, pos, arr, later = cells[2]
    assert (y, pos, arr, later) == (2003, 5, [6], [1, 2])
