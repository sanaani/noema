# Phase 19 — does content closeness matter more the farther a citation reaches?

**Pre-registration.** Everything in this file is written and committed before
any Phase 19 number is computed. Results go in a section appended below;
nothing above that section changes.

## Why

Phase 18 defined groundbreaking as a citation in the top 1% by span (how far
it carries a work from where it has been used) that then caught on. Only 12
such cells exist up to 2015, even with a peek past the cutoff. Growing the
data tenfold would give roughly 60–120: still too few. The top 1% is rare by
construction, so it will never support a test on its own.

Phase 18 also showed a gradient: catch-on falls steadily with span (30% in
the lowest decile, 12% in the highest, 6% in the top 1%). Phase 19 tests the
gradient instead of the tail:

> Does content closeness predict catching on more strongly the farther the
> citation reaches?

If it does, the effect is largest where we care most, and the trend carries
into the top 1% even though the top 1% cannot be tested alone. The top 1%
remains the reading list; the test is the slope leading up to it.

Already seen before this file was written: all Phase 18 results, including
its cells' span, similarity and catch-on by span decile (but not the
relation between similarity and follow-on within span levels, beyond the
six hidden-bridge cases in the top 1%).

## Data and cells

Exactly Phase 18's (`scripts/run-phase18.py` definitions, reused): arXiv math
papers and their OpenAlex references; eligible arrival cells (W, A, y) with ≥
5 prior citers; the co-citation table, span and 256-dimension content
similarity, all fitted on papers up to 2015. One change: the catch-all
OpenAlex record `W4285719527` (Phase 15/16: no longer served, cited from
unrelated fields) is dropped as a work.

- **Window**: T = **10** years, Phase 18's measured value. Learn window:
  arrivals up to 2005, follow-on counted in years y+1 to y+10 (all ≤ 2015).
  No peek.
- **Outcome**: the **follow-on count**, the number of A-papers citing W in
  years y+1 to y+10 (a count, not Phase 18's yes/no at 5).

## Model

Poisson regression (log link, unpenalised) of the follow-on count on:

- controls: log(1 + prior citers), arrival year, log(1 + papers in A that
  year);
- **span**, **similarity**, and **span × similarity**.

Span and similarity are standardised (mean 0, SD 1) over the learn window
before the product is taken. Seed **20261009**. Intervals: 95%, from 1,000
bootstrap draws resampling works.

## Tests

### H1 (primary) — does closeness matter more farther out?

The span × similarity coefficient.

| interval | verdict |
|---|---|
| above 0 | **content closeness matters more the farther the reach** |
| contains 0 | **no evidence that it changes with reach** |
| below 0 | **content closeness matters less the farther the reach** |

Prediction: matters more.

### H2 — does content closeness predict catching on at all?

The similarity coefficient (its effect at average span), same table with
"predicts more follow-on" / "no evidence" / "predicts less follow-on".
Prediction: predicts more follow-on.

### Reported, not tested

- All coefficients with intervals.
- **Implied effect at the tail**: the model's follow-on ratio for +1 SD of
  similarity at median span and at the learn window's top-1% span threshold,
  with intervals.
- **By span decile**: Spearman between similarity and follow-on count within
  each decile, and the mean follow-on of cells above against below the
  decile's median similarity.
- **Tail check** (descriptive, uses the peek): Phase 18's peek top 1% (arrivals
  up to 2015, follow-on judged to 2025) — Spearman between similarity and
  follow-on count, which the slope predicts is positive.
- **Label sensitivity**: H1 again with span taken as the *largest* span over
  the arriving papers' arXiv categories (primary and cross-lists) instead of
  the cell's primary area. A cross-listed paper that carries a work from one
  of its areas into another counts as far. This is the rule under which
  Phase 18's sphere-packing references were far.

## Out of scope

- Any other window, grain, outcome or model. Anything the results suggest is
  reported as exploratory in its own section.

## Run and budget

One AWS m6i.4xlarge, self-terminating, idle-log watchdog, 2-hour power-off;
smoke pass first (every 4th paper). Estimated 10–15 minutes, under $1.
Teardown verified.
