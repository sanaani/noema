# Phase 13 — a 15-year watch: does shape find cold jumps given time?

**Pre-registration.** Everything in this file is written and committed before
any Phase 13 score is computed. The sizing it rests on (counts only, no
scores) is in the Phase 12 README. Results go in a section appended below;
nothing above that section changes.

## Why

Phase 12 defined a **cold jump**: a popular tool reaching an area it had no
visible route into (no shared paper, shared author, second-hand citation or
neighbouring field). Shape helped a little on cold cells (+0.023), but the
five-year watch saw only 122 cold jumps, and 2 of them took hold. Five years
is too short for a surprising idea to be picked up.

The sizing count showed that longer watches collect far more cold jumps, and
a larger share of them take hold (about 2% at 5 years, about 17% at 15). The
two-window design of Phases 11 and 12 cannot use a long watch, because each
window needs its own history and outcome inside arXiv's 1998–2021 span.
Phase 13 uses **one window and cross-validation by tool** instead: models
are fitted on some tools and scored on others, so no tool is ever scored by
a model that saw its outcome.

## Data

Phase 11's papers and references and Phase 12's author ids, unchanged.

## Window

| history | outcome |
|---|---|
| papers dated ≤ **2006** | **2007–2021** (15 years) |

Reference coverage is 54% for 2021 papers, against 61–68% for 2015–2020;
the last year is undercounted, not dropped. Sizing count for this window:
24,700 cold cells, 728 cold jumps, 126 that took hold.

## Cells, positives, rungs, features

Exactly as Phases 11 and 12: popular tools (≥ 20 history citers), absent
from area A, rungs 1–5 with the neighbouring-field cut at the 75th percentile
of `flow` over this window's cells. TF-IDF fitted on history texts only.

- **Cold jump** (the positive): a rung-5 cell cited by ≥ 2 outcome papers in A.
- **Took hold**: a rung-5 cell cited by ≥ 5 outcome papers in A.

## Model and scoring

BASE (cites, recent, reach, size, flow) and BASE+SHAPE, logistic regression
exactly as Phase 11. **5-fold cross-validation grouped by tool**: tools are
shuffled with the seed and dealt into 5 folds; each fold's cells are scored by
models fitted on the other four folds' cold cells. Every cold cell gets one
out-of-fold score from each model. 95% intervals from 1,000 bootstrap draws
resampling tools. Seed **20261004**.

### H1 (primary) — does shape find cold jumps over 15 years?

AUC(BASE+SHAPE) − AUC(BASE) on cold cells, positive = cold jump.

| outcome | verdict |
|---|---|
| interval above 0, difference ≥ 0.03 | **shape predicts cold jumps** |
| interval above 0, difference < 0.03 | **detectable on cold cells, small** |
| interval contains 0 | **no measurable help on cold cells** |
| interval below 0 | **shape hurts on cold cells** |

Fewer than 400 cold jumps: **underpowered**, no verdict. Prediction: shape
predicts cold jumps (the gain grows with a longer watch, since slow jumps are
no longer counted as misses).

### H2 — does shape find the cold jumps that took hold?

The same out-of-fold scores (models fitted on cold jumps, not refitted),
positive = took hold, same verdict table and interval. Fewer than 100 that
took hold: **underpowered**. Prediction: shape predicts them.

### Reported, not tested

- Cells, positives and rate per rung (the Phase 12 ladder at 15 years).
- Positives among the top 100 and top 1,000 cold cells of each model, for
  cold jumps and for took hold, against chance.
- The 20 cold jumps with the most outcome papers: tool title, area, outcome
  papers, and their percentile under each model.
- The top 20 cold cells under BASE+SHAPE: tool title, area, outcome papers.

## Out of scope

- Any other window, threshold, fold count or feature. Anything the results
  suggest is reported as exploratory in its own section.

## Run and budget

One AWS m6i.4xlarge, self-terminating, idle-log watchdog, 2-hour power-off;
smoke pass first. Estimated 15 minutes, under $1; ceiling $3. Teardown
verified.

---
