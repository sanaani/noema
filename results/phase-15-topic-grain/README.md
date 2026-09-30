# Phase 15 — cold jumps between topics, not arXiv areas

**Pre-registration.** Everything in this file is written and committed before
any Phase 15 score is computed. The sizing it rests on (counts only) is in the
Phase 13 README. Results go in a section appended below; nothing above that
section changes.

## Why

Phase 13 found that, over a 15-year watch, a tool's demand profile (`shape`)
predicts cold jumps between arXiv's 28 areas (+0.067 AUC), and Phase 14 found
that two thirds of the model's hits did real work in the new area. But at 28
areas the jumps are textbooks reaching a neighbouring field. A surprising jump
lives at a finer grain: a tool reaching a *problem* it has never touched.
OpenAlex's 3,455 topics give that grain, and the sizing count found enough
cold jumps there (2,943, of which 275 took hold; targets 600 and 150).

At a fine grain one new route matters: two topics in the same subfield are
close relatives, and a tool moving between them is not surprising. Phase 15
adds that as its own rung.

## Data

Phase 11's papers and references, Phase 12's author ids, and the OpenAlex
topics fetched for the sizing count (`topics.jsonl.gz`: each paper's topics
and their subfields, in OpenAlex's score order; 526,505 papers). Papers with
no topics are dropped.

- A paper's **area** is its first (primary) topic; its **secondary
  categories** are its other topics.
- A topic's **subfield** is the one OpenAlex pairs with it.

## Window, cells, features

History ≤ **2006**, outcome **2007–2021**, as Phase 13. Cells and features
exactly as Phases 11 and 13 with topics as areas: popular tools (≥ 20 history
citers), absent from topic A, not an arXiv paper whose primary topic is A.
TF-IDF fitted on history texts only.

- **Cold jump** (positive): cited by ≥ 2 outcome papers in A.
- **Took hold**: cited by ≥ 5 outcome papers in A.

## The ladder (history only)

| rung | name | the cell is on this rung if |
|---|---|---|
| 1 | shared paper | a paper citing T lists A as a secondary topic |
| 2 | shared author | some author wrote a paper citing T and a paper whose primary topic is A |
| 3 | second-hand | a paper whose primary topic is A cites a paper that cites T |
| 4 | **same subfield** | a paper citing T has a primary topic in A's subfield |
| 5 | neighbouring field | T's `flow` into A is > 0 and at or above the 75th percentile of the cells with flow > 0 (the positive-flow rule from the sizing) |
| 6 | **cold** | none of the above |

Each cell sits on the lowest-numbered rung it meets.

## Population (fixed by counts, before any score)

The tested population is **rung 6** if it holds ≥ 600 cold jumps and ≥ 150
that took hold. Otherwise it is **rungs 4 and 6 together** (cold, or
reached only by a same-subfield relative), and the report says so.

## Model and scoring

BASE (cites, recent, reach, size, flow) and BASE+SHAPE, logistic regression
exactly as Phase 11; 5-fold cross-validation grouped by tool, as Phase 13.
95% intervals from 1,000 bootstrap draws resampling tools. Seed **20261006**.

### H1 (primary) — does shape find cold jumps between topics?

AUC(BASE+SHAPE) − AUC(BASE) on the population, positive = cold jump.

| outcome | verdict |
|---|---|
| interval above 0, difference ≥ 0.03 | **shape predicts cold jumps** |
| interval above 0, difference < 0.03 | **detectable on cold cells, small** |
| interval contains 0 | **no measurable help on cold cells** |
| interval below 0 | **shape hurts on cold cells** |

Fewer than 400 cold jumps: **underpowered**. Prediction: shape predicts cold
jumps.

### H2 — does shape find the cold jumps that took hold?

The same out-of-fold scores, positive = took hold, same table. Fewer than 100
that took hold: **underpowered**. Prediction: shape predicts them.

### Reported, not tested

- Cells, jumps, took hold and rate per rung (H2 of Phase 12 at this grain:
  does the rate fall down the ladder?).
- Shape's gain within each of rungs 1–5 (200 bootstrap draws each).
- Positives in the top 100 and 1,000 of each model, against chance.
- The 20 strongest cold jumps and the top 20 cells under BASE+SHAPE: tool
  title, the topic most of its history citers are in, the target topic,
  outcome papers, percentiles.

## Out of scope

- Any other grain, window, rung order or feature. Anything the results suggest
  is reported as exploratory in its own section.
- Landmark cells: none of the five landmarks can form one (sizing).

## Run and budget

One AWS m6i.4xlarge, self-terminating, idle-log watchdog, 2-hour power-off;
smoke pass first. Estimated 30–45 minutes, under $1; ceiling $3. Teardown
verified.

---
