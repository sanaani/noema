"""Distribution statistics. Every comparison requires matched cloud sizes."""

import numpy as np
from scipy.spatial.distance import cdist, pdist, squareform

from noema.clouds import Cloud, canonical, matched_pair


def pooled_kernel(x: Cloud, y: Cloud) -> tuple[Cloud, float]:
    a, b = matched_pair(x, y)
    distances = pdist(np.vstack((a, b)), metric="sqeuclidean")
    positive = distances[distances > 0]
    bandwidth_sq = float(np.median(positive)) if len(positive) else 1.0
    return np.exp(-squareform(distances) / (2 * bandwidth_sq)), bandwidth_sq**0.5


def mmd_from_kernel(kernel: Cloud, n: int) -> float:
    """Biased MMD²: includes self-pairs; permutations use the same estimator."""
    score = kernel[:n, :n].mean() + kernel[n:, n:].mean() - 2 * kernel[:n, n:].mean()
    return max(0.0, float(score))


def mmd_squared(x: Cloud, y: Cloud) -> float:
    a, b = matched_pair(x, y)
    kernel, _ = pooled_kernel(a, b)
    return mmd_from_kernel(kernel, len(a))


def energy(x: Cloud, y: Cloud) -> float:
    """V-statistic 2 E||X-Y|| - E||X-X'|| - E||Y-Y'|| (no square root)."""
    a, b = matched_pair(x, y)
    value = 2 * cdist(a, b).mean() - cdist(a, a).mean() - cdist(b, b).mean()
    return max(0.0, float(value))


def sliced_wasserstein(x: Cloud, y: Cloud, *, seed: int = 0, projections: int = 64) -> float:
    """Mean exact 1D W1 over fixed random unit directions; not full ambient OT."""
    a, b = matched_pair(x, y)
    if isinstance(projections, bool) or not isinstance(projections, int) or projections < 1:
        raise ValueError("projections must be a positive integer")
    directions = np.random.default_rng(seed).normal(size=(a.shape[1], projections))
    directions /= np.linalg.norm(directions, axis=0)
    return float(np.abs(np.sort(a @ directions, axis=0) - np.sort(b @ directions, axis=0)).mean())


def radius_coverage(x: Cloud, y: Cloud, *, radius: float) -> float:
    """Mean fraction of each cloud within radius of the other (higher = overlap)."""
    a, b = matched_pair(x, y)
    if not np.isfinite(radius) or radius <= 0:
        raise ValueError("radius must be finite and positive")
    distances = cdist(a, b)
    return float(
        ((distances.min(axis=0) <= radius).mean() + (distances.min(axis=1) <= radius).mean()) / 2
    )


def measure(x: Cloud, y: Cloud, *, projection_seed: int, projections: int) -> dict[str, float]:
    a, b = matched_pair(canonical(x), canonical(y))
    _, bandwidth = pooled_kernel(a, b)
    return {
        "mmd_squared": mmd_squared(a, b),
        "energy_statistic": energy(a, b),
        "sliced_wasserstein_1": sliced_wasserstein(
            a, b, seed=projection_seed, projections=projections
        ),
        "radius_coverage": radius_coverage(a, b, radius=bandwidth / 2),
        "coverage_radius": bandwidth / 2,
        "centroid_distance": float(np.linalg.norm(a.mean(axis=0) - b.mean(axis=0))),
        "kernel_bandwidth": bandwidth,
    }
