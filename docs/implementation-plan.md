# Implementation plan

## Research contract

The supplied research plan is the project specification. Preserve its original bytes, including formatting defects; amend interpretations here. Its literature and novelty claims are research inputs, not independently verified findings.

The central object is an unordered empirical distribution of individual state embeddings. Geometry code receives only finite numeric matrices. Proof provenance belongs in separate audit records, never in encoder input. Keep multiplicities explicit: an empirical distribution and a set of unique states are different experimental objects.

All compared clouds have equal sample sizes. Samples use fixed seeds and sampling without replacement. Proof splits precede state sampling. No theorem labels, destinations, neighboring states, proof order, or graph edges may reach a state encoder. Do not infer a manifold or topology from a visualization.

## Checkpoint 1 — Repository and design

- Create `sanaani/noema` as a private personal repository.
- Initial commit contains the unmodified research plan and this implementation plan.
- Use Python 3.12+, NumPy, and SciPy for a small CPU-based research package.
- Keep source, experiment configurations, tests, and compact reference results in Git; ignore local environments and bulk data.

Acceptance: remote exists, source document checksum matches, and the design is committed before implementation begins.

## Checkpoint 2 — Executable Phase 0 foundation (first implementation)

Build a package and CLI with:

1. Strict point-cloud validation and reproducible, order-independent size matching.
2. Synthetic Gaussian, mixture, ring, disk, and branching distributions. Compare independent samples of the same shape, partial overlap, separated populations, and shapes with matched population centroids. Embed shared latent coordinates through a common orthonormal map; add configurable ambient Gaussian noise.
3. Squared Gaussian-kernel MMD (biased, nonnegative estimator), multivariate energy statistic, sliced Wasserstein-1, a symmetric radius-coverage diagnostic, and centroid distance. Label sliced transport as an approximation, and coverage as a diagnostic rather than a metric. Preserve absolute scale; do not center each cloud independently.
4. A pooled, label-independent median bandwidth and permutation test for the primary MMD statistic. Monte Carlo p-values use `(exceedances + 1) / (permutations + 1)`. Benjamini–Hochberg correction covers all comparisons in a run, with the family recorded. Diagnostic metrics do not inherit the primary test's p-values.
5. Repeat independent trials across size, dimension, and noise settings. Report null rejection rates, alternative detection rates, Wilson confidence intervals, raw metrics, adjusted p-values, and same-versus-different distance ranking. Include matched-centroid cases to expose centroid limitations.
6. Config hashes, dependency versions, source revision/dirty state, seeds, and machine-readable JSON plus a readable Markdown report. Fail on invalid input and refuse accidental report overwrite.
7. Meaningful numerical, invariance, statistical, reproducibility, and CLI tests; automated CI.

Acceptance: tests and lint pass; the documented command reproduces a committed small reference experiment; output contains honest uncertainty and an explicit gate decision. A small smoke experiment can only validate execution, never qualify the measurement system.

## Checkpoint 3 — Qualify and freeze Phase 0

The initial metrics are candidates. Before running a qualification study, commit the configuration and the following proposed gates: at least 100 independent trials per scenario and stratum; at least 999 permutations; null rejection Wilson upper bound at most 0.10 at alpha 0.05; alternative detection Wilson lower bound at least 0.80 for separated and matched-centroid alternatives in every designated target stratum. Partial overlap is exploratory. Use raw primary-test rejection rates to measure calibration/power; report family-adjusted discoveries separately. Qualification reports require all target strata to pass. A failure means redesign or explicitly narrow the operating regime, documenting the failure before a new version.

Start with a CPU pilot; target realistic state counts and dimensions only after measuring resource needs. Review noise scaling and add controlled sampler shifts, anisotropy, and distribution-preserving transformations. Compare candidates on calibration data, then use a separately seeded held-out qualification run. Add persistent homology only if it resolves a demonstrated measurement gap; holes/branches alone do not require a topology package.

Acceptance: a versioned `protocol` artifact freezes metrics, bandwidth policy, sampling, thresholds, multiple-testing families, and significance procedures before mathematical results are inspected. The first implementation must not claim this gate has passed.

## Checkpoint 4 — Verified multi-proof corpus (Phase 1)

Pin a Lean toolchain and library revision. Define theorem, proof, state, and verification records with stable IDs and content hashes; record prover version, seed, resource budget, premises, tactics, and proof-term identity outside encoder inputs. Use two substantially different proof-search systems from the beginning. Select specific systems after a bounded compatibility and resource assessment.

Accept proofs only after Lean verification with no `sorry` or unapproved axioms. Store verifier evidence. Freeze non-geometric diversity criteria before inspecting embeddings: normalized proof identity and normalized state-sequence duplicates first, followed by premise/tactic/tree diversity. Prevent duplicates crossing splits; repeat with alternative thresholds. Exclude or explicitly ablate theorem-identifying initial/terminal states and common boilerplate. Report theorem coverage, unsuccessful searches, and proof/state counts.

Acceptance: a small verified corpus from two systems, reproducible extraction, deduplication and split audits, and a documented sampling population. Do not call sampled states all possible states of a theorem.

## Checkpoint 5 — Encoders and reproducibility (Phases 2–3)

Define a state-content-only encoder interface and an external provenance table. Begin with a syntax baseline, then select a semantic encoder with a pinned model/training manifest and leakage audit. Separate representation training, calibration, and theorem evaluation data. Build clouds only after disjoint proof splits, matching sizes without replacement and balancing proof contributions. Run within-prover and cross-prover experiments with same-file, definition, statement, hypothesis, and domain controls.

Acceptance: H1/H2 reports with uncertainty at the theorem/proof sampling unit, negative controls, permutation exchangeability justified at that unit, and explicit kill-criterion outcomes. The synthetic iid point permutation test must not be reused blindly for correlated proof states.

## Checkpoint 6 — Added information and intersections (Phases 4–5)

Compare full clouds against statement embeddings, premise/definition overlap, domain labels, tactic histograms, single-proof clouds, centroids, and trajectories where available. Quantify graph fidelity separately. Replicate with a materially different encoder. Search cross-theorem overlaps under a precommitted null and multiple-comparison family. Inspect only statistically surviving pairs with a blinded mathematical review protocol and chance baseline.

Acceptance: incremental signal beyond baselines, encoder/prover robustness, auditable overlap candidates and interpretations, or a documented negative result. Proof navigation remains a separate future project.

## Scope and risks

Execution continues through the research plan; checkpoints are progress records, not stopping points. Checkpoints 1–2 established the foundation. Continue calibration, held-out qualification, corpus construction, representations, controlled experiments, and interpretation subject to the scientific gates. A failed gate calls for documented diagnosis and redesign or a justified negative conclusion, not silently advancing to an invalid experiment.

The local machine has four CPU threads, about 8 GiB RAM, and initially 12 GiB free disk. Use bounded CPU experiments and pinned lightweight tools first; do not launch paid compute without authorization. Defaults are development smoke settings. Pairwise metrics need O(n²) memory; projections and permutations have explicit budgets. Synthetic success would validate measurement behavior only, not H1–H4. No thresholds are tuned after observing results and presented as preregistered.
