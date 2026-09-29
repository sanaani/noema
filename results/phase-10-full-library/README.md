# Phase 10 — rare jumps across all of Mathlib

**Pre-registration.** Everything in this file is written and committed before
any Phase 10 score is computed. Results go in a section appended below; nothing
above that section changes.

## Why

Phases 8 and 9 found no sign that the 2024 map knows which lemmas will become
ends of a rare cross-area jump. Phase 9 had only 184 such lemmas, because it
used Phase 3's 24,916-theorem sample, about 12% of Mathlib. Across the whole
library, 2024 → 2026 has about 4,800 new theorems joining two specialised
lemmas from different areas, and about 5,300 lemmas at their ends (counted
before this file; no score was computed). Phase 10 asks Phase 9's Part B on
the whole library. If the map still fails with that many positives, the
problem is the map, not the amount of data.

## Definitions

- **The map**: encoder B's vectors of all 206,845 2024 statements (Phase 6).
  A lemma's **area** is the second component of its 2024 module.
- **Specialised**: Phase 9's measure (`scripts/specialisation.py`) above its
  median over the 206,845 statements.
- **Citations**: the number of 2024 theorems whose proof term uses the lemma.
- **New 2026 theorem**: in the 2026 graph (`09712d48`) and not in the 2024
  graph (`f0957a7`), excluding compiler-generated `.proof_N` names.
- **Specialised pair**: two specialised 2024 lemmas in different areas that no
  2024 theorem uses together.
- **Population**: specialised 2024 lemmas with a known area, present by name
  in the 2026 graph.
- **Positive**: an end of a specialised pair that some new 2026 theorem uses
  together.

Phase 3's "eligible" rule (no shared rare lemma) is dropped: it was defined on
the sample only.

## Scores

At each lemma's own 2024 position, over the 50 nearest *other* 2024
statements by cosine (k = 50, as in Phases 5–9):

- **M, mixing**: 1 − (count of the most common area among the 50) / 50.
- **S, sparsity**: 1 − the mean cosine to the 50.

## Tests

B1: AUC of M. B2: AUC of S. Positives against the rest of the population.
95% intervals from 2,000 bootstrap draws resampling lemmas by 2024 module.
One-sided p (share of draws at or below 0.5), Holm at 0.05 across the two.
Seed **20261001**.

With thousands of positives, a trivially small effect can pass. So:

| outcome | verdict |
|---|---|
| passes Holm, AUC ≥ 0.55 | **the 2024 map marks where rare jumps will start** |
| passes Holm, AUC < 0.55 | **detectable, too small to guide a search** |
| interval contains 0.5 | **no measurable difference** |
| interval below 0.5 | **rare jumps sit on the other side** |

Predictions: both no measurable difference, or detectable but too small.

### Reported, not tested

- Citation count and specialisation, each as a score.
- M and S within citation strata (0, 1–2, 3–10, 11–50, 51+), and their
  stratum-weighted mean AUC: whether the map adds anything once popularity is
  held fixed.
- The 25 positives with the highest S, and the areas holding the most
  positives against their share of the population.

## Run

`scripts/run-phase10.py` on one AWS CPU worker (m6i.4xlarge, 64 GB),
smoke pass first, self-terminating. Estimated under an hour and under $3;
ceiling $10. Role, instance profile, security group, instance and task object
torn down and the teardown verified.

## Out of scope

Part A of Phases 8–9 (scores at the new theorem's own statement), because the
2026 statements outside the sample were never encoded. Any second threshold,
k or score. The Navier–Stokes test.

---

## Results

*Appended after the run. Nothing above this line changed.* Numbers from
`results/phase10.json`, one m6i.4xlarge run (smoke pass, then about 4
minutes). A first launch failed before any instance started (disk set below
the image's 75 GB snapshot) and was torn down; the rerun used 100 GB.

**Counts.** 4,793 new 2026 theorems join 17,598 specialised pairs.
Population 65,848 specialised lemmas; **5,253 positives**, 29× Phase 9's.

| test | prediction | result | verdict |
|---|---|---|---|
| **B1** AUC(M) | no difference, or too small | **0.542** [0.527, 0.558] | **detectable, too small to guide a search** |
| **B2** AUC(S) | no difference, or too small | **0.464** [0.448, 0.480] | **rare jumps sit on the other side** |

With enough data the map's signal is measurable, and it is small. Lemmas
whose map neighbourhood mixes several areas are slightly likelier to become
the end of a rare jump (0.542). Sparsity reverses Phase 5's direction:
future jump ends sit in slightly *denser* parts of the map (0.464).

### Reported, not tested

- **Citation count: 0.710** [0.699, 0.721]. Popularity wins again, now
  within the specialised half of Mathlib.
- **Specialisation: 0.401.** The most specialised lemmas are the *least*
  likely to become jump ends. Rare jumps run through moderately specialised
  lemmas, not the most esoteric ones.
- **M holds within popularity.** Within citation strata M scores 0.547–0.618,
  stratum-weighted 0.560, rising with citations; S sits at 0.46–0.50
  except the 171 most cited lemmas. The mixing signal is not a proxy for
  popularity. It is small.
- **Areas.** RingTheory holds 14.7% of positives against 5.8% of the
  population; LinearAlgebra and NumberTheory are also over-represented.
  CategoryTheory holds 4.0% against 12.3%.

### What this establishes

- The data question is settled: with 5,253 positives, the 2024 map carries a
  real but small signal (mixing, 0.54–0.56 at fixed popularity) about which
  specialised lemmas will start a rare cross-area jump.
- It is far weaker than popularity (0.71), and too small on its own to point
  a search at the right lemmas.

### Teardown

Instance terminated, IAM role, instance profile, security group and task
object deleted; verified.
