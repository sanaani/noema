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

---

## Results

*Appended after the run. Nothing above this line changed.* Run
`noema-p12-20260930-174758` (the Phase 12 launcher with `USERDATA=phase22`),
one m6i.4xlarge, 6 minutes, about $0.10, torn down and verified. Numbers from
`results/phase22.json`.

### Where the important jumps actually went

The 229 important jumps (146,938 far pairs) fall on **70 routes** and **15
target areas**, so the grain rule chose **route**. They are concentrated in
applied targets, not in logic or topology:

| target area | important jumps | far pairs |
|---|---:|---:|
| math.OC (optimization and control) | 113 | 14,866 |
| math.NA (numerical analysis) | 38 | 12,674 |
| math.ST (statistics) | 19 | 13,936 |
| math.LO (logic) | 17 | 15,128 |
| math.SP (spectral theory) | 12 | 9,420 |
| other 10 areas | 30 | — |

Top routes: probability → optimization/control 43, PDE → optimization/control
21, probability → numerical analysis 13, differential geometry →
optimization/control 12, algebraic geometry → optimization/control 9.

### Verdict

| test | within-route AUC, BASE → BASE+SIM | difference [95%] | verdict |
|---|---|---|---|
| **H1** (≥ 5.84 bits, 229 jumps) | 0.825 → 0.888 | **+0.064 [+0.035, +0.096]** | **similarity picks the pair** |
| H1 at ≥ 4.65 bits (888 jumps) | 0.806 → 0.884 | +0.078 [+0.062, +0.095] | similarity picks the pair |

Similarity alone, within route: 0.884 (primary), 0.879 (wide).

### Reported, not tested (primary threshold)

| variant | AUC BASE → BASE+SIM | difference |
|---|---|---:|
| within target area | 0.895 → 0.922 | +0.027 |
| no strata (area indicators in both models) | 0.932 → 0.945 | +0.013 |
| within route, without breadth | 0.800 → 0.885 | +0.086 |
| within route, without area indicators | 0.846 → 0.905 | +0.059 |

Top 100 (no strata): BASE 20, BASE+SIM 31, chance 0.16. Top 1,000: 83 and
100, chance 1.6.

### What this establishes

- **Similarity forecasts the pair, not only the field.** Comparing a real
  jump only with non-jumps on the same field-to-field route (the field is
  then no help), adding similarity raises the ranking from 0.825 to 0.888,
  with an interval clear of zero and of the 0.03 bar. Same at the wider
  threshold.
- **Breadth ("cited by everyone") explains part of it, not all**: the gain is
  +0.086 without breadth and +0.064 with it.
- Phase 21's lists (all logic and topology) did not reflect where jumps
  happened; half of the real ones went into optimization and control.

### What it does not establish

- Where similarity helps most. Within target area the gain is smaller
  (+0.027), because the home area then still tells BASE a lot; with only
  area indicators and no strata, most of Phase 21's gain is taken by knowing
  the fields (+0.013 left). Similarity's distinct contribution is ranking
  works *within* a given route.
- Anything after 2015: the forward test is still blocked by missing
  references (Phase 21 sizing).
