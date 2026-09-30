# Phase 21 — forecasting important jumps, with "far" set by real jumps

**Pre-registration.** Everything in this file is written and committed before
any Phase 21 score is computed. Results go in a section appended below;
nothing above that section changes.

## Why

Phase 20 asked whether content similarity can point at important jumps before
they happen, and could not answer: it called a pair "far" only if it was in the
most distant 10% of all possible pairs (about 7 bits), and pairs that far
almost never meet (5 important jumps).

The sizing count (`sizing/README.md`) fixed two things before any score:

- **Far** is now set by where real jumps land: span ≥ **5.84 bits**, the
  start of the top 1% of arrivals that actually happened (Phase 18, learn
  window). At the 2005 cutoff that gives **229** important jumps among
  146,938 unconnected pairs.
- **Outcomes must end by 2021.** Reference coverage in the data collapses
  after 2021 (79% of 2022 papers have no references, 95% of 2025 papers), so
  Phase 20's 2015 and 2025 cutoffs cannot be used.

Already seen before this file was written: all results of Phases 11–20, and
the sizing counts (pairs, crossed pairs and important jumps at cutoffs 2005 and
2015, by span threshold). No similarity value and no model score has been
computed for these pairs at any threshold used here.

## Data

As Phase 20: Phase 11's arXiv math papers and OpenAlex references, arXiv
primary category as the area (28 areas), `W4285719527` dropped.

## Three cutoffs

Everything at cutoff H is computed from papers up to H only: the co-citation
table, the text model (TF-IDF, Phase 11 settings, + 256-dimension truncated
SVD), spans, similarities, candidate pairs.

| cutoff H | role | outcome years |
|---|---|---|
| **2005** | train, and test by cross-validation | 2006–2015 |
| **2011** | forward test of the model trained at 2005 | 2012–2021 |
| **2021** | forecast list, no outcome | — |

The outcome window is 10 years (Phase 18's measured catch-on time).

## Pairs, features, outcome

Unchanged from Phase 20, except "far":

- **Candidate pair (W, A)**: W has at least 5 citers up to H; no paper whose
  primary area is A cites W up to H.
- **Span**: −log₂ Σ_B s(B) F[A | B], s = W's citers' areas up to H, F the
  co-citation table up to H.
- **Far**: span ≥ **5.84 bits**, the same number at every cutoff.
- **Similarity**: cosine between the mean text vector of W's citers up to H
  and the mean text vector of A's papers in the last 5 years up to H.
- **Controls**: log(1 + citers up to H), log(1 + citers in the last 5 years),
  log(1 + A's papers in the last 5 years).
- **Important jump** (positive): a far pair that at least **5** A-papers cite
  in the 10 outcome years.

## Models

Logistic regression, as Phase 20:

- **BASE**: the three controls and span;
- **BASE+SIM**: BASE plus similarity.

Features are standardised within each cutoff's far population. Seed
**20261011**. Intervals: 95%, from 1,000 bootstrap draws resampling works.

## Tests

Both tests use AUC(BASE+SIM) − AUC(BASE) and this table:

| outcome | verdict |
|---|---|
| interval above 0, difference ≥ 0.03 | **similarity forecasts important jumps** |
| interval above 0, difference < 0.03 | **detectable, small** |
| interval contains 0 | **no measurable help** |
| interval below 0 | **similarity hurts** |

Fewer than 100 important jumps: **underpowered**.

### H1 (primary) — at 2005, does similarity forecast important jumps?

5-fold cross-validation grouped by work (Phase 13's code) on the 2005 far
population. Prediction: similarity forecasts important jumps.

### H2 — does the 2005 model work on pairs it has never seen?

Both models are trained on the whole 2005 far population and applied unchanged
to far pairs at 2011 (outcome 2012–2021).

- **Population**: pairs whose work is **new since 2005** (fewer than 5 citers
  up to 2005, so the work is in no training pair). If these hold fewer than
  100 important jumps, H2 is scored on all far pairs at 2011 instead. The
  choice uses counts only. Both populations are reported either way.
- **Known limit, stated in advance**: the training labels use citations from
  2006–2015, which overlaps the forward test's years. On new works no pair is
  shared with training; only the model's six coefficients carry over. On all
  works, a pair still unconnected in 2011 can be in both sets.
- Coverage is lower in 2015–2021 (32–46% of papers have no references) than
  before 2012 (about 20%), so forward outcomes are undercounted.

Prediction: detectable, small.

### Reported, not tested

- Candidate pairs, far pairs, crossed pairs and important jumps at each
  cutoff.
- Important jumps in the top 100 and top 1,000 under BASE, BASE+SIM and
  similarity alone, against chance, for H1 (out-of-fold) and H2.
- **A wider "far"**: H1 repeated at span ≥ 4.65 bits (top 10% of real
  arrivals, 888 important jumps in the sizing count).
- **The 2011 top 50** under BASE+SIM in the H2 population, with outcomes.
- **Landmark check** at 2011 for (Zagier's *Elliptic Modular Forms*
  W116915404, metric geometry), (Diamond–Shurman W1537136047, metric
  geometry) and (Fisk's interlacing note W2156858248, combinatorics): whether
  unconnected, span, whether far, the pair's similarity percentile among all
  candidate pairs, papers citing it in 2012–2021, and its rank if far.
- **The 2021 forecast list**: the top 50 far, unconnected pairs at 2021 under
  BASE+SIM trained at 2005. Forecasts only. As a rough early look, the share
  of the top 50 and top 1,000 already cited by at least one area paper dated
  2022 or later, against the share among all far pairs (all undercounted
  alike).

Titles of works that are not arXiv papers are looked up from OpenAlex after
the run.

## Out of scope

- Any other cutoff, window, threshold or feature. Anything the results
  suggest is reported as exploratory in its own section.

## Run and budget

One AWS m6i.4xlarge, self-terminating, idle-log watchdog, 2-hour power-off;
smoke pass first (every 4th paper, catch-on lowered to 1 paper). Estimated
20–40 minutes, under $1. Teardown verified.
