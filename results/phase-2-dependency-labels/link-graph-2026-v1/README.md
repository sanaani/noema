# Dependency label v1 — the 2026 answer key from Lean

The forward test's label, rebuilt from Lean's own dependency graph instead of a
text search of the 2026 Mathlib source.

Reproduce from this directory alone — no Mathlib checkout, no GPU:

```bash
.venv/bin/python scripts/analyze-mathlib-forward.py \
    --connectors results/phase-2-dependency-labels/link-graph-2026-v1/new-connectors.json
.venv/bin/python scripts/analyze-forward-independence.py --connectors <same>
.venv/bin/python scripts/analyze-forward-vocabulary.py  --connectors <same>
.venv/bin/python scripts/analyze-forward-area.py        --connectors <same>
```

## Setup

| | |
|---|---|
| model frozen at | Mathlib `f0957a7`, 2024-07-01 |
| answer key from | Mathlib `09712d48`, 2026-09-21 |
| 2024 theorems | 206,889 (`../../phase-1-recognition/link-graph-v1/edges.jsonl.gz`) |
| 2026 theorems | 281,359 (`edges-2026.jsonl.gz`, this directory) |
| new since 2024 | 148,911 |
| connectors (new, cite >= 2 corpus theorems) | 88 |
| distinct corpus pairs connected | 145 |
| eligible pairs (no shared rare lemma in 2024) | 1,530,134 |
| **positives among eligible pairs** | **53** |

Both edge lists come from the same elaborator over the same definition of
"depends on", so the two graphs are directly comparable. A *connector* is a
theorem present in 2026, absent in 2024, whose proof term cites at least two
distinct corpus theorems.

## The headline: the effect survives, and it is weaker

| | grep label | dependency label |
|---|---:|---:|
| positives | 17 | **53** |
| **state-geometry angle AUC** | **0.973** | **0.898** |
| proof size alone | 0.509 | 0.439 |
| vocabulary overlap AUC | 0.691 | 0.672 |

The exact label triples the positives and drops the AUC by 0.075. **0.898 on 53
positives is the number to quote**, not 0.973 on 17: the grep label was not a
noisier measurement of the same thing, it was a smaller and differently
selected one. A text search can only find citations written as visible names,
which biases it toward pairs whose connector names them plainly — exactly the
easy cases.

The angle remains far from proof size, which stays near chance in both.

## Band table

| band | pairs | hits | lift |
|---|---:|---:|---:|
| 0-30 | 26 | 0 | 0x |
| 30-45 | 501 | 4 | 231x |
| 45-55 | 2,251 | 4 | 51x |
| 55-65 | 8,441 | 5 | 17x |
| 65-75 | 34,204 | 19 | 16x |
| 75-85 | 182,588 | 10 | 2x |
| 85-95 | 1,300,144 | 11 | 0x |
| 95-180 | 1,979 | 0 | 0x |

## Does it survive the obvious objections?

**Clustering.** 53 positives over 69 distinct endpoints.

| subset | n | AUC |
|---|---:|---:|
| all positives | 53 | 0.898 |
| vertex-disjoint (independent pairs) | 25 | 0.877 |
| drop pairs touching a seed family | 40 | 0.936 |
| drop the `Complex.exp*`/`cos*` hub | 36 | 0.932 |

Leave-one-endpoint-out over 69 endpoints: min 0.886, median 0.897, max 0.934.
No single theorem carries the result — something 17 positives could not have
shown.

Degree-preserving cluster null, 5,000 draws: null AUC 0.501 +/- 0.045 against
observed 0.898, p < 1e-5.

**Is it just a subfield detector?** No.

| subset | pairs | hits | angle AUC |
|---|---:|---:|---:|
| all eligible | 1,530,134 | 53 | 0.898 |
| cross-area only | 1,394,580 | 30 | 0.904 |
| same-area only | 135,554 | 23 | 0.855 |

Cross-area AUC is *higher* than overall. Angle as an area detector scores
0.656; area alone predicts the 2026 link at 0.673. The confound is weak and the
angle keeps its AUC where the confound cannot reach.

**Is it just shared words?** Partly, but not wholly. Vocabulary overlap alone
scores 0.672. 12 of the 53 connected pairs share under 5% of their state
vocabulary.

## What this still does not establish

The corpus is 1,797 theorems, 0.87% of the 2024 library, and it was selected
theorem-by-theorem in phase 1 — a selection effect this phase inherits and
cannot correct. 53 positives is three times 17 and still a small number. The
band lifts above 30-45 rest on single-digit hit counts and should not be quoted
individually; the AUC is the stable statistic.

## Two checks run later, on this same corpus

Both were written for the unseeded corpus and run here for the seeded column of
its comparison table; they read the committed centroids and this label.

* `residual.json` — the angle on the pairs that share no area and under 5% of
  their state vocabulary: **0.928 on 11 positives**, with vocabulary itself at
  0.399 on the same pairs as the control. Vocabulary on all eligible pairs is
  0.672, which agrees with `vocabulary.json`.
* `state-source.json` — 425 of the 1,797 centroids are a single synthetic state
  (the statement; the proof ran no tactic). Angle AUC on observed-observed
  pairs 0.848 (25 positives), observed-synthetic 0.965 (23),
  synthetic-synthetic 0.878 (5). Too few positives to say whether proof states
  add to the statement; the unseeded corpus answers that.

## What it settles for planning

The label gain over the grep label is now measured rather than assumed:
**R = 53/17 = 3.1**, against the pessimistic R = 2 used for planning. At that
rate 1,000 positives needs about 7,800 corpus theorems, roughly 156 randomly
sampled files, rather than 195. See `scripts/size-corpus.py --ratio 3.12`.
