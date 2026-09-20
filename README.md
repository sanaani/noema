# Noema

Exploring whether theorem embeddings and the distributions of States across their proofs reveal useful mathematical relationships.

The starting point is the [original research plan](docs/latent_geometry_mathematical_theorems_research_plan.md), preserved byte for byte. The [current specification](docs/current-state-object-spec.md) governs this investigation. The original [implementation plan](docs/implementation-plan.md) is historical and superseded where it conflicts with that specification.

**Immediate priority: encoder invariance, before further corpus acquisition or
mathematical case studies.** The [Lean-certified presentation audit](results/encoder-invariance-v1/README.md)
tests α-renaming, pretty-print changes and definitionally equal restatements,
including their effect on cumulative mass with both center and States transformed.
The fixed encoder has no validated claim to measure mathematical relatedness.
The [checked State encoding contract](results/state-consistency-v1/README.md)
now supplies typed capture and a frozen Lean-certified equivalence registry.
Accepted equivalent States receive identical vectors; unknown States and
unvalidated encoders are rejected. This is scoped consistency, not validated
mathematical relatedness or a migration of the old display-only corpus.
The follow-up [semantic encoder evaluation](results/semantic-encoder-evaluation-v1/README.md)
finds no evidence for the four prespecified cross-area connections in a fixed
theorem-center benchmark, so the distance-usefulness claim remains unvalidated.
The [alternative-encoder comparison](results/encoder-comparison-v1/README.md)
tests five replacements, a fixed Qwen instruction, canonical Lean inputs and
explicit proposition-distinction controls. The representation intervention is
reported separately from the neural models' raw-input behavior.
None of the alternatives passes on raw displays. Canonical inputs pass the
finite screen while retaining 12 verified proposition distinctions, including
with a structural control; mathematical relatedness is still unvalidated.

**For the longer-term research direction and an LLM handoff, read
[Demonstrating usefulness of Theorem Density Objects](docs/theorem-density-usefulness.md).**
The object is centered on the theorem's initial State and retains all acquired
nonempty proof-State occurrences, their rays, and cumulative mass. That proposal
explains how mass could help inspect mathematical connections and existing proof
routes, what it cannot establish, and the recommended next investigation.
The [historical-connections pilot](results/historical-connections-v1/README.md)
measured initial-State centers; cumulative-mass usefulness has not yet been tested.

The [active dataset](results/state-objects-admitted-v1/README.md) now contains
**102 theorem groups, 813 proof records and 16,592 separate state-vector rows**.
Open the [current boundary explorer](results/theorem-boundaries-v2/explore.html):
it follows every projected location with an inward-bending area objective,
excludes generic “no goals” displays from geometry, and shows shared x–y axes,
zero, scale and individually selectable multi-object overlays. Every original record remains accessible.
The [earlier convex explorer](results/state-objects-admitted-v1/explore.html)
is preserved as an archive.

The [first form analysis](docs/theorem-forms-v1.md) constructed and measured all
102 hulls. Its [interactive atlas](results/theorem-forms-v1/explore.html) shows
every object and every state, with common or local display axes. All objects
touch at the empty-goal encoding; substantial formatting sensitivity means these
forms cannot yet be interpreted as the shapes of mathematical ideas.

An enforced admission rule excludes six theorem groups whose assumptions were
proved contradictory in Lean, and holds 148 groups with unresolved source identity
or inventoried proof/trace gaps. All states of every admitted theorem remain;
there is no state deduplication or proof/state cap. The full 26,820-row
[historical archive](results/state-object-records-v1/README.md) remains available
for recovery and repair, but is no longer the active analysis set.

The [remediation report](docs/theorem-admission-remediation-v1.md) records the
exclusions, the contradiction screen of all 128 Workbook groups, the admission
checks and what is still open. The earlier [assumption audit](docs/assumption-audit-v1.md)
identified defects; labelling them was not sufficient remediation.

The current focus is the **Theorem Density Object** and its mathematical usefulness.
The [current specification](docs/current-state-object-spec.md) defines the scope;
the [convex-hull literature review](docs/state-object-convex-hull-literature-review.md)
documents the earlier boundary investigation. Proof admission does not establish complete internal state capture,
all-known-proof coverage or mathematical faithfulness of the encoder. Those remain
open work, not problems declared fixed by documentation. No model was trained.

The completed strategy-transfer continuation addressed a task-design failure in the earlier study.
An [adversarial analysis](docs/adversarial-centroid-results-v1.md) verifies that
invariant premise text is sufficient for the old centroid's perfect score;
all 12 contexts are also constructively equivalent in Lean. That ceiling was
not an informative test of State object added information.

The first strategy-transfer screen failed its task and budget gates. A fresh
[structurally matched experiment](docs/strategy-transfer-protocol-v2.md) now passes
both: all nine baseline upper accuracy bounds are below 71.2%, and simulated
power qualifies a 512-triplet confirmation budget. Premise overlap and both
source and target statement-structure distances are matched exactly by design.

The eight-leaf development State object initially exceeded its centroid, but failed the
original ten-point continuation rule. The user removed that arbitrary margin,
and a fresh 512-triplet, nine-leaf study was acquired with exact matching and
no minimum-gain requirement. All 6,144 sampled proofs and 30,720 intermediate
states passed Lean verification.

The **[completed 512-triplet study](docs/gpu-execution-results-v1.md)** has baseline
headroom, but shows no advantage for its sampled-state energy-distance predictor: its accuracy
is **53.91%**, versus **54.49%** for its centroid (paired gain **-0.59 points**,
marginal bootstrap 95% interval **[-2.54, +1.37]**). None of the three sampled-state arms
exceeds its corresponding centroid. Tactic histograms and complete-program
comparisons score 82.03% and 92.19%; the latter sees more proof information.

