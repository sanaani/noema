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

## Results

*Appended after the run. Nothing above this line changed.* Run
`noema-p12-20260929-200701` (launched with the Phase 12 launcher,
`USERDATA=phase13`), one m6i.4xlarge, 6 minutes, about $0.15. Numbers from
`results/phase13.json`; tool titles looked up in OpenAlex afterwards
(`results/titles.json`).

### The ladder at 15 years (history ≤ 2006, 2,241 popular tools)

| rung | cells | jumps | rate |
|---|---:|---:|---:|
| 1 shared paper | 6,474 | 1,984 | 31% |
| 2 shared author | 13,388 | 1,694 | 13% |
| 3 second-hand | 472 | 43 | 9.1% |
| 4 neighbouring field | 5,129 | 255 | 5.0% |
| **5 cold** | **24,700** | **728** | **2.9%** |

### Verdict

| test | positives | AUC BASE → BASE+SHAPE | gain [95% CI] | verdict |
|---|---:|---|---|---|
| **H1** cold jumps | 728 | 0.776 → 0.843 | **+0.067** [+0.054, +0.079] | **shape predicts cold jumps** |
| **H2** cold jumps that took hold | 126 | 0.818 → 0.886 | **+0.067** [+0.043, +0.095] | **shape predicts cold jumps** |

Both predictions held. With a five-year watch (Phase 12) shape's gain on cold
cells was +0.023; with fifteen it is +0.067, the same size as Phase 11's
gain on all cells.

### Reported, not tested

| | top 100 | top 1,000 |
|---|---:|---:|
| cold jumps: BASE+SHAPE / BASE / chance | 39 / 37 / 2.9 | **213** / 172 / 29 |
| took hold: BASE+SHAPE / BASE / chance | 13 / 12 / 0.5 | **49** / 39 / 5.1 |

Shape's gain is in the middle of the list, not the top: the top 100 are
nearly the same under both models.

**The 20 strongest cold jumps** (most outcome papers) are mostly standard
references adopted by a new area: *Matrix Analysis* into statistics (23
papers), *Large Deviations Techniques* into dynamical systems (16), *Banach
Lattices and Positive Operators* into PDE (15), *Functions of Bounded
Variation* into metric geometry (17). Shape moved several of them up sharply:
*Global Stability of Dynamical Systems* into optimisation, the strongest (26
papers), from the 20th percentile under BASE to the 66th; *Banach Lattices*
from the 66th to the 95th; *Nonlinear Potential Theory* into complex
analysis from the 69th to the 92nd.

**The top 20 under BASE+SHAPE** are graduate textbooks (algebraic topology,
Lie groups, algebraic geometry) predicted for neighbouring structural areas;
14 of the 20 became jumps.

### What this establishes

- Given a long enough watch, the demand profile predicts where a popular
  tool will appear in an area it had **no visible route into**, beyond
  popularity and citation habits, and it predicts the jumps that took hold
  as well as the ones that merely happened.
- Phase 12's small cold-cell gain was a short-watch effect: cold jumps are
  slow, and five years counted most of them as misses.

### What it does not establish

- **That these jumps are surprising ideas.** At the level of 28 arXiv areas
  and tools cited by 20+ papers, the cold jumps that happen are mostly
  textbooks being adopted by a new field. Valuable, yes, but not the
  Viazovska kind. Finding those needs a finer grain than arXiv categories.
- **Forward prediction in the strict sense.** Cross-validation by tool
  keeps each tool's outcome away from its model, but all tools share one
  period; a period-specific trend could help every fold at once.

### Sizing: a finer grain than 28 areas (counts only, no scores)

*Thresholds set before the run (`scripts/count-grains.py`): 600 cold jumps
and 150 that took hold.* Same window (≤ 2006 → 2007–21) and ladder; a paper's
area from four labellings. Runs `noema-p12-20260930-024413` (topics from the
OpenAlex snapshot) and `noema-p12-20260930-025942` (count), about $0.40.

At the topic grain the registered rung-4 rule breaks: most cells have flow 0,
so its 75th percentile is 0 and every cell lands on rung 4 (0 cold cells).
The **positive-flow rule** takes the percentile over cells with flow > 0 and
never counts flow 0 as neighbouring. Both are reported; the rule was changed
for this mechanical reason, before any score.

| grain | areas | cold jumps (registered rule) | took hold | cold jumps (positive-flow rule) | took hold | large enough |
|---|---:|---:|---:|---:|---:|---|
| arXiv category | 28 | 728 | 126 | 738 | 128 | no |
| MSC, 2 digits | 91 | 367 | 42 | 599 | 71 | no |
| OpenAlex subfield | 248 | 1,275 | 106 | 1,924 | 137 | no |
| **OpenAlex topic** | **3,455** | 0 (rule breaks) | 0 | **2,943** | **275** | **yes** |

**Landmarks stay unscorable at every grain.** They cite almost no tool that
was popular (≥ 20 citing arXiv papers) by 2006: Viazovska 2 of 26 references,
Croot–Lev–Pach 2 of 9, Ellenberg–Gijswijt 0 of 5, Huang none in OpenAlex.
MSC codes are missing on all five. OpenAlex topics do place them on the
problem side (Viazovska: point processes and geometric inequalities;
Croot–Lev–Pach: graph theory), not the tool's home.
