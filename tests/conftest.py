"""Shared helpers for the archive-reproduction tests.

`analyze_saved`/`measure` recompute an archived result from its committed
vectors. Comparing the recomputed structure to the stored JSON with `==` asks
for bit-identical float64, which is not what reproduction means: a BLAS reduction
orders its partial sums by CPU and vector width, so the last digit moves between
machines. The dev host and GitHub's runners disagree by one ULP on values like
0.8622231943351463 vs ...64, and every archive test fails in CI while passing
locally. Compare numerically instead, at a tolerance far tighter than any effect
these experiments measure.
"""

import math

import pytest

# 1e-12 relative is ~4 orders of magnitude below the 1e-6 numerical-identity
# tolerance the invariance protocol fixes, so this cannot mask a real change.
REPRODUCTION_RTOL = 1e-12


def assert_reproduces(measured, archived, path="root"):
    """Assert `measured` matches `archived`, comparing floats to REPRODUCTION_RTOL."""
    if isinstance(archived, dict):
        assert isinstance(measured, dict), path
        assert measured.keys() == archived.keys(), path
        for key in archived:
            assert_reproduces(measured[key], archived[key], f"{path}.{key}")
    elif isinstance(archived, list):
        assert isinstance(measured, list), path
        assert len(measured) == len(archived), path
        for i, item in enumerate(archived):
            assert_reproduces(measured[i], item, f"{path}[{i}]")
    elif isinstance(archived, float) and not isinstance(measured, bool):
        assert not math.isnan(measured), path
        assert measured == pytest.approx(archived, rel=REPRODUCTION_RTOL, abs=1e-15), path
    else:
        assert measured == archived, path
