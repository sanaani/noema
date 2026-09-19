# Candidate investigation: all 30 hidden-connection pairs

Pairs 7–8 (arctan/oangle) already yielded the verified bridge
(`results/bridge-conjecture-v1/`). The remaining 28 were investigated in four
batches against pinned-Mathlib (`f0957a75`) statements and `edges.jsonl.gz`
dep overlaps. Counts below cover the 28.

## Tally

- NOISE 12 · GENRE 9 · TOPICAL 4 · BRIDGEABLE 3 (pairs 14 + 15 are one idea)

## How spurious results occur (taxonomy)

1. **Sibling duplication** — primed/unprimed, add/sub, auxbound1/2 twins of the
   same lemma each match independently (pairs 0/1, 3/4, 11/12, 14/15). 8 of 28
   rows collapse to 4 ideas. Fix: dedupe by dep-set overlap before ranking.
2. **Genre resemblance** (9) — same proof flavor, generic deps only:
   closure/approximation (10), abs-estimates (17), integrability-via-domination
   (26), sum/factorial manipulation (19), closed-form integer evaluation (13),
   rewrite-lemma shape (28), kernel/multiplier smoothness (29), splitting
   identities (3, 4). The head matches "analysis proof shaped like X".
3. **Pure noise** (12) — no discernible relation; scores 0.63–0.64 sit just
   above background. Magnets: tiny numeric-fact theorems (`gold_irrational`
   twice, eulerMascheroni bounds) with short generic S-exprs, and giant
   integral statements sharing operator soup.
4. **Topical threads** (4) — shared on-topic lemma, no composition: `conj_I`
   conjugation machinery (0, 1), statement-level `Real.pi` (18), `Real.exp`
   parametrization (22). Real common subject matter, but nothing new follows.

## New ideas

- **Pairs 14/15 (strong)**: `cosKernel_def` states the kernel as a theta value
  via `re`; the n=2 polarization identity rewrites `re` as a normSq
  difference, giving `↑(cosKernel ↑a x) = (normSq(1+θ) − normSq(1−θ))/4`.
  Same cluster and same proof pattern as the verified arctan bridge.
  Next step: machine-check in Lean.
- **Pair 27 (weak)**: tan-continuity-from-nonvanishing composed with the
  Eisenstein denominator lower bound gives summand continuity — but this is
  likely already the file's internal plumbing. Verify novelty before claiming.
- **Pairs 0/1 (negative result)**: generalizing polarization to `μₙ` is real
  mathematics but makes the sinKernel route strictly longer; the theta content
  is untouched. Investigation artifact kept unverified at
  `results/bridge-conjecture-v1/UNVERIFIED-polarization-over-roots.lean`.

## Lesson

The head reliably finds *shared proof machinery* (verified: 61→13 transfer on
held-out families), but shared machinery ≠ composable statements. The
arctan-style hit needs the extra shape: one side equates X to f(...), the
other constrains f. Only 2 of 30 rows had it.
