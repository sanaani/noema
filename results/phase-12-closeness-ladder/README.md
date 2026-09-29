# Phase 12 — how close was the tool already? A closeness ladder for Phase 11's cells

**Pre-registration.** Everything in this file is written and committed before
any author data is downloaded or any rung is computed. Results go in a section
appended below; nothing above that section changes.

## Why

Phase 11 found that a tool's demand profile (`shape`) predicts which areas it
will enter next, +0.057 AUC over popularity and citation habits. Its
exploratory check showed that about half of that gain was *next-door use*:
papers cross-listed in the area already citing the tool. But "next door" was
defined by one convenient count (cross-listed citers), not by what it means:
**the tool already had a visible route into the area.** There are other routes
that count missed: a person who works in both places, an area paper that cites
a paper that uses the tool, an area that leans heavily on the tool's home
fields.

The project's question is how to find jumps that are **rare, surprising and
valuable**. A jump is surprising only if it had no visible route. Phase 12
makes "next door" a measured distance, a ladder of routes, and asks whether
shape still finds jumps on the bottom rung, where there was no route at all.

## Data

Phase 11's papers, references, windows, cells, positives and features,
unchanged (`results/phase-11-tool-area-grid/README.md`). One addition:

- **Authors**: OpenAlex author ids (`authorships[].author.id`) of each paper's
  arXiv DOI and journal DOI works, from the same OpenAlex parquet snapshot
  (2026-09-23), joined by DOI exactly as Phase 11's references were. A paper
  OpenAlex does not hold has no authors. Missing author ids are dropped.

## The ladder (history window only)

For a cell (tool T, area A), using only history papers:

