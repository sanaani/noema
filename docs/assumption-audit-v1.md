# Audit of unsupported assumptions

The problem extended beyond deduplicating states. I repeatedly treated a convenient
measurement choice as if it fulfilled the scientific objective. This audit separates
what the archive demonstrates, what was only assumed, and what has now been corrected.

All **26,820 recorded states now have separate physical vector rows**, grouped under
256 theorem identities. No states, proof copies or equal coordinates have been removed.
The rows contain their previously computed coordinates; storing them separately does
not recover internal context that the original printed inputs omitted. The current
[record archive](../results/state-object-records-v1/README.md) passed row-by-row
verification and CI (`8c42e6d`, run `34907220974`).

## Findings and actions

### 1. Identical printed text meant identical mathematical state

**Not justified; counterexamples established.** The preceding
[identity audit](state-input-identity-audit-v1.md) demonstrated that Lean can print
identical goals with different underlying constants, or print a focused subgoal
while hiding different pending obligations. It also found printer elisions in the
actual corpus. We cannot count actual false identifications because the necessary
internal snapshots were not recorded.

**Addressed:** separate provenance identities and vector rows are implemented;
future encoding checkpoints by record identity. Mathematical state identity remains
unverified. A future acquisition must capture structured goals, local context and
environment information before claiming to solve this missing-context problem.

### 2. Counting source proof records measured independent proof diversity

**False as a counting inference.** The 1,337 source records contain **1,093 distinct
scripts within their theorem groups**, with **244 additional exact script copies**.
Different scripts may also express the same argument. Conversely, identical script
text in different environments does not establish identical elaborated proofs.
This audit does not claim to have counted independent mathematical arguments.

**Addressed:** current descriptions distinguish proof records, scripts and
independent proofs. Every copy and all its states remain. The exhaustive
[duplicate groups](../results/assumption-audit-v1/duplicate-script-groups.json)
identify the records; they are annotations, not an exclusion list.

### 3. Successful replay meant we captured every state of a proof

**Not established.** The archive contains 1,317 accepted local replay traces:
1,146 observe tactic nodes, while **171 observe only outer proof-term obligation
and completion boundaries**. There are also 266 publisher traces. An automated
tactic can perform many internal operations between observations. Several recorded
nodes can describe nested parts of the same tactic, so counts are not comparable
as counts of independent reasoning steps.

The `trace_complete` flag is operational: replay succeeded, some states were
extracted, and an empty active-goal record appeared, subject to extraction checks.
It does not establish exhaustive internal state capture. **1,313 proof records meet
that operational criterion; 24 do not.** The archive also contains **8,909 `no goals`
records**, which can represent completion of a local subtask.

**Addressed:** the specification distinguishes extraction granularity and operational
completion from full capture. Existing flags remain historical evidence; the audit
adds explicit per-theorem limitations without rewriting their meaning retroactively.

### 4. A kernel-accepted theorem was necessarily a meaningful problem instance

**A concrete counterexample exists in the selected corpus.**
`workbook:lean_workbook_plus_5257` assumes three natural numbers are each at least
20, while their sum is at most 18. Those assumptions cannot all be true. Its
conclusion therefore follows regardless of the substantive bound it states.

An independent [Lean4.9 diagnostic](../results/assumption-audit-v1/Vacuous.lean)
proves `False` directly from the same assumptions, with no `sorry` and only
`propext` and `Quot.sound` in its axiom report. The
[saved verification](../results/assumption-audit-v1/vacuity-verification.json)
pins the fixture and Lean binary. The source group has **26 proof records and
313 recorded states**. The audit checks that every script contains those assumptions.

**Addressed:** this group is explicitly annotated as having inconsistent assumptions;
all 313 states remain. Other theorem groups are marked *not checked for consistency*.
This is not an exhaustive search for inconsistent assumptions, nor a determination
that the formalization contradicts its original informal author's intent.

### 5. A bounded source census fulfilled “all known proofs”

**Not established.** The inventory covers enumerated formal-source releases, not all
mathematical literature. It does not supply every known informal proof or all
equivalent formulations of a theorem. In the existing identity audit, **119 Mathlib
groups have differing elaborated expressions across versions**; equivalence was
not proved. A known short-name misassociation was already quarantined. Even the
111 groups passing the enumerated coverage/identity checks do not establish global
proof completeness.

**Addressed:** the full inclusion target is retained, while current acquisition is
labelled incomplete against the broader goal. Per-theorem audit annotations carry
the existing gaps and do not upgrade source-census completion to global completion.

### 6. 256 theorem IDs was an adequate or representative scale

**No adequacy argument was supplied.** The 128-per-family default was a convenience
choice. The frozen population has 123,667 Mathlib IDs and 30,766 Workbook IDs, while
the sample is split 128/128. It is a stratified pilot, not a sample matching those
population proportions and not an established representative sample of mathematics.
There was no coverage or geometric-stability argument showing that 256 suffices.

**Addressed:** removed the implicit sampling-size default; future draws require an
explicit count. The current sample stays frozen and is described as a bounded pilot.
No unreported resampling or new acquisition occurred during this audit.

### 7. A math-trained encoder made its geometry mathematically faithful

