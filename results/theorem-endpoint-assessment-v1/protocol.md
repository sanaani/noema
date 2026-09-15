# Final trajectory dot as a theorem-specific center: assessment protocol

Question: can the last local State/transition of an arbitrary valid proof provide a
proof-independent and theorem-specific center for the proposed State density object?
The user requires a clear assessment, not an arbitrary statement/centroid substitute.

Test a controlled information-loss counterexample before treating missing Dartmouth
weights as a blocker. For a proved target T with proof p and a proved auxiliary
obligation G with proof q, a valid proof may reduce T to G using `suffices h : G by
exact p`, then close G with q. Test multiple distinct closed theorem targets and
multiple auxiliary goals in Lean 4.9. Use identical auxiliary-variable names and
closing tactics within each column, and capture all active goals/local declarations.
No contradictory hypotheses, sorry, unproved axioms, or unproved target declarations.

The matrix crosses four targets (addition commutativity, multiplication commutativity,
conjunction commutativity, and reflexivity of natural-number order) with four
auxiliary goals (True, 0 = 0, universal equality reflexivity, and True ∧ True).
Each wrapper is a controlled proof variant, not an observation about its frequency
in the archived corpus. Use compiler-checked declarations and print all axiom lists.
Require every observed closing step to have one goal before and zero afterward.

If different target theorems have identical final (before, tactic, after) inputs,
any deterministic encoder restricted to those local inputs must assign them the
same endpoint for every possible fixed checkpoint. This is a mathematical input
identity argument, not a numeric execution of Dartmouth. A global proof-context
encoder would not be covered by the argument.

Separate assessments:
- Existence of a vector for a theorem: possible in principle, not under dispute.
- A unique/faithful center determined by the last local transition for all proofs:
  assessed by the counterexample.
- Average usefulness of endpoints for a restricted corpus, or a whole-proof/theorem
  encoder preserving mathematical relationships: not decided by a constructed collision.

Do not train an encoder, alter existing state objects, contact authors, or acquire
paid compute to evaluate a property that can be disproved at the input level.
