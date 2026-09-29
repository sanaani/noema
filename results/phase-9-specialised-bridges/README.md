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

## Results

*Appended after the run. Nothing above this line changed.* Numbers from
`results/phase9.json` (`scripts/analyze-phase9.py`), laptop CPU, no AWS.
Counts as expected: 94 specialised bridges, 3,746 ordinary, 5,358 within-area;
Part B 9,765 specialised lemmas present in 2026, 184 positives.

### Verdicts

| test | prediction | result | verdict |
|---|---|---|---|
| **A1** AUC(M), specialised bridges vs within-area | real but weak | 0.552 [0.480, 0.619] | **not supported** |
| **A2** AUC(M), specialised vs ordinary bridges | — | 0.486 [0.415, 0.555], p = 0.65 | **no measurable difference** |
| **A2** AUC(S) | passes | 0.525 [0.453, 0.594], p = 0.25 | **no measurable difference** |
| **B1** AUC(M), future jump lemmas | — | 0.532 [0.469, 0.600], p = 0.17 | **no measurable difference** |
| **B2** AUC(S) | passes | 0.503 [0.431, 0.576], p = 0.44 | **no measurable difference** |

Every test failed. With 94 and 184 positives the intervals are wide (about
±0.07), so small effects cannot be ruled out, but none of the pre-registered
predictions held.

### Reported, not tested

- **Sparsity on A1: 0.628** [0.558, 0.696]. Specialised bridges land in
  emptier parts of the map than within-area theorems, as in Phases 5 and 8.
  A2 shows ordinary bridges do too.
- **Popularity wins again.** Connector citation count: 0.828 on A1. In Part B,
  a specialised lemma's 2024 citation count scores 0.712 [0.663, 0.757].
- **Specialisation itself scores 0.417** [0.367, 0.469] in Part B: among
  specialised lemmas, the *less* specialised ones become jump ends more often.
- Within citation strata, B's M and S sit at 0.44–0.57.
- Word mixing on A1 0.548; M − M_V +0.004 [−0.038, +0.044].

### Exploratory

- **The label is better, not clean.** The 94 specialised bridges
  (`all_specialised_bridges_by_S`) read as real cross-area work much more
  often than Phase 8's list: Eisenstein series and the slash action, Galois
  theory with filter bases, Kruskal–Katona, Riesz content, number-field
  ramification. But `even_two_mul`, `Nat.mono_cast` and `Nat.factorial_two`
  still pass as specialised. Rare notation (`n !`) and rare simple
  predicates (`Even`) carry a high IDF.
- **Rare jumps cluster in a few active projects.** Modular forms and the upper
  half plane account for about a third of the top 25 by sparsity. Where people
  were building in 2024–26 may predict rare jumps better than any static
  property of the map. Untested.

### What this establishes

- Only 2.4% of new cross-area theorems join two specialised lemmas.
- Neither mixing nor sparsity of the 2024 map predicts where those
  theorems land, or which specialised lemmas they will join.
- Across Phases 5, 7, 8 and 9, how much a lemma is already used beats the
  map every time.

### Hands to the Navier–Stokes test

B1 and B2 did not pass; as pre-registered, the map is not carried to the
Navier–Stokes proof.