| rung | name | the cell is on this rung if |
|---|---|---|
| 1 | **shared paper** | a paper citing T lists A as a secondary category (Phase 11's `xlist` > 0) |
| 2 | **shared author** | some author wrote both a paper citing T and a paper whose primary area is A |
| 3 | **second-hand** | a paper whose primary area is A cites a paper that cites T |
| 4 | **neighbouring field** | T's `flow` into A is at or above the 75th percentile of `flow` over all of that window's cells |
| 5 | **cold** | none of the above |

Each cell sits on the **lowest-numbered** rung it meets. Rung 3's middle paper
must be one of the arXiv math papers (only their references are known).

## Tests

Seed **20261003**; 1,000 bootstrap draws resampling tools; logistic regressions
exactly as Phase 11 (standardised features, L2, C = 1).

### H1 (primary) — does shape find cold jumps?

Keep only rung-5 (cold) cells in both windows. Fit BASE and BASE+SHAPE on the
fit window's cold cells, score the test window's cold cells.
AUC(BASE+SHAPE) − AUC(BASE):

| outcome | verdict |
|---|---|
| interval above 0, difference ≥ 0.03 | **shape predicts cold jumps** |
| interval above 0, difference < 0.03 | **detectable on cold cells, small** |
| interval contains 0 | **no measurable help on cold cells** |
| interval below 0 | **shape hurts on cold cells** |

If either window has fewer than 100 cold positives, H1 is reported as
**underpowered** with no verdict.

Prediction: shape predicts cold jumps, with a smaller gain than Phase 11's
X2 (+0.046), since X2 removed only rung 1.

### H2 — is the ladder a distance?

The test window's positive rate on each rung. Passes if the rate on rung 5 is
below the rate on every other rung. Prediction: passes, and the rate falls from
rung 1 to rung 5.

### Reported, not tested

- Cells, positives and positive rate per rung, both windows.
- Shape's gain within each rung separately (models fitted per rung, as in H1).
- **All cells, ladder controlled**: BASE + the four rung indicators (rungs
  1–4), with and without shape (as Phase 11's X1, with the whole ladder).
- **Cold short lists**: positives among the top 1,000 cold test cells under
  BASE and BASE+SHAPE, against chance.
- **Cold jumps that took hold**: cold test cells cited by at least 5 outcome
  papers in A. How many there are, and how many fall in each model's top 1,000
  cold cells, against chance.
- **The top 20 cold predictions** of BASE+SHAPE, with the tool's OpenAlex id,
  its title when it is one of the arXiv papers, the area, and how many outcome
  papers in A cited it. For reading, not scoring.
- Author coverage: share of history papers with at least one author id.

## Out of scope

- Any other rung, threshold, or ordering. Anything the results suggest is
  reported as exploratory in its own section.
- Landmark cells (none formed a Phase 11 cell).

## Run and budget

One AWS m6i.4xlarge, self-terminating, with the Phase 11 guardrails (idle-log
watchdog, 2-hour power-off). Smoke pass first: authors from the newest three
snapshot files, then the Phase 11 smoke windows. Then the authors stage on the
full snapshot (Phase 11's reference stage took 17 minutes) and the analysis.
Estimated under 1 hour and under $2; ceiling $5. The role, instance profile,
security group, instance and task object are torn down and the teardown
verified.

---

## Results

*Appended after the run. Nothing above this line changed.* Run
`noema-p12-20260929-160858`, one m6i.4xlarge, 23 minutes, about $0.35.
Numbers from `results/phase12.json`.

**Authors.** 526,506 of 597,860 papers have OpenAlex author ids (the same
papers that have references). History papers with authors: 88% (fit), 81%
(test).

### The ladder (test window: ≤ 2015 → 2016–20)

| rung | cells | positives | rate | shape's gain [95% CI] |
|---|---:|---:|---:|---|
| 1 shared paper | 43,508 | 1,797 | 4.1% | +0.055 [+0.047, +0.062] |
| 2 shared author | 143,510 | 1,337 | 0.93% | +0.048 [+0.040, +0.056] |
| 3 second-hand | 4,549 | 21 | 0.46% | +0.075 [+0.031, +0.117] |
| 4 neighbouring field | 29,137 | 53 | 0.18% | +0.110 [+0.064, +0.157] |
| **5 cold** | **182,883** | **122** | **0.067%** | **+0.023 [+0.005, +0.041]** |

Fit window cold cells: 68,753 with 151 positives, so H1 is powered.

### Verdict

| test | prediction | result | verdict |
|---|---|---|---|
| **H1** shape on cold cells | shape predicts cold jumps | 0.846 → 0.868, **+0.023** [+0.005, +0.041] | **detectable on cold cells, small** |
| **H2** cold rate below every rung | passes, falling 1 → 5 | 4.1% → 0.93% → 0.46% → 0.18% → 0.067% | **passes; falls at every step** |

### Reported, not tested

- **Cold short list:** positives in the top 1,000 cold cells: BASE 10,
  BASE+SHAPE 16, chance 0.7.
- **Cold jumps that took hold** (≥ 5 outcome papers in A): **2** of 182,883
  cold cells. Neither is in either model's top 1,000.
- **All cells, ladder controlled:** BASE + rung indicators 0.874 → with
  shape 0.894, +0.020 [+0.017, +0.023].
- **Top 20 cold predictions** (titles in `results/top20-titles.json`): none
  was a positive. They are standard textbooks in areas that had not cited
  them: *Harmonic Analysis in Phase Space*, *Geometric Measure Theory*,
  *Matrix Analysis*, *Sobolev Spaces*, *Algebraic Topology*.

### What this establishes

- **The ladder is a real distance.** Each rung down is 2–5× less likely to
  fill, and cold cells fill 60× less often than shared-paper cells. Cold
  cells are 45% of all cells but hold 3.7% of positives.
- **Almost every jump had a visible route.** 96% of the tools that entered
  a new area in 2016–20 were already one step away, by a shared paper, a
  shared author, a second-hand citation or a neighbouring field.
- **Shape still helps on cold cells, a little.** The interval is above 0 but
  the gain is under the 0.03 bar, and 16 hits in 1,000 is too few to be
  useful as a list. Shape's larger gains are on the near rungs.

### What it does not establish

- **That shape finds valuable cold jumps.** At this grain (popular tools,
  28 arXiv areas, five years) valuable cold jumps barely exist in the
  data: 2 took hold. The top of the cold list is textbooks, not
  surprising ideas. A test of "rare and valuable" needs a finer target
  (sub-areas or topics, not 28 arXiv categories) or a longer horizon.

### Sizing: would a longer watch give enough cold jumps? (after the results)

`scripts/count-horizons.py` (run `noema-p12-20260929-164945`, about $0.05;
counts only, no model scores; `results/horizons.json`). Cold cells that
became a jump (≥ 2 papers) / took hold (≥ 5), by history cutoff, watched to
2021. Reference coverage is 54–68% through 2021, then collapses (21% in
2022, 5% in 2025), so 2021 is the last usable outcome year.

| history ≤ | popular tools | watch | cold jumps | took hold |
|---|---:|---:|---:|---:|
| 2000 | 154 | 21 years | 291 | 99 |
| 2002 | 440 | 19 | 448 | 148 |
| 2004 | 1,078 | 17 | 679 | **171** |
| 2006 | 2,241 | 15 | **728** | 126 |
| 2008 | 4,051 | 13 | 645 | 70 |
| 2010 | 6,578 | 11 | 541 | 45 |
| 2015 | 17,647 | 6 | 173 | 6 |

A longer watch makes a jump far more likely to take hold (2% of cold jumps
at 5 years, about 25% at 15+). But the corpus has a fixed clock: arXiv
math is thin before 2004 and references stop in 2021. Every extra year of
watching is a year taken from history, so cold jumps peak at about 730
(one window) and took-hold jumps at about 170. A pre-registered test needs
two separate windows (fit, then test); the best split (≤ 2000 → 2001–10,
≤ 2010 → 2011–21) gives 128 and 541 cold jumps, 23 and 45 took hold.
