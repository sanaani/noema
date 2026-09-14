# Corrected State-object implementation and first acquisition

**Historical acquisition report.** The first acquisition did not meet the full
specification. The [current admission and remediation](theorem-admission-remediation-v1.md)
excludes known contradictory cases and holds unresolved groups. Use the active
dataset linked there; the archive below preserves original results and provenance.

> **Interpretation corrected after the input-identity audit:** the coordinates
> represent printed local-goal displays, not verified complete mathematical state
> identities. Identical displays can hide different underlying information;
> `no goals` can describe a finished subtask while other proof work remains.
> See [the audit and controlled Lean counterexamples](state-input-identity-audit-v1.md).
> The numerical archive below is preserved; its semantic interpretation is provisional.

The corrected implementation is complete, and the first acquisition and geometry
pass ran on September 14, 2026. It samples **theorems**, includes every proof record
found in the enumerated sources for each selected identity, and retains every
valid acquired state occurrence. The candidate State object is the **filled
convex hull** of those vectors. No centroid or neighborhood radius defines it;
no encoder was trained and no prediction task was run.

The [interactive explorer](../results/state-object-v1/explore.html) and
[archived results](../results/state-object-v1/README.md) contain the actual objects,
full state text, provenance and checked original-space relationships. Download or
open the HTML locally; GitHub's source preview does not execute it.

## What was acquired

| Measurement | Result |
|---|---:|
| Frozen theorem identities | 256: 128 Mathlib, 128 Lean Workbook |
| Included proof records | 1,337 |
| Proof records with a complete acquired trace | 1,313 |
| Proof records with unresolved trace/validation gaps | 24 |
| Retained valid state occurrences | 26,820 |
| Unique valid state inputs, all encoded | 3,659 |
| Theorems with acquired State objects | 255 |
| Theorems with all inventoried proof traces acquired | 234 |
| Objects also passing the stated source/identity audit | 111 |
| Largest inventoried proof collection for one theorem | 37 records |
| Largest acquired object | 273 distinct state inputs |
| Original coordinate dimension | 1,472 |

A source record is **not necessarily a distinct mathematical proof**. Identical
scripts, migration versions and independently published copies keep separate
provenance. The initial inventory held 1,223 records. Further source and kernel
inspection expanded it to 1,337 without changing any of the 256 sampled IDs.
Multiple `by` blocks inside one theorem were treated as parts of one proof.

Selection used the frozen seed and SHA256 ordering of theorem IDs, before
encoding or geometry. Neither proof length, proof count nor state count was a
selection variable. Workbook eligibility required at least one published proof
record. There was no cap on proofs, states, or encoder input length. The largest
state used 17,338 UTF-8 byte tokens plus EOS and was encoded whole.

**This does not establish coverage of every known mathematical proof.** The
source census covers the pinned releases listed below. Informal proofs,
equivalent formulations, unindexed alternatives and unknown proofs remain
outside established coverage. A timeout or source failure retains its original
inclusion target and explicit gap; it does not replace the theorem in the sample.

## Geometric result

All 32,640 unordered theorem pairs were examined; none were sampled out.

| Original-space result for acquired regions | Pairs |
|---|---:|
| Intersection is only the shared completed-proof point | 32,384 |
| Intersection extends beyond that point | 1 |
| Unobservable because one theorem has no validated states | 255 |
| Numerically unresolved among observed pairs | 0 |

Every observed object includes the exact `no goals` state. Consequently, all
255 observed hulls intersect and their intersection graph is connected. Their
union is star-shaped about that shared point. These facts follow from the
representation's common completion state; they are **not evidence that all
sampled theorems share mathematical content**.

For 32,384 pairs, a strict separating plane through the completion point
certifies that it is the entire intersection of the acquired hulls. One pair,
`lean_workbook_plus_9114` and `lean_workbook_5091`, additionally shares:

```lean
a b c : ℝ
⊢ 0 ≤ (a - b) ^ 2 + (b - c) ^ 2 + (c - a) ^ 2
```

The segment from this state to completion belongs to both objects. This is a
concrete shared algebraic obligation. It establishes a shared segment, not
overlap of positive volume or a general relationship-discovery result. The
shared state was identified by the exhaustive pair analysis, not by changing
the theorem sample after inspecting results.

Each hull is connected and has no holes by definition. The largest numerical
affine dimension is 272; every object has fewer than 1,473 generating points and
therefore **zero 1,472-dimensional volume**. It still has an occupied region
relative to its own affine span. This is a material limitation of literal
full-space volume with this encoder and acquisition size. Neither missing states
nor dimensions were discarded to manufacture an overlap.

The explorer uses one common 2D PCA projection of all 3,659 unique vectors,
accounting for 19.45% of their variation. It draws every acquired generating point
of the displayed objects. **Screen overlap is illustrative; classification uses
the original coordinates.** The projection's global origin is display metadata,
not the definition of a theorem object.

## Proof and identity coverage

The 24 unresolved proof records comprise six timeouts after attempts up to 600
seconds, sixteen source-validation failures, and two Mathlib generated/alias
records whose original tactic states could not be attributed. They all remain
in [coverage-gaps.json](../results/state-object-v1/coverage-gaps.json), with full
source and attempts in the archive. `lean_workbook_52061` has no validated acquired
states and remains one of the 256 selected theorem identities.

All 120 selected proof records from the older Mathlib 4.7 snapshot and all 122
from the 4.10 snapshot replayed successfully. An additional 114 Mathlib4.19
records were inventoried; 112 supplied attributable complete traces. The two
exceptions are `StarSubalgebra.embedding_inclusion` (alias) and
`hasSum_nat_add_iff'` (generated by `to_additive`). The kernel declaration and
source provenance remain included; no substitute states were invented.

