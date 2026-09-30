# Phase 22 — does similarity pick the pair, or only the field?

**Pre-registration.** Everything in this file is written and committed before
any Phase 22 number is computed. Results go in a section appended below;
nothing above that section changes.

## Why

Phase 21 found that, at the 2005 cutoff, content similarity forecasts which
far, not-yet-connected (work, area) pairs become important jumps: AUC
0.855 → 0.925, +0.070 [+0.054, +0.087]. Two things in its lists leave the
meaning open:

- **Every top-50 entry targets logic (math.LO) or general topology
  (math.GN).** Similarity may only be telling fields apart: some fields
  absorb outside work more readily, and their text may sit closer to
  everything. That would be a forecast of the *field*, not of the *pair*.
- **Most top entries are standard textbooks**, cited across many fields.
  Similarity may be picking "used by everyone", not "fits this field".

Phase 22 asks whether similarity still ranks pairs once both are accounted
for.

Already seen before this file was written: all results of Phases 11–21.
Nothing about how Phase 21's 229 important jumps spread over fields or routes
has been looked at.

## Population, outcome and features

Phase 21's H1 population, unchanged: cutoff **2005**, candidate pairs (W, A)
with W cited by at least 5 papers up to 2005 and by no A-paper; far = span ≥
**5.84 bits**; important jump = at least **5** A-papers cite W in
2006–2015. Span, similarity and the three size controls are Phase 21's.

New:

- **Home area** of W: the area with most of W's citers up to 2005 (ties: the
  first in alphabetical order).
- **Route**: (home area, target area), e.g. math.DS → math.LO.
- **Breadth**: the number of distinct areas whose papers cite W up to 2005.
  Textbooks are broad; this is the "generic reference" control.

## Models

Logistic regression (standardised features, C = 1, as Phase 21):

- **BASE**: the three size controls, span, breadth, and indicator columns for
  the home area and the target area;
- **BASE+SIM**: BASE plus similarity.

Out-of-fold scores from 5-fold cross-validation grouped by work (Phase 13's
code). Seed **20261012**. Intervals: 95%, from 1,000 bootstrap draws
resampling works.

## The test grain, fixed by counts before any score

The score is the **within-stratum AUC**: the chance that a real jump ranks
above a non-jump *of the same stratum*, pooled over strata (each stratum
weighted by its number of jump × non-jump comparisons). Pairs in different
strata are never compared, so knowing which field is favoured earns nothing.

- **Primary stratum = route** if the important jumps fall on at least **10**
  routes that also hold non-jumps, and those routes hold at least **100**
  important jumps;
- otherwise **target area**, with the same two conditions;
- otherwise **underpowered**.

The choice uses counts only and is logged before any model is fitted.

## Test

### H1 — within the stratum, does similarity still forecast important jumps?

Within-stratum AUC(BASE+SIM) − AUC(BASE):

| outcome | verdict |
|---|---|
| interval above 0, difference ≥ 0.03 | **similarity picks the pair** |
| interval above 0, difference < 0.03 | **detectable, small** |
| interval contains 0 | **similarity only picks the field** |
| interval below 0 | **similarity hurts** |

Prediction: detectable, small.

### Reported, not tested

- Important jumps and far pairs by target area and by the top routes.
- The same difference at the other grain (target area if route is primary,
  and the reverse), and with no strata at all.
- The primary test without breadth, to show breadth's share of the effect.
- Within-stratum AUC of similarity alone.
- The primary test at the wider far threshold (≥ 4.65 bits, Phase 21's 888
  positives).
- Important jumps in the top 100 and top 1,000 (no strata) under both models.

## Out of scope

- Any other cutoff, window, threshold or feature; the 2011 forward test (too
  few positives while references thin out after 2015, see
  `../phase-21-forecast-real-far/sizing/README.md`).

## Run and budget

One AWS m6i.4xlarge, self-terminating, idle-log watchdog, 2-hour power-off;
smoke pass first (every 4th paper, catch-on lowered to 1 paper). Estimated
10–20 minutes, under $1. Teardown verified.
