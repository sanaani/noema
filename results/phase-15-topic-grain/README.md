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

## Results

*Appended after the run. Nothing above this line changed.* Run
`noema-p12-20260930-092256` (the Phase 12 launcher with `USERDATA=phase15`),
one m6i.4xlarge, 11 minutes, about $0.15, torn down and verified. Numbers from
`results/phase15.json`; tool and topic names looked up from OpenAlex in
`results/names.json`.

### Cells and the ladder

2,241 popular tools × 3,455 topics: 7,718,748 cells, 11,111 cold jumps in all.
248 subfields. Positive-flow threshold 0.074.

| rung | cells | jumps | took hold | jump rate |
|---|---:|---:|---:|---:|
| 1 shared paper | 39,971 | 5,454 | 1,389 | 13.6% |
| 2 shared author | 66,081 | 2,449 | 379 | 3.7% |
| 3 second-hand | 3,562 | 93 | 13 | 2.6% |
| 4 same subfield | 306,981 | 977 | 113 | 0.32% |
| 5 neighbouring field | 117,576 | 153 | 4 | 0.13% |
| 6 cold | 7,184,577 | 1,985 | 163 | 0.028% |

The rate falls down every step of the ladder. Rung 6 met both targets (1,985
≥ 600 jumps, 163 ≥ 150 took hold), so the tested population is **rung 6
(cold)**.

### Verdict

| test | AUC BASE → BASE+SHAPE | difference [95%] | verdict |
|---|---|---|---|
| **H1** cold jump | 0.969 → 0.976 | +0.0065 [+0.0042, +0.0086] | **detectable on cold cells, small** |
| **H2** took hold | 0.980 → 0.991 | +0.0114 [+0.0073, +0.0156] | **detectable on cold cells, small** |

Both predictions ("shape predicts") were too strong: shape helps, reliably,
but by less than the 0.03 bar. The AUCs are near 1 because most of the 7.2
million cold cells are obviously dead (an unpopular tool, a tiny topic), and
BASE already ranks those last.

### Reported, not tested

- **Top of the list** (cold jumps among the top N cold cells; chance is the
  base rate × N):

  | | top 100 | top 1,000 |
  |---|---:|---:|
  | BASE | 12 | 28 |
  | BASE+SHAPE | 14 | **75** |
  | chance | 0.03 | 0.28 |

  About 1 in 13 of shape's top 1,000 cold picks became a jump, 2.7 times
  BASE's count and about 270 times chance. For took hold: 8 against BASE's 1
  (chance 0.02).
- **Shape's gain within the other rungs**: shared paper +0.081 [+0.075,
  +0.087]; shared author +0.083 [+0.076, +0.091]; second-hand +0.009 [−0.047,
  +0.046]; same subfield +0.033 [+0.027, +0.040]; neighbouring field +0.006
  [−0.000, +0.012].
- **Strongest cold jumps** (outcome papers): Triebel's *Theory of Function
  Spaces*, from harmonic analysis to stochastic processes in finance (25);
  Lasserre's *Global Optimization with Polynomials* to tensor decomposition
  (24); Horn and Johnson's *Matrix Analysis* to tensor decomposition (22); the
  *Handbook of Mathematical Functions* to fractional differential equations
  (16); Sato's *Lévy Processes* to fractional differential equations (12); Cox,
  Little and O'Shea's *Ideals, Varieties, and Algorithms* to tensor
  decomposition (11). All 20 were in the top 1.2% under BASE+SHAPE.
- **Top 20 under BASE+SHAPE**: all 20 are one tool, `W4285719527`, paired with
  20 topics. OpenAlex no longer serves this record (404). Its 577 history
  citers span free probability, n-categories and quantum thermodynamics, so it
  is a catch-all record that many unrelated references were resolved to, not
  a real work. Its 20 cells produced 16 outcome citations in total.

### What this establishes

- At the topic grain, with same-subfield moves no longer counted as cold,
  shape still adds a small but clearly nonzero lift. The lift is concentrated
  where it matters for a lead list: the top 1,000 cold picks hold 75 real
  jumps against 28 for BASE.
- The ladder is a real distance at this grain too: each rung's jump rate is
  lower than the one above.

### What it does not establish

- **Mis-tagged topics.** OpenAlex topics are assigned by a classifier built for
  all of science. Some targets are implausible for arXiv math papers (for
  example *Functions of Bounded Variation* into "Species Distribution and
  Climate Change"). Some cold jumps are therefore jumps into a wrong label,
  not a new problem.
- **Junk tool records.** At least one catch-all record reaches the top of the
  list. How many of the top 1,000's 75 hits come from such records is not
  known without a rerun that excludes them (exploratory, not done).
- **Real work.** Phase 14's reading check was at the arXiv-area grain; it was
  not repeated here.
