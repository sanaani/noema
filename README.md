# Noema

Exploring whether the unordered states encountered across alternative proofs form reproducible theorem geometries.

The starting point is the [original research plan](docs/latent_geometry_mathematical_theorems_research_plan.md), preserved byte for byte. The [implementation plan](docs/implementation-plan.md) defines the engineering checkpoints and scientific gates.

The first implementation provides the Phase 0 synthetic measurement pipeline. No formal proofs have been collected and no mathematical hypothesis has been confirmed.

See the [checkpoint results](docs/checkpoint-2-results.md) and [reference experiment](results/reference-smoke/report.md) for the completed implementation and its current limits.

## Run it

Requires Python 3.12+; the reference environment and CI use Python 3.12.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 noema synthetic \
  --config configs/smoke.json --output outputs/my-smoke
```

Each run creates `report.json` with all trial statistics and provenance, and `report.md` with readable tables. The output directory must be new. The seed controls every sample, projection, and permutation; timestamps and platform metadata naturally differ across reruns. Dependency pins make the reference environment reproducible. BLAS thread limits avoid overhead on these small matrix operations.

The smoke configuration runs 336 comparisons across seven scenarios, two sample sizes, and two dimensions. It checks independent same-shape samples, partial overlap, separated populations, multimodality, holes, and branches. Each comparison uses equal-size clouds. A shared isometric map embeds the two latent dimensions into the ambient space; noise is added per ambient coordinate. This is a controlled low-intrinsic-dimensional benchmark, not a model of all proof-state distributions.

For a larger exploratory sweep across dimensions and noise levels:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 noema synthetic \
  --config configs/pilot.json --output outputs/my-pilot
```

The pilot makes 2,520 comparisons and costs substantially more than the smoke run. Both are development runs and deliberately report `not_qualified`. The [implementation plan](docs/implementation-plan.md) specifies the qualification thresholds and later corpus/encoder work.

## Measurements

| Measurement | Purpose |
|---|---|
| Gaussian MMD² | Primary distribution comparison and pooled-label permutation test |
| Energy V-statistic | Multivariate distance-based comparison |
| Sliced Wasserstein-1 | Average exact transport along random 1D projections |
| Symmetric radius coverage | Local proximity diagnostic; larger means more coverage |
| Centroid distance | Baseline exposing information lost by collapsing a cloud to its mean |

MMD uses the nonnegative biased estimator and a bandwidth computed without labels from the pooled points. Only MMD receives a significance test. P-values include the Monte Carlo correction and undergo Benjamini–Hochberg adjustment across every primary comparison in a run. Synthetic trials use independent random streams. Real proof states require cluster-aware inference because states within one proof are correlated.

The implementation of projected transport uses sorted, equal-weight samples, consistent with the [SciPy definition of 1D Wasserstein-1](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html). Explicit random generators follow [NumPy's Generator interface](https://numpy.org/doc/stable/reference/random/generator.html).

## Develop

```bash
ruff check .
ruff format --check .
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m pytest
```

Tests cover analytic metric values, invariance to input order and shared translations, isometric embeddings, degeneracy, exact/permutation reference calculations, null calibration, detection power, multiple-testing adjustment, reproducibility, invalid input, and CLI overwrite protection. GitHub Actions runs these checks and the smoke experiment.

Source lives in `src/noema/`; configurations in `configs/`; scientific and engineering decisions in `docs/`. Bulk data and local run outputs stay outside Git. The numerical API accepts finite point matrices and does not accept theorem identity, proof order, or graph edges. Future proof provenance and encoder integration remain separate checkpoints.
