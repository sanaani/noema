# Phase 9 — rarity by what a lemma says, not how often it is named

**Pre-registration.** Everything in this file is written and committed before
any Phase 9 score is computed. Results go in a section appended below; nothing
above that section changes.

## Why

Phase 8 called a lemma rare if 2024 Mathlib names it 10 times or fewer. Its
rare bridges then ran through `four_ne_zero`, `div_le_iff₀` and `tsub_tsub`:
common facts under rarely used names (`div_le_iff₀` had just replaced
`div_le_iff`, 72 citations; `four_ne_zero` has 1 against `two_ne_zero`'s 187).
The README's first guess, that tactics hide these citations, was wrong: the
dependency graph reads whole proof terms. The fix is the same either way.
Rarity has to come from what a statement *says*.

## The measure

`scripts/specialisation.py`, fixed before this file was committed. A
statement's concepts are the identifiers and non-ASCII symbols of its goal and
non-instance hypothesis types, minus its binder names. Instance hypotheses
(`inst✝ : CommMagma G`) are dropped: they say how general a statement is, not
what it is about. **Specialisation** is the mean of the three largest
log(N / df) over its concepts, df counting Phase 6's 206,845 2024 statements
that mention the concept.

Checked by hand before this file, on names chosen to test it: `mul_comm`,
`tsub_tsub` 0; `Nat.cast_one` 1.84; `four_ne_zero` 3.16 (bottom 4%);
`Finset.sum_congr` 4.09; `IsCoprime.pow` 4.53; `ModularForm.SL_slash` 7.22;
`UpperHalfPlane.mdifferentiable_coe` 8.12 (top 30%). A first version that kept
instance hypotheses put `mul_comm` in the top 10% and was discarded.

## Definitions

As Phase 8, with rarity replaced:

- **Specialised lemma**: specialisation above the 2024 median (6.54).
- **Specialised pair**: an eligible cross-area pair, both ends specialised,
  not cited together by any 2024 theorem.
- **Specialised bridge**: a Phase 5 bridge joining at least one specialised
  pair. **Ordinary bridge**: every other bridge.

**Counts, seen before this file** (labels only, no score): 94 specialised
bridges and 3,746 ordinary; 184 corpus lemmas are an end of a specialised pair
joined by 2026. At the 75th percentile there would be 13 bridges, too few, so
the median was chosen. Nothing else was tried.

That count is itself the first finding: **only 2.4% of new cross-area
theorems join two specialised lemmas.** Almost every bridge has an everyday
lemma at one end.

## Tests

Scores M (mixing) and S (sparsity), k = 50, exactly as Phase 8.
Bootstrap, verdict rows and Holm as Phase 8. Seed **20260929**.

- **A1 (primary)**: AUC(M) at the connector's 2026 statement, specialised
  bridges vs within-area. With 94 positives, the interval will be wide.
  Prediction: real but weak.
- **A2**: AUC(M), AUC(S), specialised vs ordinary bridges, Holm across two.
  Prediction: S passes.
- **B1, B2**: AUC(M), AUC(S) at each specialised corpus lemma's own 2024
  position (population: specialised lemmas present in 2026; positives: ends of
  a joined specialised pair), Holm across two. Prediction: S passes.

### Reported, not tested

- A lemma's specialisation itself as a score in B, and a lemma's 2024
  citation count, and M and S within citation strata (0, 1–2, 3–10, 11+).
- Word mixing M_V on A1.
- All 94 specialised bridges with their pairs, in full, so a reader can judge
  them.

## Out of scope

As Phase 8. The Navier–Stokes test uses Part B's map only if B1 or B2 passes.

---
