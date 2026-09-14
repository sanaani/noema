# Recovery checkpoint: convex hull investigation

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
