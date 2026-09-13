"""Known distributions share a latent coordinate system and ambient embedding."""

import numpy as np

from noema.clouds import Cloud

SCENARIOS = {
    "same_gaussian": ("gaussian", "gaussian", "null"),
    "same_ring": ("ring", "ring", "null"),
    "partial_overlap": ("gaussian", "partial", "exploratory"),
    "separated": ("gaussian", "shifted", "alternative"),
    "ring_vs_disk": ("ring", "disk", "alternative"),
    "unimodal_vs_mixture": ("gaussian", "mixture", "alternative"),
    "branches_vs_ring": ("branches", "ring", "alternative"),
}


def latent_sample(shape: str, n: int, rng: np.random.Generator) -> Cloud:
    if shape in {"gaussian", "partial", "shifted"}:
        points = rng.normal(scale=0.5, size=(n, 2))
        points[:, 0] += {"gaussian": 0.0, "partial": 0.75, "shifted": 3.0}[shape]
        return points
    if shape == "mixture":
        points = rng.normal(scale=0.2, size=(n, 2))
        points[:, 0] += rng.choice([-1.0, 1.0], n)
        return points
    angles = rng.uniform(0, 2 * np.pi, n)
    if shape == "ring":
        radii = np.ones(n)
    elif shape == "disk":
        radii = np.sqrt(rng.uniform(size=n))
    elif shape == "branches":
        angles = rng.integers(0, 3, n) * (2 * np.pi / 3)
        radii = rng.uniform(size=n)
    else:
        raise ValueError(f"unknown shape: {shape}")
    return np.column_stack((radii * np.cos(angles), radii * np.sin(angles)))


def sample_pair(
    scenario: str, *, n: int, dimension: int, noise: float, seed: int
) -> tuple[Cloud, Cloud, Cloud]:
    """Return independent anchor, same-shape replicate, and comparison samples.

    Noise is standard deviation per ambient coordinate, so total noise grows with d.
    All three samples use a shared random isometric embedding, never per-cloud PCA.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")
    if n < 2 or dimension < 2 or not np.isfinite(noise) or noise < 0:
        raise ValueError("require n >= 2, dimension >= 2 and finite noise >= 0")
    left, right, _ = SCENARIOS[scenario]
    children = np.random.SeedSequence(seed).spawn(4)
    basis_rng = np.random.default_rng(children[0])
    basis, _ = np.linalg.qr(basis_rng.normal(size=(dimension, 2)))
    result = []
    for shape, child in zip((left, left, right), children[1:], strict=True):
        rng = np.random.default_rng(child)
        points = latent_sample(shape, n, rng) @ basis.T
        result.append(points + rng.normal(scale=noise, size=(n, dimension)))
    return tuple(result)
