# Corrected State-object implementation

This implements [the current specification](current-state-object-spec.md). It
samples theorem identities, inventories every published proof record associated
with each selected identity, and retains every acquired state occurrence. It
trains no model and has no prediction-accuracy objective.

## Frozen population and inclusion target

The September 14 draw contains 256 theorems: 128 Mathlib names and 128 Lean Workbook
problem IDs. Selection uses a fixed seed and SHA256 ordering of theorem IDs,
before encoding or geometry. The source inventory and draw are archived in
`results/state-object-v1/`. The theorem IDs do not change when acquisition fails
or additional proof versions are found. Neither proof count nor proof length nor
state count is a selection variable. Workbook eligibility requires at least one
published proof record; empty proof lists are inventoried in the original source
but do not provide a proof population.

The initial 1,223 proof records include two LeanDojo Mathlib snapshots, the
original Lean Workbook proof lists and completed stepwise episodes, original
Goedel proofs, and their published Lean4.27 migration. Additional LeanTree
Mathlib4.19 declarations extend the inclusion inventory after matching source
spans. A source record is not necessarily a distinct mathematical proof: identical
scripts and migrated versions retain their separate provenance. Multiple
`by` blocks within one declaration are parts of one proof.

Completeness is audited against enumerated releases. Coverage of all mathematical
literature, equivalent formulations, informal proofs and unknown alternative
proofs is **not established**. Cross-version names alone do not certify identical
elaborated statements; unresolved identity mappings stay explicit. Missing,
invalid or untraceable records cannot silently become smaller complete objects.

## Acquisition and measurement

`collect-state-object-sample.py` inventories first, freezes theorem IDs, then
retains all associated proof records. `enrich-state-object-sources.py` retrieves
full source files at pinned revisions and records SHA256 hashes. Missing files
in the Hugging Face migration mirror are recovered from its author's pinned
GitHub repository. Original source files and failed requests are retained.

`patch-state-object-repl.py` adds before/after goal observations for all original
syntax tactic nodes, including structural and nested nodes. Proof source is
unchanged. `replay-state-object-proofs.py` checks completion and reported axioms,
rejects `sorryAx`, and checkpoints every attempt. A timeout is an acquisition gap,
not an exclusion rule. These are tactic-level states; opaque internal operations
of automated tactics are not all exposed. Factorized LeanTree subgoals are
archived separately until their original proof context can be replayed.

`encode-state-object-states.py` uses the pinned, existing Lean-trained ReProver
ByT5 export on a temporary A10G. It encodes **all UTF-8 bytes**, with no inherited
1,024-token limit or truncation. All inputs use one fixed `int8_float32` runtime,
mean pooling including EOS, and L2 normalization. Exact input duplicates share a
vector cache, while every proof/state occurrence remains recorded. Each vector
is checkpointed atomically. The older CPU duplicate is not resumed.

An initial half-precision runtime produced nonfinite vectors on this model and
was rejected; its diagnostic attempt is archived separately. It supplies no
vectors to the selected float32 coordinate space. A multiline-JSON parser issue
in the first replay attempt was corrected and those attempts rerun.

## Geometry and verification

`noema.state_objects.assemble_object` binds proof inclusion, occurrences and
encoder identity. Missing proofs, incomplete traces, missing vectors or explicit
coverage gaps prevent complete-object status. The candidate object is the filled
convex hull of every acquired valid state vector. It is stored implicitly as all
its generating vectors; no centroid or neighborhood radius defines it.

`hull_relation` solves nonnegative barycentric feasibility and checks witnesses
in the original embedding coordinates, or returns a checked separating
hyperplane. Numerical ambiguity remains unresolved. Projections may illustrate
objects but cannot establish original-space intersection. Each convex hull is
connected and contractible by construction; this is not an empirical discovery.
Shared completed-state inputs must be identified because they can force contact
between otherwise unrelated theorems.

Tests include inclusion of 400 proofs with variable numbers of states,
invalidation when a proof or embedding is missing, encoder-space isolation,
containment/contact/separation, more than eight necessary vertices, and a false
overlap caused by projection.

## Execution status

Acquisition and geometry reporting are in progress. The active recovery pointer
is `outputs/ACTIVE_CONFIRMATION.md`; every completed remote record is synchronized
locally. The temporary instance has automatic termination. Final coverage counts,
artifacts and resource cleanup will be recorded here when the run finishes.
