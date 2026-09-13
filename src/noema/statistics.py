"""Inference for iid synthetic samples; proof-state inference needs clustered nulls."""

import numpy as np
from scipy.stats import norm

from noema.clouds import Cloud, canonical, matched_pair
from noema.metrics import mmd_from_kernel, pooled_kernel


def permutation_mmd(x: Cloud, y: Cloud, *, seed: int, permutations: int) -> dict[str, float]:
    if isinstance(permutations, bool) or not isinstance(permutations, int) or permutations < 1:
        raise ValueError("permutations must be a positive integer")
    a, b = matched_pair(canonical(x), canonical(y))
    kernel, bandwidth = pooled_kernel(a, b)
    n = len(a)
    observed = mmd_from_kernel(kernel, n)
    rng = np.random.default_rng(seed)
    exceedances = 0
    # Chunk to bound memory, with one label-independent bandwidth for the whole test.
    for start in range(0, permutations, 128):
        count = min(128, permutations - start)
        signs = np.ones((count, 2 * n))
        for row in signs:
            row[rng.permutation(2 * n)[:n]] = -1
        scores = np.einsum("bi,ij,bj->b", signs, kernel, signs, optimize=True) / n**2
        tolerance = 1e-12 * max(1.0, abs(observed))
        exceedances += int(np.count_nonzero(scores >= observed - tolerance))
    return {
        "statistic": observed,
        "p_value": (exceedances + 1) / (permutations + 1),
        "bandwidth": bandwidth,
    }


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    p = np.asarray(p_values, dtype=float)
    if p.ndim != 1 or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("p-values must be a finite vector in [0, 1]")
    if len(p) == 0:
        return []
    order = np.argsort(p, kind="stable")
    adjusted = p[order] * len(p) / np.arange(1, len(p) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1].clip(0, 1)
    result = np.empty_like(p)
    result[order] = adjusted
    return result.tolist()


def wilson_interval(successes: int, total: int, confidence: float = 0.95) -> list[float]:
    if total < 1 or not 0 <= successes <= total or not 0 < confidence < 1:
        raise ValueError("invalid binomial counts or confidence")
    z = float(norm.ppf((1 + confidence) / 2))
    fraction = successes / total
    denominator = 1 + z * z / total
    center = (fraction + z * z / (2 * total)) / denominator
    width = z * (fraction * (1 - fraction) / total + z * z / (4 * total**2)) ** 0.5
    return [max(0.0, center - width / denominator), min(1.0, center + width / denominator)]
