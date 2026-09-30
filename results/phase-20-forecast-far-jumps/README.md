# Phase 20 — forecasting important jumps before they happen

**Pre-registration.** Everything in this file is written and committed before
any Phase 20 number is computed. Results go in a section appended below;
nothing above that section changes.

## Why

Phases 18–19 settled a definition and a predictor:

- An **important jump** is a work reaching an area far from where it has
  been used (far by who-cites-whom) and catching on there.
- Among far reaches, those whose papers are **close in content** to the
  work's existing users are followed more, and the effect grows with distance
  (Phase 19: span × similarity +0.047 [+0.014, +0.082]).

Phases 18–19 scored jumps *after* they happened, using the arriving papers'
text. A useful tool must point at pairs that have **not yet met**. Phase 20
forecasts: using only data up to a cutoff, rank every far, not-yet-connected
(work, area) pair, and check which became important jumps.

Similarity is the predictor, not part of the definition, so the test is not
circular.

Already seen before this file was written: all results of Phases 11–19.

## Data

Phase 11's arXiv math papers (1992–2026) and OpenAlex references, arXiv
primary category as the area (28 areas), `W4285719527` dropped (Phase 19).
2026 is a partial year, so the last full year is **2025**.

## Three cutoffs

Everything at cutoff H is computed from papers up to H only: the co-citation
table, the text model (TF-IDF, Phase 11 settings, + 256-dimension truncated
SVD), spans, similarities, candidate pairs.

| cutoff H | role | outcome years |
|---|---|---|
| **2005** | train, and test by cross-validation | 2006–2015 |
| **2015** | forward test of the model trained at 2005 | 2016–2025 |
| **2025** | live list: forecasts, no outcome yet | — |

The outcome window is 10 years, Phase 18's measured catch-on time.

## Pairs, features, outcome

- **Candidate pair (W, A)**: W has at least 5 citers up to H; no paper whose
  primary area is A cites W up to H (not yet connected).
- **Span**: Phase 18's, −log₂ Σ_B s(B) F[A | B], with s = W's citers' areas
  up to H and F the co-citation table up to H.
- **Similarity**: cosine between the mean text vector of W's citers up to H
  and the mean text vector of A's papers in the last 5 years up to H.
- **Controls**: log(1 + citers up to H), log(1 + citers in the last 5 years),
  log(1 + A's papers in the last 5 years).
- **Important jump** (positive): the pair is far (below) and at least **5**
  A-papers cite W in the 10 outcome years.

## The far population, fixed by counts before any score

Far = the pair's span is in the top X% of candidate pairs at that cutoff.
X is the smallest of **1%, 5%, 10%** at which the 2005 cutoff has at least
**100** important jumps; if none reaches 100, X = 10% and the report says
"underpowered". The same X is used at 2015 and 2025 (threshold recomputed on
each cutoff's candidates). Only counts are used to choose X.

## Models

Logistic regression (standardised features, as Phase 13):

- **BASE**: the three controls and span (distance alone, plus size);
- **BASE+SIM**: BASE plus similarity.

Features are standardised within each cutoff's far population. Seed
**20261010**. Intervals: 95%, from 1,000 bootstrap draws resampling works.

## Tests

### H1 (primary) — at 2005, does similarity forecast important jumps?

5-fold cross-validation grouped by work (Phase 13's code) on the 2005 far
population. AUC(BASE+SIM) − AUC(BASE):

| outcome | verdict |
|---|---|
| interval above 0, difference ≥ 0.03 | **similarity forecasts important jumps** |
| interval above 0, difference < 0.03 | **detectable, small** |
| interval contains 0 | **no measurable help** |
| interval below 0 | **similarity hurts** |

Fewer than 100 important jumps: **underpowered**. Prediction: detectable,
small.

### H2 — does the 2005 model still work ten years later?

Both models trained on the whole 2005 far population, applied unchanged to the
2015 far population (outcome 2016–2025). Same difference and table.
Prediction: detectable, small.

### Reported, not tested

- Candidate pairs, far pairs and important jumps at each cutoff; the counts
  at 1%, 5% and 10%.
- Important jumps in the top 100 and top 1,000 under BASE, BASE+SIM and
  similarity alone, against chance, at 2005 (out-of-fold) and 2015.
- **The 2015 top 50** under BASE+SIM, with outcomes: work, its main area of
  use, target area, span, similarity, A-papers citing it in 2016–2025.
- **Landmark check** at 2015: for (Zagier's *Elliptic Modular Forms*
  W116915404, metric geometry), (Diamond–Shurman W1537136047, metric
  geometry) and (Fisk's interlacing note W2156858248, combinatorics): whether
  the pair was still unconnected at 2015, whether it was far, and its rank
  under BASE+SIM. (Croot–Lev–Pach cite no decisive work.)
- **The 2025 live list**: the top 50 far, unconnected pairs under BASE+SIM
  trained at 2005. Forecasts only.

Titles of works that are not arXiv papers are looked up from OpenAlex after
the run.

## Out of scope

- Any other cutoff, window, grain, threshold or feature. Anything the results
  suggest is reported as exploratory in its own section.

## Run and budget

One AWS m6i.4xlarge, self-terminating, idle-log watchdog, 2-hour power-off;
smoke pass first (every 4th paper). Estimated 20–40 minutes, under $1.
Teardown verified.