Full declaration names and source ranges were audited against the pinned Lean
kernels. One short-name match incorrectly associated `BoxIntegral.Box.volume_apply`
with a similarly named declaration in the same file. It was explicitly
quarantined, its attempted replay retained diagnostically, and its vectors
excluded from this corpus's geometry.

Among the 128 Mathlib identity groups, 119 have different elaborated expressions
across versions. These may reflect binder, instance or library changes, but their
equivalence was **not established**. Fourteen also lack an exact-name declaration
in Mathlib4.19 and need renamed/equivalent-formulation mapping. The provisional
aggregate objects retain their source variants and identity-gap flags. Identical
expression syntax also presumes referenced constants retain their meanings.
Thus complete proof acquisition (234 objects) and complete audited inventory
status (111 objects) are deliberately separate. Neither means global proof
completeness.

Four Workbook scripts have an independently rechecked, `sorryAx`-free proof term
but a redundant trailing tactic reports `no goals to be solved`. Their source
and compiler errors remain unchanged and visible. Only that exact redundant
error is accepted after the kernel recheck; other source failures contribute no
validated states. Separate failed attempts and publisher data remain archived.

## Sources and instrumentation

The census includes all associated proof records found in these pinned sources:

- [Lean Workbook](https://huggingface.co/datasets/internlm/Lean-Workbook), revision
  `2e066e310b2c6d2c27616927ae131f82901c8f1c`: all entries in selected problems'
  proof lists and all complete published stepwise episodes.
- [Goedel Lean Workbook proofs](https://huggingface.co/datasets/Goedel-LM/Lean-workbook-proofs),
  revision `b731852af8d8ab11498fda27bce9020738c01c59`.
- [Lean4.27 migration](https://huggingface.co/datasets/banach1729/goedel-workbook-lean427),
  revision `4049a8c4c2c7ae05d41207dccba1e9bf8afeb664`. Missing mirrored full sources
  were recovered from the author's [repository](https://github.com/mike1729/goedel-workbook-lean427)
  at `3c2afe6bfc6bdeca6b78d1f257468164bba56966`.
- LeanDojo [release 10929138](https://zenodo.org/records/10929138) and
  [release 12740403](https://zenodo.org/records/12740403), covering Mathlib commits
  `fe4454af900584467d21f4fd4fe951d29d9332a7` and
  `29dcec074de168ac2bf835a77ef68bbe069194c5`.
- [LeanTree](https://huggingface.co/datasets/ufal/leantree), revision
  `ea65c26187a456958f17d57b28376aec1dedf1a7`, supplemented by kernel-resolved
  declarations from Mathlib4.19 commit `c44e0c8ee63ca166450922a373c7409c5d26b00b`.
  Factorized subgoal records are preserved separately; geometry uses replayed
  original-context states rather than substituting factorized goals.

All original full source files, checksums, source cards, retained trace
occurrences and failed attempts are archived. The observer records before/after
states at all original syntax tactic nodes, including nested/structural nodes.
Term proofs receive attributable proof-term boundary observations. This is
**tactic/term-level extraction**, not access to every opaque internal inference
of an automated tactic. Whole Mathlib files were elaborated in their original
contexts, observing only selected declaration ranges.

The existing Lean-trained ReProver ByT5 export was fixed at revision
`8612469b496b72bdb2f0d6ccd5316c100200581e`, model SHA256
`311e636b7479e97236de85f5271f2b045e1e40a1de5a431df03b050b2176f827`.
Every final vector uses the same L40S GPU, `int8_float32` runtime, full byte input,
mean pooling including EOS, and L2 normalization. Exact text duplicates share a
cache without losing any occurrence association. The encoder manifest accompanies
the vectors; no CPU duplicate of the old experiment was resumed.

Initial half-precision NaNs, A10 memory limits, an older Lean JSON parser's
astral-Unicode handling, and observer/parser defects were diagnosed and corrected.
Successful final coordinates were uniformly regenerated in the fixed L40S
runtime. Failed attempts supply no final coordinates. Resumption uses atomic
per-proof and per-state checkpoints; corpus assembly refuses unknown proof IDs,
changed proof bodies or mixed encoder spaces.

## Verification and execution record

The suite covers all-proof inclusion (including a 400-proof fixture), every
recorded state, missing-proof/vector invalidation, immutable provenance,
Unicode/full-length requests, term/tactic attribution, more than eight necessary
vertices, separation, point contact, larger intersection and false overlap under
projection. Lint, formatting and all 122 tests pass.

`verify-state-object-archive.py` independently rechecks every archived vector
hash, proof inclusion and occurrence association, and all 32,640 pair records.
For point contacts it reconstructs each separating plane from stored coefficients
and checks every generating point in the original coordinates. Numerical
certificates use floating-point checks; they are not exact-arithmetic formal
proofs. Remote-to-local artifact hashes were also checked before termination.

A temporary Ohio GPU instance was used, initially A10G and then L40S with more
host/GPU memory so the longest inputs could be retained. The original absolute
shutdown deadline and $5 ceiling were preserved. Results were copied locally
before terminating the instance. Final resource cleanup and the estimated charge
are recorded in the accompanying compute manifest.

The prior synthetic study, vectors and literature review remain preserved. This
run establishes an auditable implementation and an initial, explicitly incomplete
source census. It does not settle whether the convex hull is the best State
object definition or whether fully acquired theorem objects carry the intended
mathematical relationships.