**Unvalidated.** ReProver was developed for premise retrieval; that training objective
does not by itself establish that distances, linear interpolation, hull volume or
hull intersection represent mathematical relationships. This distinction follows
from the stated task in the [LeanDojo paper](https://arxiv.org/abs/2306.15626v2)
and the authors' [retriever documentation](https://github.com/lean-dojo/ReProver/blob/main/README.md).

The current measurement also depends on serialization, mean pooling, L2 normalization
and a quantized model execution. Robustness of the scientific interpretation to those
choices has not been tested. **199 state records, comprising 79 distinct inputs,
exceed 1,024 UTF-8 bytes plus EOS; the maximum is 17,339.** These were processed whole.
That establishes execution without truncation, not semantic quality at those lengths;
1,024 here is a length diagnostic, not a newly asserted model validity limit.

**Addressed:** the encoder is explicitly a fixed measurement instrument. Claims of
faithful mathematical geometry are withheld. This audit neither trains a model nor
substitutes a prediction task for the user's exploratory objective.

### 8. Hull connectivity and a projected picture revealed theorem topology

**Some observed properties are imposed by construction.** A nonempty filled convex
hull is connected and contractible. Every observed hull contains the same encoded
`no goals` display, so the 255 observed hulls all meet there. That common intersection
cannot establish a substantive relationship among all those theorems.

The archive's largest affine dimension is 272 in a 1,472-dimensional space. Thus
these finite hulls have zero volume in the full ambient space. Lower-dimensional
extent still exists; it should not be confused with full-dimensional volume or
the extent of all possible proof states. See the elementary derivations in the
[literature review](state-object-convex-hull-literature-review.md).

Keeping every row also changes the weighting of a PCA illustration: the current
projection explains **39.02%** of variation across recorded rows; the earlier
unique-input projection explained **19.45%** across its differently weighted inputs.
Neither picture determines original-space intersection. Longer or more frequently
recorded proofs contribute more rows; those rows are not independent observations.

**Addressed:** the user's rubber-band hull remains a candidate definition. We distinguish
its imposed properties from discovered mathematical relationships, retain every
boundary/terminal state, and use original-space certificates rather than pictures
to classify the acquired regions. Repetition counts remain visible.

### 9. Solver success supplied a valid intersection certificate

**A numerical bug was reproduced and fixed.** For the interval `[0,1]` and the point
`1.0000000005`, the solver supplied weights approximately `[-5e-10, 1.0000000005]`.
The old validation accepted that tiny negative weight. It gave zero residual by
extrapolating outside the interval and incorrectly reported intersection.

**Addressed:** intersection certificates now require nonnegative weights and
roundoff-scale normalization checks in both geometry routines and the archive
verifier. Three gap regressions are covered. These cases now return *unresolved*
rather than a false intersection. Floating-point certificates remain numerical,
not exact formal geometric proofs.

The saved pair classifications are unchanged under the stronger verifier:
32,384 point contacts, one intersection extending along a shared segment, and
255 pairs involving an unobserved object. Their certificates do not rely on the
negative-weight failure. They describe the acquired encoded displays only.

### 10. Existing replay files were necessarily compatible and properly verified

**Two validation defects were found.** The Mathlib worker returned existing
checkpoints without verifying their source, target or declared environment.
The axiom-report checks could accept another theorem's report through substring
matching; checking only for `sorryAx` also did not enumerate other axioms.

**Addressed:** checkpoint reuse validates proof ID, theorem ID, body hash, complete
Mathlib source artifact and declared environment. Corpus assembly now checks the
complete Mathlib source artifact too. Both workers require the exact target's
report and explicitly enumerate the accepted foundational basis:
`propext`, `Classical.choice`, `Quot.sound`. Other axioms require review rather than
being silently accepted. Validation policy is versioned; pre-policy checkpoints
must be preserved and replayed into a new directory before future reuse under
the new policy. Source or environment mismatch fails before execution.

The exhaustive retrospective check found **no mismatch in 1,429 archived attempts**.
All **1,317 accepted attempts** have the correct target report and use only the
listed basis. Thus these were real code defects, but this audit found no resulting
misclassification in the accepted archive. Environment labels do not independently
prove all toolchain binaries or transitive imported meanings identical; that remains
a provenance limitation.

### 11. Earlier engineering gates represented the user's objective

**They did not.** The earlier eight-vector predictor, centroid comparison and
arbitrary ten-point gate did not implement an occupied region from all known
proof states. The user corrected that scope. The older implementation document
still looked authoritative enough to reintroduce those choices on recovery.

**Addressed:** it is now prominently marked historical, and the README points to
the corrected specification. Earlier numerical results remain intact, but they
do not settle the current hypothesis. No mining or reopening of those closed
experiments was performed for this audit.

## Evidence, recovery and limits

[Machine-readable evidence](../results/assumption-audit-v1/README.md) includes the
exhaustive script count, every replay check, per-theorem annotations, the numerical
counterexample and the Lean-checked inconsistency. Source corpus and coordinate
archives are unchanged. New tests exercise the actual failure modes, and CI
repeats the retrospective audit alongside archive verification.

The numerical and checkpoint defects are repaired; unsupported claims are qualified
in the current specification. Complete semantic-state capture, all-known-proof
coverage, representative scale, proof independence and mathematical faithfulness
of the embedding remain unestablished. This audit does not turn those unknowns
into negative results about the State-object idea, nor claim that documentation
changes alone supply the missing evidence.
