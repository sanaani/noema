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

## First-study completion record — 2026-09-13

Historical record: the subsequently supplied [revised plan](research-plan-v2.md)
supersedes the whole-project completion declaration below. See the
[continuation protocol](continuation-protocol-v2.md) for its additional requirements.

The recovered execution is complete through the plan's scientific stopping rules.
Checkpoints 1–4 are implemented and evidenced for the explicitly bounded study.
Checkpoint 5's controlled analysis ran and failed its frozen feasibility gate.
Checkpoint 6's baseline comparisons, sensitivity analyses and operational graph
fidelity ran; the resulting negative evidence closes the conditional intersection
phase without candidate mining. H3/H4 across mathematical domains remain untested,
not falsified, because the corpus is single-domain and the upstream gate failed.
This is a terminal negative/inconclusive result for this design rather than an
unfinished positive-discovery implementation or permission to bypass the gates.

See [final research status](final-research-status.md) for every checkpoint and kill
criterion, [corpus results](corpus-results.md) for the verified census, and
[reproduction](reproduction.md) for executable commands and recovery. The original
research document, failed prior experiments, metric freeze and preregistered
thresholds remain preserved. Proof navigation remains a separate future project.

## Revised-plan completion record — 2026-09-13

The user supplied a revised source document after the first study. Its additional
requirements are now executed: proof-cluster power curves and independent
qualification; external length/depth metadata; a native-replay capacity audit;
one preregistered canonical-replay redesign on a fresh theorem seed; power-derived
acquisition; complete Lean verification; exact length/depth matching; within- and
cross-prover comparisons; unmatched diagnostics; baseline and diversity audits;
and archived-vector reproduction.

The new corpus has 1,864 verified proofs and 60,501 retained states. All nine
primary matched tests show association, but text clouds tie simpler baselines
at 100% pairwise wins. The added-information gate fails, closing conditional
intersection discovery under criterion 4. The stronger conjecture remains
unestablished, and cross-domain H3/H4 remain untested. No failed overlap p-value
or mathematical motif is claimed. See the [current final result](revised-plan-results.md)
and [reproduction guide](reproduction-v3.md). All 80 local tests pass; every field
of all 18 comparisons reproduces exactly from the archived corpus and vectors.


## User-directed task-design continuation — 2026-09-14

The user corrected the interpretation of the canonical study: the saturated
statement/premise controls made its added-information gate uninformative. That
instruction supersedes the hypothesis-level negative language in the historical
completion records above, while preserving their measurements and the ban on
old-corpus pair mining.

The continuation implements a preregistered adversarial diagnosis, 12 Lean
context-equivalence certificates, all context-swap controls, a new finite
associativity strategy-transfer population, exactly matched premise overlap,
a pinned Lean-trained ReProver arm, nine cheap headroom controls, paired power
simulations, and an archive-only reproduction path. The structural control's
upper accuracy bound exceeds .90; no confirmation budget through 256 triplets
meets the registered joint-power requirement. Both upstream gates therefore
close this bounded candidate before cloud scoring or held-out acquisition.

The diagnostic and small screen are complete. Conditional sampling qualification
and confirmation are not opened, and Phase 5 is explicitly outside this user
continuation. This is a documented task/budget outcome, not a cloud-hypothesis
failure. See the [current result](strategy-transfer-results-v1.md) and
[reproduction guide](reproduction-strategy-transfer-v1.md). Earlier research
sources, source freezes, failed gates and data are retained.


## Structurally matched continuation — 2026-09-14

The user's instruction to keep going opened a separately preregistered fresh
candidate. V2 uses eight-leaf associativity theorems, exact source and target
clade matching, matched premise overlap, and no theorem-pair or proof-program
reuse across triplets. All nine controls pass headroom on 64 triplets. The
registered power extension qualifies 512 triplets at a lower power bound .8324.

This opens the cloud test, which is now complete for syntax, MiniLM and the
Lean-trained ReProver, including all 100 registered proof-resampling draws.
ReProver energy scores .65625 on the initial sample versus centroid .609375,
but 0/100 draws achieves the required .10 gain over every control (80 needed).
The mean gain over its same-sample centroid is .011875. This is a failed
conditional added-information gate with demonstrated headroom, not another
ceiling or budget failure. It closes this operational candidate before nine-leaf
confirmation; broader hypotheses and smaller possible effects remain unresolved.

The [completed report](strategy-transfer-results-v2.md) and
[reproduction guide](reproduction-strategy-transfer-v2.md) contain the scope,
commands, source freezes, restart behavior and complete archived evidence.
All 93 local tests pass. No previous candidate was rescored or mined, no metric
was substituted after results, and Phase 5 remains unopened.


The user subsequently rejected the 10-point threshold as arbitrary and explicitly
instructed continuation. That direction supersedes the stopping decision above.
Preserve all measured v2 outcomes and its original protocol, while preparing a
fresh confirmation with no minimum gain requirement and explicit uncertainty.

## Completed GPU study and user cancellation of CPU encoding — 2026-09-14

The threshold-free nine-leaf continuation acquired all 512 triplets and verified
6,144 Lean proofs and 30,720 intermediate states. A deterministic repeat search
reproduced the complete assignment; all shortest-proof banks and transfer labels
passed independent checks. Syntax and MiniLM finished all 8,500 inputs.

The user approved a temporary GPU instance. A label-blind development benchmark
found approximately 168 texts/sec but CPU/GPU vector differences beyond rounding.
The GPU supplement was committed at `2c2e357` before confirmation GPU embeddings
or scores. It designated a separate hardware check and retained the CPU primary.
All 8,500 GPU inputs completed in 54.19 seconds, with identical frozen assignments,
weights, singleton batches, tokenization, pooling and analysis rules. No CPU
ReProver vectors were mixed into that arm.

The complete GPU cloud scores 53.91%, versus its centroid54.49%; paired gain is
-0.59 points with marginal 95% bootstrap interval [-2.54,+1.37]. All nine cheap
controls pass headroom; no paired superiority component passes. Tactic and
complete-program controls score 82.03% and 92.19%, with the latter explicitly
having more proof information. There is no ten-point threshold in these results.
This supplies no positive added-information evidence for this operational test,
while leaving smaller possible effects and the broader conjecture unresolved.

After seeing the GPU result, the user explicitly cancelled CPU work. Its encoder
and both waiting drivers were stopped with 7,270 CPU ReProver inputs cached;
no partial CPU result was scored. The planned CPU/GPU outcome comparison is
cancelled, and the GPU result retains its prospectively secondary provenance.
The full original CPU confirmation is not falsely reported as completed.

The [completed GPU report](gpu-execution-results-v1.md) and archived reproduction
commands now provide the finished numerical result. All GPU fields reproduce
exactly, including supplemental controls. The instance, temporary security group
and registered SSH key were removed; estimated compute cost is at most about
USD .27, excluding small storage/network charges. No expensive acquisition or
Phase 5 was opened, and no old population was mined for interesting pairs.
