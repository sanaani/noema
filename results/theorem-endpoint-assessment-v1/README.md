# Assessment: can the final trajectory dot locate a theorem?

**NO for the proposed last-local-transition center.** It cannot generally supply
both a proof-independent location and a location that distinguishes theorems.
This conclusion follows from Lean-checked counterexamples and an input-information
argument; it does not depend on obtaining the Dartmouth encoder checkpoint.

This assessment addresses the user's specified center: the last dot of a Dartmouth-
style local proof-step trajectory. It does not reject the possibility of embedding
an entire theorem, completed proof, or a richer State containing the theorem target.
Nor does it establish the empirical frequency of the failure in ordinary proofs.

## What was checked

Lean 4.9 kernel-checked 16 proof variants: four distinct target statements crossed
with four possible final obligations. All 16 completed with no added axioms.
Two additional general-purpose lemmas were kernel-checked without axioms as well.
The exact source, compiler output, source/binary hashes and receipt are preserved.

| Target theorem | Final obligation A | B | C | D |
|---|---|---|---|---|
| Natural-number addition commutes | True | 0 = 0 | ∀ n : Nat, n = n | True ∧ True |
| Natural-number multiplication commutes | True | 0 = 0 | ∀ n : Nat, n = n | True ∧ True |
| P ∧ Q implies Q ∧ P | True | 0 = 0 | ∀ n : Nat, n = n | True ∧ True |
| Every natural number is ≤ itself | True | 0 = 0 | ∀ n : Nat, n = n | True ∧ True |

Each column has exactly identical printed before-state, final tactic, and after-
state inputs across all four target theorems. The before-goal expressions themselves
also match within each column. Every final tactic discharges exactly one active
goal and leaves zero active goals. Every row has an unchanged theorem type across
its four proof variants, checked from the elaborated declaration types.

A concrete pair:

```lean
theorem addition_truth : ∀ a b : Nat, a + b = b + a := by
  suffices h : True by
    exact Nat.add_comm
  exact True.intro

theorem conjunction_truth : ∀ P Q : Prop, ∀ h : P ∧ Q, Q ∧ P := by
  suffices h : True by
    exact fun _ _ h => ⟨h.2, h.1⟩
  exact True.intro
```

The proof work that determines which theorem is proved differs. Both final local
steps nevertheless receive precisely:

```text
before: ⊢ True
tactic: exact True.intro
after:  no goals
```

These wrappers are intentionally controlled variants, not a claim that human
mathematicians usually write proofs this way. Their purpose is to test whether
an arbitrary valid proof's endpoint intrinsically identifies its theorem. The
user's inclusion objective covers all proofs, not a restricted canonical style.

## Why this is decisive without the trained model

Dartmouth sections 4.5 and 4.7 describe local before/after edit representations,
pooled with typed edit indicators; the default pooled step representation excludes
the tactic token. Our counterexample is stronger than necessary because even the
final tactic matches across target theorems. Identical local model inputs force
identical outputs for any fixed deterministic checkpoint:
https://aclanthology.org/2026.acl-srw.105.pdf

No encoder can reconstruct which target produced the identical local input from
that input alone. Better weights, larger vectors, different projections, or more
GPU compute cannot restore information that the input omits. A stochastic encoder
would produce the same conditional output distribution, not theorem identity.

More generally, given proofs p : T and q : G, the term `(fun (_ : G) => p) q`
proves T. Its tactic counterpart can discharge G last. The final obligation can
therefore be changed without changing the target theorem. The auxiliary goal is
not a theorem-invariant endpoint definition.

If an endpoint encoder must assign a fixed center c(T) to every proof of T, then
all allowed auxiliary endings for T must agree with c(T). But the same ending is
available for every proved target U. Therefore c(T) = c(U). Exact invariance over
this family forces collapse of all those theorem centers. The generic equality
argument is formalized by `invariant_endpoint_centers_collapse`; the proof wrapper
is formalized by `auxiliary_goal_wrapper`.

For approximate invariance, a common endpoint z within epsilon of each of two
centers implies their separation is at most 2 epsilon by the triangle inequality.
Thus no uniformly separated theorem centers with smaller endpoint error can be
recovered from these common final inputs. No arbitrary numeric closeness threshold
is needed to expose this ambiguity.

We do NOT assert that different columns produce different numeric embeddings;
without running the model, distinct inputs may also map to the same vector. The
negative conclusion needs only identical inputs across different theorem targets.

## Full formal State versus printed local input

The capture preserves the entire local declaration list, including implementation-
detail entries hidden by the printer. These hidden entries retain theorem-specific
information and differ between targets. They are recorded in `lean-output.log`.
Consequently, we do not claim that the complete Lean contexts are identical.
This reinforces the scope: the collision concerns the published printed-local-step
representation and our current printed-State encoder. A representation consuming
the full theorem result or proof history is a different construction.

The four targets are structurally distinct statements. We do not claim they are
logically inequivalent: all are proved propositions, and logical equivalence alone
is too coarse to define the intended mathematical geometry.

## Relation to the earlier positive example

The earlier `endpoint-audit-v1` found different scripts for one theorem with
identical final transition inputs. That established existence of a shared endpoint.
It did not establish specificity. This test supplies the missing countercheck:
different theorem targets can have the same endpoint too, and changing auxiliary
proof organization can change a theorem's final transition input.

The missing Dartmouth checkpoint still prevents numerical comparison of distinct
transition inputs and measurement of typical-corpus endpoint clustering. It no
longer prevents a clear assessment of the unrestricted endpoint-center premise.

## Consequence for the State density object

A State density object remains an investigable representation of recorded states.
What fails is identifying its theorem-specific center with the final local
transition. The necessary theorem information must be retained in whatever defines
the reference point. That could be a full-result or context-aware representation,
but its geometric fidelity would need independent validation; this report does
not silently substitute it for the user's endpoint requirement.

No existing theorem objects, vectors, traces or explorer files were changed. No
new encoder was trained, no author contacted, and no paid compute started.

## Reproduction

Compile the fixture and regenerate its verification receipt:

```bash
.venv/bin/python scripts/verify-theorem-endpoint-assessment.py \
  --lean outputs/state-identity-audit-v1/lean-4.9.0-linux/bin/lean
```

Check the saved source/log hashes, matrix, type certificates and axiom receipts
without recompiling (the CI path):

```bash
.venv/bin/python scripts/verify-theorem-endpoint-assessment.py
```

The CI check is a verification of the archived receipt, not a fresh Lean kernel
execution. The local run actually compiles all 18 declarations with the pinned
binary. `verification.json` records which properties were checked and the limits.
