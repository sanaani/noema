"""The measurement boundary accepts numeric state content, never proof metadata."""

import numpy as np
from numpy.typing import ArrayLike, NDArray

Cloud = NDArray[np.float64]


def cloud(values: ArrayLike) -> Cloud:
    result = np.asarray(values, dtype=np.float64)
    if result.ndim != 2 or result.shape[0] < 2 or result.shape[1] < 1:
        raise ValueError("a cloud must have shape (n >= 2, d >= 1)")
    if not np.isfinite(result).all():
        raise ValueError("clouds must contain only finite values")
    return result


def canonical(values: ArrayLike) -> Cloud:
    """Canonical row order makes seeded sampling invariant to input row order."""
    result = cloud(values)
    return result[np.lexsort(result.T[::-1])]


def matched_pair(x: ArrayLike, y: ArrayLike) -> tuple[Cloud, Cloud]:
    a, b = cloud(x), cloud(y)
    if a.shape != b.shape:
        raise ValueError("clouds must have equal sample counts and dimensions; match sizes first")
    return a, b


def match_sizes(
    x: ArrayLike, y: ArrayLike, *, seed: int, size: int | None = None
) -> tuple[Cloud, Cloud]:
    a, b = canonical(x), canonical(y)
    if a.shape[1] != b.shape[1]:
        raise ValueError("cloud dimensions must agree")
    n = min(len(a), len(b)) if size is None else size
    if isinstance(n, bool) or not isinstance(n, int) or not 2 <= n <= min(len(a), len(b)):
        raise ValueError("size must be an integer between 2 and the smaller cloud size")
    rng = np.random.default_rng(seed)
    return canonical(a[rng.choice(len(a), n, replace=False)]), canonical(
        b[rng.choice(len(b), n, replace=False)]
    )