All 8,500 ReProver inputs were completed on the GPU using the same theorem set,
model weights, proof sampling and analysis rules. The user stopped the remaining
CPU encoding; its checkpoints and execution history are preserved in the
[reproducibility notes](docs/strategy-transfer-confirmation-results-v1.md).
No duplicate CPU result is needed for the completed study. The temporary GPU
instance and its temporary AWS resources have been removed.

The [GPU archive](results/gpu-execution-check-v1/README.md) reproduces every score,
paired test, interval and supplemental control without a GPU or model download.
The earlier 99-test suite, two scheduler tests and three new device tests pass.
The [development result](docs/strategy-transfer-results-v2.md) remains intact;
the [first screen](docs/strategy-transfer-results-v1.md) stays closed with State objects
unscored. No old-corpus pair mining, Phase 5, or full mathlib acquisition occurred.
The broader conjecture remains unresolved.

The [canonical-v3 report](docs/revised-plan-results.md), its
[comparison table](results/canonical-v3/report.md),
[power study](docs/cluster-power-results.md), and
[reproduction guide](docs/reproduction-v3.md) remain historical evidence. That
study verified 1,864 proofs and 60,501 states with exact length/depth matching;
its measurements are preserved and its saturated-task interpretation corrected.

The first study's 3,072 verified proofs and unmatched outcomes remain intact in
the [historical report](docs/final-research-status.md). The original
[checkpoint 2 report](docs/checkpoint-2-results.md) remains a foundation record.

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

The smoke configuration runs 336 comparisons across seven scenarios, two sample sizes, and two dimensions. It checks independent same-shape samples, partial overlap, separated populations, multimodality, holes, and branches. Each comparison uses equal-size State objects. A shared isometric map embeds the two latent dimensions into the ambient space; noise is added per ambient coordinate. This is a controlled low-intrinsic-dimensional benchmark, not a model of all proof-state distributions.

For a larger exploratory sweep across dimensions and noise levels:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 noema synthetic \
  --config configs/pilot.json --output outputs/my-pilot
```

The pilot makes 2,520 comparisons and costs substantially more than the smoke run. Both are development runs and deliberately report `not_qualified`. The separately seeded v2 qualification passed only the restricted low-noise regime; see the [qualification review](docs/phase-0-review.md). The noisy pilot and failed v1 qualification remain part of the evidence.

## Measurements

| Measurement | Purpose |
|---|---|
| Gaussian MMD² | Original primary distribution comparison; revised power candidate |
| Energy V-statistic | Qualified primary metric for the revised matched experiment |
| Sliced Wasserstein-1 | Average exact transport along random 1D projections |
| Symmetric radius coverage | Local proximity diagnostic; larger means more coverage |
| Centroid distance | Baseline exposing information lost by collapsing a State object to its mean |

MMD uses the nonnegative biased estimator and a bandwidth computed without labels from the pooled points. The original study tests MMD; the revised proof-cluster calibration tests MMD and energy, and its frozen formal continuation selects energy. P-values include the Monte Carlo correction and undergo Benjamini–Hochberg adjustment across each complete primary family. The new synthetic calibration permutes whole proof blocks. Formal comparisons use whole-theorem label permutations and theorem-cluster uncertainty because states within one proof are correlated.

The implementation of projected transport uses sorted, equal-weight samples, consistent with the [SciPy definition of 1D Wasserstein-1](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html). Explicit random generators follow [NumPy's Generator interface](https://numpy.org/doc/stable/reference/random/generator.html).

## Develop

```bash
ruff check .
ruff format --check .
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m pytest
```

Tests cover analytic metric values, invariance to input order and shared translations, isometric embeddings, degeneracy, exact/permutation reference calculations, null calibration, detection power, multiple-testing adjustment, reproducibility, invalid input, and CLI overwrite protection. GitHub Actions runs these checks and the smoke experiment.

Source lives in `src/noema/`; configurations in `configs/`; scientific and engineering decisions in `docs/`. Model weights and transient run outputs stay outside Git; selected numerical evidence is archived. The numerical API accepts finite point matrices and does not accept theorem identity, proof order, or graph edges. Proof provenance remains in external audit records. Syntax, exact truth-table, and pinned pretrained text encoders consume only normalized state content. The formal run also includes proof-sampling sensitivity, stricter diversity policies, baselines and graph-fidelity diagnostics.

## Reproduce the formal study

After installing the additional encoder dependencies and bootstrapping the pinned
tools as described in the [reproduction guide](docs/reproduction.md):

```bash
noema corpus --output outputs/my-corpus --theorems 24 --proofs 64
noema audit --corpus outputs/my-corpus/manifest.json --output outputs/my-audit
# Freeze/review the actual sampling assignments before computing embeddings.
noema formal --corpus outputs/my-corpus/manifest.json \
  --freeze outputs/my-audit/splits.json --output outputs/my-formal
```

Corpus and formal analysis support `--resume` for incomplete checkpoints and
refuse to overwrite completed results. The checksummed corpus and all three
embedding caches are committed under `results/corpus-v1/` and `results/formal-v1/`.
The reproduction guide also shows how to use these archives without recollecting
proofs or recomputing embeddings.

The completed added-information test supplies no positive evidence for opening
cross-theorem overlap mining or making mathematical-discovery claims. Cross-domain
H3/H4 remain untested in this single-domain population.
