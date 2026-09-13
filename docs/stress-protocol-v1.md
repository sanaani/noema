# Supplementary measurement stress audit v1

Run `configs/stress-v1.json` without changing the qualified metric implementation.
This exploratory supplement addresses the implementation plan's anisotropy,
sampler-shift, and distribution-preserving transformation checks. It does not
extend or replace the qualified operating regime and cannot qualify a learned
encoder. There are 100 independent trials per scenario, 999 permutations, 128
points, dimension 64, and ambient coordinate noise 0.02.

Scenarios are: equal anisotropic Gaussian distributions (latent scales 4 and
0.25); those distributions with a shift of 1 along the narrow coordinate;
independent isotropic Gaussians with a separate orthogonal rotation applied to
one latent sample; and two mixtures with identical component supports but
sampling weights 0.5 versus 0.85 (centers ±1.5 on the first latent coordinate,
component standard deviation 0.25). The first and third are nulls, the others
are alternatives. Sampler-weight sensitivity is expected: empirical-distribution
geometry represents occurrence frequencies, not merely a set of possible states.

Use all frozen diagnostics and MMD significance procedures. One BH family covers
all 400 comparisons; report raw rejection Wilson intervals separately. The first
trial of each scenario also measures invariance under a shared ambient rotation
and translation. MMD, energy, centroid distance, and radius coverage should be
unchanged up to floating-point tolerance. Finite-projection sliced Wasserstein
need not be exactly rotation invariant when the projection seed is held fixed;
retain its delta as an approximation diagnostic. No topology package is added
because this audit has not demonstrated a gap requiring topological summaries.
