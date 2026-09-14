# Audit of the 26,820 state records and 3,659 encoder inputs

**Finding: identical printed text is not a validated identity for a mathematical
proof state.** The cache preserved every recorded vector association, but the
information supplied to the encoder is insufficient to establish that identically
printed records represent the same underlying state. The earlier assurances that
we had retained the full mathematical state were too strong.

The audit inspected every record and coordinate reference in the frozen corpus,
checked the observer code, and ran controlled counterexamples in **Lean 4.9.0**,
the version used for the main Workbook replay. It required no GPU or new encoding.
The original sources, vectors, object definitions and numerical certificates have
been preserved. The audit does not silently replace them with a new experiment.

## A concrete failure, checked in Lean

In one namespace, define `x` as 5. In another, define `x` as 6. Ask Lean to display
the goal `x = 5` in each namespace. Both print exactly:

```text
⊢ x = 5
```

Yet their internal expressions refer to different constants, `Distance.x` and
`Apples.x`. The first goal is true and the second false. The fixture checks the
first equality and the negation of the second in Lean, without `sorry` or an
unproved axiom. Both inputs would receive the same cache key and encoder input
under the existing text-only scheme.

This is a **controlled counterexample to the assumption**, not a claim that these
two invented namespaces occur in the collected corpus. The source, compiler
output and checks are archived in
[Counterexamples.lean](../results/state-identity-audit-v1/Counterexamples.lean) and
[counterexample-verification.json](../results/state-identity-audit-v1/counterexample-verification.json).

A second fixture proves `True ∧ True` and `True ∧ (2 = 2)`. Inside the left-hand
branch, both display `case left` followed by `⊢ True`; the pending right-hand
obligation is absent from that focused display. Thus even an identical *local*
goal need not be an identical *whole-proof* state. The observer records the active
goals at nested tactic nodes, not a complete account of suspended enclosing work.

The original observer calls Lean's `ContextInfo.ppGoals`, which calls
`Meta.ppGoal`, the formatter exercised by the fixture. Lean4.9's implementation
omits some local implementation declarations by default and applies expression
pretty printing. These behaviors can be inspected in the pinned
[goal printer](https://github.com/leanprover/lean4/blob/v4.9.0/src/Lean/Meta/PPGoal.lean)
and [printing options](https://github.com/leanprover/lean4/blob/v4.9.0/src/Lean/PrettyPrinter/Delaborator/Options.lean).
Lean's [proof-state documentation](https://lean-lang.org/doc/reference/latest/Tactic-Proofs/Reading-Proof-States/)
also explains that displayed states can hide proof terms and large expressions.

## Where the numbers come from

These are exhaustive counts, not estimates:

| Accounting stage | Entries remaining | Reduction from previous stage |
|---|---:|---:|
| All recorded states | 26,820 | — |
| Count identical text once within each recorded trace | 7,557 | 19,263 |
| Count identical text once within each proof record, across its traces | 7,022 | 535 |
| Count identical text once within each theorem, across its proof records | 3,914 | 3,108 |
| Count identical text once across all theorems | 3,659 | 255 |

The reductions describe **text reuse**, not proven semantic duplication. The
first reduction includes repeated before/after and nested observations as well
as any genuine returns to an identically printed state. It should not be described
as deleting 19,263 mathematically redundant steps.

Most text reuse occurs inside a theorem's observations and proofs. Only **two
text strings occur across different theorem IDs**: `no goals`, plus one shared
algebraic subgoal. The final reduction of 255 consists of 254 additional theorem
associations for `no goals` and one for the algebraic subgoal. It is not evidence
of thousands of geometrically overlapping theorem states.

The corpus contains 8,909 `no goals` records, across 1,313 proof records and 255
theorems. **`no goals` can also mean a nested or focused tactic has no active goals;
it does not, by itself, establish that the entire proof is complete.** The
compiler's separate verification establishes accepted proof completion. My earlier
explanations treated this distinction too loosely.

## Issues found in the actual corpus

- **33 distinct inputs, appearing in 128 records across five Mathlib theorems,
  contain `⋯`.** The display has hidden part of an expression. Some hidden parts
  are proof terms, whose differences can be irrelevant to Lean's logical meaning;
  the marker is not proof that every affected record is semantically wrong.
  It does establish that the source display is not a lossless internal snapshot.
- **744 nonempty input strings recur under multiple environment labels.** These
  labels include different printer/library versions, publisher traces and retry
  variants. A label difference is a risk flag, not a proof of changed semantics;
  some labels refer to the same underlying Lean/Mathlib environment.
- **264 nonempty input strings are associated with multiple elaborated theorem
  expression variants.** Those are parent theorem expressions, not the internal
  expressions of the individual goals. This is not a count of proved false merges.
- **No complete internal goal/context/environment snapshots were archived for
  these 26,820 records.** Full proof source and replay provenance remain available,
  but the hidden information cannot be reliably reconstructed from the cached
  text alone. Replaying the pinned sources with richer instrumentation is required
  to establish how many actual state identities were conflated.

The five theorems affected by visible elision and all flagged input groups are
listed in the [machine-readable audit](../results/state-identity-audit-v1/summary.json).
The audit assigns **26,820 separate provenance-based record IDs** and attaches an
explicit vector reference to each. It does not call the 3,659 text hashes
mathematical state IDs. These records are in `state-records.json.gz`; all text
groups and their memberships are in `input-groups.json.gz`.

## What survives, and what does not follow

Every text hash matches its stored text; all vector chunk hashes pass. There are
3,659 distinct stored coordinate arrays. Expanding their references into 26,820
coordinate copies gives **exactly the same generating set for every archived
object**. Thus coordinate caching itself did not shrink a hull or average
states. The physical storage optimization is sound for the fixed text encoder.

The semantic premise is not established. The current geometry measures **encoded
printed local-goal displays**. It cannot yet be interpreted as a verified geometry
of complete mathematical proof states.

All 32,384 sole-point-contact certificates refer to the shared empty-active-goals
input. Their coordinate arithmetic remains valid, but their contact cannot be
interpreted as evidence of shared mathematical content. No states were removed to
change those results.

The single additional shared input is:

```text
a b c : ℝ
⊢ 0 ≤ (a - b) ^ 2 + (b - c) ^ 2 + (c - a) ^ 2
```

Its six observations come from three proof records across two theorem IDs, in
the same Lean4.9 replay environment. Source inspection confirms that all three
introduce this same local algebraic claim with `have ... := by nlinarith`, while
the enclosing theorem goals differ. It is a plausible genuine shared *local*
obligation. It is not an identical complete proof state. The complete source
comparison is archived in `shared-local-goal-sources.json`.

## Required correction before treating a larger acquisition as semantic evidence

Keep the readable display and encoder-input cache, but separate them from state
identity. Each recorded state must retain its own provenance and a structured
snapshot of its goal expressions, local declarations and values, metavariable
context, active and suspended goals, and relevant environment identity. Qualified
constant names alone are insufficient across versions unless the definitions
they resolve to are also pinned. The distinction between a local obligation and
the whole proof state must be explicit.

Equality of printer output must not assert semantic equality. Even structural
snapshot equality and mathematical equivalence are separate questions: different
internal expressions can be equivalent, and equivalent displays can conceal
different expressions. Exact caching of a complete serialized input remains a
storage mechanism, with all record associations preserved.

The next extractor must pass counterexamples for hidden namespaces/definitions,
hidden local values or terms, and focused/suspended goals before reusing text
identity as evidence. This audit does **not** claim that the extractor has already
been replaced or that existing vectors can recover information never supplied
to the encoder. No change in the number of coordinate copies fixes that omission.
