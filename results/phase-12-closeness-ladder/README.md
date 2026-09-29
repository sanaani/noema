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
