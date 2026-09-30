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

---

## Results

*Appended after the run. Nothing above this line changed.* Run
`noema-p12-20260930-143059` (the Phase 12 launcher with `USERDATA=phase19`),
one m6i.4xlarge, 10 minutes, about $0.15, torn down and verified. Numbers
from `results/phase19.json`.

Learn window: 9,674 cells (arrivals up to 2005), 37,998 follow-on papers,
2,374 cells with 5 or more.

### Verdict

| test | coefficient [95%] | verdict |
|---|---|---|
| **H1** span × similarity | +0.047 [+0.014, +0.082] | **content closeness matters more the farther the reach** |
| **H2** similarity | +0.058 [+0.020, +0.095] | **predicts more follow-on** |

Both predictions held.

### Reported, not tested

- **Coefficients** (per SD for span and similarity): log prior citers +0.24
  [+0.17, +0.30]; year −0.12 [−0.15, −0.09]; log area size −0.19 [−0.26,
  −0.12]; span **−0.35** [−0.40, −0.30].
- **Implied effect of +1 SD of similarity on follow-on**:

  | at | span (bits) | follow-on ratio [95%] |
  |---|---:|---|
  | median span | 3.6 | ×1.06 [1.02, 1.10] |
  | top-1% span | 5.8 | **×1.21** [1.09, 1.35] |

- **By span decile** (Spearman of similarity with follow-on; mean follow-on,
  high against low similarity): lowest decile +0.10 (5.3 vs 4.0); deciles 2–7
  between −0.01 and +0.04, with mixed means; deciles 8, 9, 10: +0.06 (3.3 vs
  2.5), +0.02 (2.8 vs 2.4), +0.07 (2.0 vs 1.7). The per-decile view is noisy
  and not monotone; the lowest decile also shows an effect.
- **Tail check** (peek top 1%, 866 cells, 12 with 5 or more follow-ons):
  Spearman +0.04. Positive, as the slope predicts, and weak.
- **Label sensitivity** (span as the largest over the arriving papers'
  categories): span × similarity +0.041 [+0.005, +0.074], same verdict;
  +1 SD similarity at top-1% span ×1.20 [1.08, 1.32].

### What this establishes

- **Far reaches are followed much less** (span −0.35 per SD: each SD
  farther cuts follow-on by about 30%), confirming Phase 18's gradient on the
  count outcome with controls.
- **Among far reaches, the ones whose papers say similar things to the work's
  existing users are followed more**, and this effect grows with distance:
  about +6% per SD of similarity at an ordinary reach, about +21% at the
  top-1% reach. This is the hidden-bridge pattern, now on 9,674 cells rather
  than six.
- The result does not depend on which arXiv category is taken as the area.

### What it does not establish

- **Size.** The effect is real but modest: similarity shifts follow-on by
  tens of percent, while span alone shifts it by a factor of several. It
  ranks far reaches; it does not pick breakthroughs by itself.
- **The tail directly.** The top-1% value is the model's extrapolation of a
  linear interaction; the direct tail check is weak (+0.04), and the decile
  view is not monotone.
- **Cause.** Similar content may make a borrowed tool easier to use, or
  papers that already speak the new area's language may be better placed to
  be read there. The data do not separate these.
