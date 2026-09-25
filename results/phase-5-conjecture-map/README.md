# Phase 5 — does the 2024 map know where bridging theorems land?

**Pre-registration.** Everything in this file was written and committed before
a single 2026 statement was printed or encoded. Results go in a section
appended below; nothing above that section changes.

## Why

Every connection the project has counted exists because someone later wrote a
theorem that uses both ends. Phases 1–4 ranked the *pairs*. The goal behind
them is conjecture: telling a mathematician, or a model that writes candidate
statements, *where* a new theorem would be worth stating. That is a question
about locations in the map, not about pairs.

Phase 4 made it askable. Its encoder B, trained on 2024 Mathlib only, reads a
theorem's statement at least as well as its proof states, so a theorem can be
placed on the map before it has a proof. Phase 1's betweenness test hinted at
the geometry: known bridge theorems sat between their two ends (6/6 families
in the top 4.3%), on a hand-picked corpus.

Phase 5 asks whether, knowing only the 2024 map, you can tell a spot where a
new theorem will connect *different areas* from a spot where it will connect
within one. If you cannot, the map is not a guide for conjecture, whatever it
does for pairs.

## The map

Phase 3's 24,916 corpus theorems, each placed by B on its **2024 statement**:
an observed theorem by B's vector of its initial goal (`statements.npz`), a
statement-only theorem by B's vector of its single state, which is that same
initial goal. Each carries its 2024 Mathlib area (second component of its
module). Nothing from 2026 enters the map.

## The new theorems

A **connector** is a theorem new in the 2026 graph that cites at least two
corpus theorems (10,368, `new-connectors.json`, phase 3). Its position is B's
vector of its **2026 statement**, printed from Mathlib `09712d48` by
`Statements2026.lean` — phase 1's `InitialGoals.lean` ported to Lean
`v4.35.0-rc2`, same rendering — and encoded by B exactly as B encoded its
training texts (same tokenizer, first 512 tokens, mean-pooled, normalised).

Connectors are classed from the phase 3 label alone, before any statement is
printed:

| class | rule | count |
|---|---|---:|
| **bridge** (positive) | joins at least one eligible cross-area pair | 3,840 |
| **within-area** (negative) | joins eligible pairs, all same-area | 5,358 |
| hard bridge | joins at least one hard-subset pair (cross-area, vocabulary < 5%) | 743 |
| excluded | joins no eligible pair | 1,170 |

"Eligible", "cross-area" and "hard subset" are phase 3's definitions.
Connectors whose statement fails to print or encode are dropped and counted.

## The scores

All computed at a connector's position, from the map alone.

- **Mixing, M** (primary): the 50 corpus theorems nearest by cosine;
  `M = 1 − (count of their most common area) / 50`. High where the map's
  neighbourhood is split between areas.
- **Lexical mixing, M_V** (control): the same, with the 50 nearest by Jaccard
  of identifier sets — the tokenizer of `analyze-forward-vocabulary.py`
  applied to the connector's 2026 statement and each corpus theorem's 2024
  statement text; ties broken by corpus order. It asks whether plain word
  overlap finds the same neighbourhoods.
- **Density, D** (reported): mean cosine to the 50 nearest.

k = 50 is fixed; no other k is scored.

## Hypotheses and what each outcome means

Intervals are 95%, from 2,000 bootstrap draws that resample connectors by
their 2026 source file, so theorems written together move together.

### H1 (primary) — does mixing mark bridge spots?

AUC of M, bridges against within-area connectors.

| outcome | verdict |
|---|---|
| AUC ≥ 0.60, interval above 0.5 | **the map locates bridge spots** |
| interval above 0.5, AUC < 0.60 | **real but weak** |
| interval contains 0.5 | **not supported** |
| interval below 0.5 | **contradicted** |

Prediction: real but weak, AUC 0.53–0.60.

### H2 — is it the geometry or the words?

AUC(M) − AUC(M_V), same connectors, paired bootstrap. Interval above 0: the
geometry places bridge spots beyond what word overlap does. Contains 0: no
measurable difference. Below 0: words do better. Prediction: no measurable
difference.

### H3 — the hard version

H1's test with hard bridges (743) as the positives, same negatives, same
verdict rows. Prediction: weaker than H1.

### Reported, not tested

- **Does new mathematics land near the map at all?** AUC of D, connectors
  against 10,000 new 2026 theorems that cite no corpus theorem, drawn once
  (seed 20260927, compiler-generated `.proof_N` names excluded), printed and
  encoded the same way.
- **Citation count.** A connector citing more corpus theorems has more chances
  to join a cross-area pair. AUC of that count alone on H1's labels, and H1
  within count strata (2, 3–5, 6 or more).
- **Printer drift.** Lean's pretty-printer changed between the two versions
  (`s₁.entries ~ s₂.entries` in 2024 prints as `s₁.entries.Perm s₂.entries`
  in 2026). For the 21,073 corpus theorems that keep their name in 2026, the
  2026 statement is printed too: the median angle between each theorem's two
  B vectors, and H1 rerun with the map rebuilt from 2026 printings (surviving
  theorems only). Drift adds the same noise to bridges and non-bridges, so it
  can lower power but not manufacture a difference.
