# Recovery checkpoint: convex hull investigation

**Current display:** `results/theorem-boundaries-v2/explore.html` implements the
user's inward-bending minimum-area boundary request, removing `no goals` from
geometry while preserving every raw record. All 10,748 nonempty states are plotted;
all 16,592 records remain inspectable. Shared axes, labeled x/y ticks and original
zero are shown; `lean_workbook_34313` and `lean_workbook_13957` open in an overlay.
Every projected location is a boundary vertex; global minima are proven only for
exhaustive small or degenerate cases. Read the new results README. This is a 2D
boundary study; higher-dimensional nonconvex regions remain undefined. Prior
convex archives and their vectors are unchanged.

**Latest exploration:** [theorem-object forms](theorem-forms-v1.md), archived in
`results/theorem-forms-v1/`, measures all 102 admitted hulls using all 16,592 rows.
An interactive all-object atlas and PDF preserve every state. Every diameter
uses the common empty-goal point. Literal whitespace variants occur in 79 objects
and can span substantial fractions of their diameters. These are recorded-display
forms, not established mathematical shapes. The exceptional intersection now has
a separating-plane certificate for exactly a shared segment within numerical
precision. Admission and source arrays are unchanged; no new encoder or GPU run.

**Latest active dataset:** `results/state-objects-admitted-v1/` has 102 theorem
groups and 16,592 separate physical state-vector rows. Six groups are excluded
for contradictions proved in Lean; 148 are held for source identity or proof/trace
gaps. Read [the remediation](theorem-admission-remediation-v1.md). The original
26,820-row archive is preserved for recovery, not active analysis. No new GPU
or encoder run was needed. Do not reinstate held groups by changing labels;
resolve their evidence gaps and rebuild admission.

**Current recovery entry (September 14, 2026):** all 26,820 recorded states now
have separate physical vector rows in `results/state-object-records-v1/`, pushed
in commit `8c42e6d`; CI run `34907220974` passed. No deduplication is permitted.
The subsequent [assumption audit](assumption-audit-v1.md) qualifies source coverage,
proof diversity, state capture and geometry interpretation, with archived evidence
in `results/assumption-audit-v1/`. Numerical and checkpoint validation defects are
fixed in source. No new encoder run or paid resource is required to recover this
work. The original source corpus and original coordinates remain unchanged.

**Latest scope correction:** read [the current specification](current-state-object-spec.md)
before resuming. The user explicitly rejected the proposed audit of eight-state
objects as a substitute for their objective. Sample theorems, then include every
known proof and every extractable intermediate state for each selected theorem.
Investigate geometry and mathematical relationships; no model training or
prediction task is the current goal. The earlier proposed eight-state audit below
is historical and superseded. The corrected inventory, acquisition and all-pairs geometry pass are now complete,
with explicit coverage gaps. See [the current results](state-object-implementation-v1.md)
and [durable archive](../results/state-object-v1/README.md). The sections below
preserve the earlier checkpoint history.

Updated 2026-09-14. The user authorized a small investigation of the "rubber band"
definition of a State object: the convex hull of embedded proof states. They
also explicitly requested crash recovery and preservation of completed compute.

## Conceptual correction

A proof state contains the local context and current goal. Each retained state
is encoded as one vector (1,472 coordinates in ReProver). A theorem contributes
states across its proofs. The user's intended State object is an occupied region,
whose intersections and connectivity are the research target. The earlier
eight-vector energy-distance transfer experiment did not construct such a region
and does not resolve this objective. Its centroid was only a baseline.

Use "State object" in discussion. The user rejected adding neighborhoods around
points. Investigate convex hulls without neighborhood radii. In 2D this is the
rubber-band enclosure; in higher dimensions use its convex-hull generalization,
without claiming to minimize a higher-dimensional perimeter or surface area.

## Durable previous work

Completed numerical and terminology archive commit:
`e1b1f2a27b134e2bb91810a8dd0128e0f0bcb8b6`, pushed to origin/main.
Exact-head CI run `34886834596` passed.

- `results/gpu-execution-check-v1/run/reprover-embeddings.npz`: all 8,500 encoded
  inputs. No GPU rerun needed. SHA256:
  `a2be3c9e6eeb6b380c3f9b698d36e3746e526d10e503bdf439fc8de612157791`.
- `results/strategy-transfer-confirmation-v1/`: frozen 512 triplets; all 6,144
  sampled proofs and 30,720 intermediate states verified; complete syntax and
  MiniLM embeddings; proof-bank, transfer and assignment audits.
- `results/gpu-execution-check-v1/`: completed scores and reproducibility data.
- `results/device-benchmark-v1/`: timing, device checks and resource cleanup.
- `scripts/verify-gpu-execution.py`: reproduces numerical GPU results from the
  saved arrays without acquiring embeddings again.

CPU encoding was cancelled by the user at 7,270 saved inputs. Do not resume it.
Those partial CPU checkpoints are local only, documented in cancellation.json;
the complete GPU arrays are the durable alternative. The temporary AWS instance
was terminated and temporary key/security group removed. No paid resource should
be relaunched for this small geometry investigation.

## Current investigation

Latest instruction: **literature review first, before a new research project**.
The hull experiment is on hold. At this checkpoint only existing files have been
inspected; no new geometry results or experiment code exist.
Planned analysis uses all 1,024 preassigned anchor-candidate comparisons from the
512 confirmation triplets. It does not search for favorable pairs or reuse
strategy-transfer labels as a new confirmatory outcome. Treat it as explicitly
user-requested exploratory geometry, separate from frozen earlier studies.

Construct each hull from the eight saved state vectors (duplicates do not enlarge
a hull). Test intersection by nonnegative convex-combination feasibility, with
numerical witnesses/separating-hyperplane checks. Compare original-space results
with fixed common PCA projections, and plot the first assigned pairs rather than
selecting pictures for their outcomes. Eight vectors span at most seven affine
dimensions, so disjointness of these sparse hulls does not establish disjointness
after collecting states from many more proofs. Each convex hull is connected and
has no holes by construction; this definition can test between-object overlap,
but cannot discover internal holes or disconnected components of one object.

Completed: a cited literature review in
`docs/state-object-convex-hull-literature-review.md`, covering
conceptual spaces, formal-proof representations, convex geometric semantics,
convex separation and the nerve theorem. Preserve historical protocols and
numerical arrays. Do not silently resume the previously proposed experiment
before reporting this review. The proposed geometry audit remains unimplemented
and unrun; no new encoding, hull analysis or paid compute occurred.

The review contains 17 references, including the original plan's mathematical
representation papers, conceptual spaces, convex ontology semantics, SVM convex
separation, the nerve theorem, and a June 2026 axiom-dependence preprint. It
includes elementary derivations of the sparse-sample dimension bound, normalized
unit-vector containment obstruction, projection asymmetry, and monotone hull
growth. These are mathematical deductions, not new measured corpus results.

The main README and the strategy-transfer report now explicitly distinguish the
previous finite-sample predictor from the intended occupied-region objective.
Historical protocols, archived scores and embeddings remain unchanged.

Recovery verified directly: `git ls-remote origin refs/heads/main` returned the
completed-work commit above, and the 92 MiB GPU archive's SHA256 matched the
recorded value. The checkpoint below supplements the older local note at
`outputs/ACTIVE_CONFIRMATION.md`; this document takes precedence on scope and
terminology. The first recovery-note commit, `59d5e85`, was pushed and its CI run
`34889214311` passed. The literature review and scope clarification are the next
documentation checkpoint.