- H1's labels by decile of M, and the ten highest-M bridges with the pairs
  they join.

## What is out of scope

- **Generating statements.** This tests the map, not a writer or a prover.
- **ReProver.** Only B, the encoder phase 4 found best.
- **Any second k, any second score.** Anything suggested by the results is
  reported as exploratory in its own section.

## Budget

One CPU worker (m6i.4xlarge), self-terminating: fetch Mathlib `09712d48`
with its prebuilt oleans, print ~41,000 statements. Encoding with B runs
locally on CPU. Estimated $1–2, ceiling $10. The role, security group,
instance and task object are torn down and the teardown verified.

---

## Results

*Appended after the run. Nothing above this line changed.* Numbers from
`results/phase5.json`, written by `scripts/analyze-phase5.py`. Statements were
printed by one m6i.4xlarge worker (41,441 printed, 0 missing) and encoded
locally on CPU by `scripts/encode-b.py`. As a check, CPU re-encodes of 2,000 of
B's own training texts sit at median 0.16°, max 0.25°, from the GPU vectors.
All 10,368 connectors were encoded and none were dropped.

### Verdicts

| test | pre-registered prediction | result | verdict |
|---|---|---|---|
| **H1** AUC(M), 3,840 bridges vs 5,358 within | real but weak, 0.53–0.60 | **0.568** [0.545, 0.590] | **real but weak** |
| **H2** AUC(M) − AUC(M_V), paired | no measurable difference | **−0.022** [−0.037, −0.008] | **words do better** |
| **H3** AUC(M), 743 hard bridges vs 5,358 within | weaker than H1 | **0.581** [0.548, 0.614] | **real but weak** |

**H1 passed as predicted.** The 2024 map tells a future cross-area spot
from a future within-area spot a little better than a coin flip, and the
interval clears 0.5.

**H2 went against the prediction.** Mixing measured by plain word overlap
(M_V 0.590 [0.567, 0.613]) beats mixing measured by B's geometry, and the
paired interval stays below zero. On this question B's map adds nothing
beyond the words. It does slightly worse.

**H3 was not weaker.** Hard bridges score 0.581 against H1's 0.568. The
intervals overlap, so "weaker" is wrong but "stronger" is not shown either.

### Reported, not tested

- **Citation count beats the map.** How many corpus theorems a connector
  cites predicts "bridge" at AUC **0.689** [0.674, 0.703] on its own, well
  above M. Within count strata M still separates: 2 cited 0.533 (1,311 vs
  3,472), 3–5 cited 0.602 (1,891 vs 1,740), 6 or more 0.606 (638 vs 146). So
  M is not only a proxy for count, but most of the easy signal is count.
- **Density.** On H1's labels, D scores **0.394** [0.372, 0.416]: bridges
  land in *sparser* parts of the map than within-area connectors do. New
  theorems that cite the corpus sit only slightly nearer the map than new
  theorems that don't (AUC of D 0.534, 10,368 vs 10,000).
- **Printer drift.** Across the 21,073 surviving corpus theorems, a theorem's
  2024 and 2026 printings sit at a median of 0.19° apart. The tail is long:
  the 90th percentile is 22.6°. With the map rebuilt from 2026 printings, H1
  rises to **0.600**. That point estimate has no interval, and the map it
  uses has survivors only. This fits drift costing power, as the pre-registration
  expected. It is not a re-test of H1.
- **Bridge share by M** (8 bins of roughly equal size, from low M to high): 0.318, 0.403,
  0.415, 0.486, 0.484, 0.479, 0.481, 0.438. Nearly all of the rise sits in the first
  bin, where the neighbourhood is almost all one area. Above M ≈ 0.2 the
  share is flat, and it dips in the top bin.
- **Top-M bridges.** Several of the ten highest-M bridges qualify through
  generic lemmas: `Category.comp_id`, `Nat.cast_one`/`Nat.cast_zero`,
  `Finset.sum_congr`, `Complex.continuous_re`. They are cross-area by the
  area label, but they are not the kind of bridge a mathematician would call
  a discovery. The full list is in `phase5.json`.

### What this establishes

- The 2024 map carries a small, real signal about where cross-area theorems
  will appear (H1, H3).
- It does **not** beat word overlap at this (H2). The signal is available
  without the encoder.
- Citation count, which is known only after the theorem exists, is a
  stronger predictor than either. A conjecture tool cannot use it.

### What it does not establish

- Whether a different score (another k, a learned placement) would beat
  words. Only M, M_V and D at k = 50 were scored, as pre-registered.
- Whether the flat region above M ≈ 0.2 is a ceiling of the map or of the
  area label, which is coarse (28 areas) and counts generic lemmas as
  bridges.

### Hands to phase 6

Placement by nearest-neighbour mixing is weak and loses to words. Phase 6
(`docs/phase-6-jepa-plan.md`) asks the sharper question directly. It trains a
predictor, on top of a frozen B, to place a theorem's statement from the lemmas
it cites. Word-overlap placement is the baseline it has to beat.

### Cost and teardown

One m6i.4xlarge worker for the printing, self-terminating. The instance,
its IAM role and instance profile, the security group and the task object
were deleted, and the deletion was verified. The bucket is kept, as before.
