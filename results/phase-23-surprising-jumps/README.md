# Phase 23 — does similarity forecast the surprising jumps?

**Pre-registration.** Everything in this file is written and committed before
any Phase 23 score is computed. Results go in a section appended below;
nothing above that section changes.

## Why

Phase 22 showed that similarity forecasts which works on a route will jump
(within-route AUC +0.064 [+0.035, +0.096]). Its follow-up
(`../phase-22-within-route/hits/`) showed that the model's hits are the kind
the project cares least about: 29 of the 31 hits in its top 100 were
**knocking** (the target field already cited the work through cross-listed
papers) or **next door** (one of the target's 3 nearest fields already cited
it). Surprising jumps were 41% of real jumps and 6% of hits.

Phase 23 makes surprise part of the target: among pairs that are **neither
knocking nor next door**, does similarity still forecast which will catch on?

Already seen before this file was written: all results of Phases 11–22 and
the follow-up, and the sizing counts below. No score has been computed on
this population.

## Population

Phase 22's build at the **2005** cutoff, unchanged (candidate pairs (W, A)
with W cited by at least 5 papers up to 2005 and by no A-paper; span,
similarity, size controls, home area, breadth), restricted to pairs labelled
**surprising** by the follow-up's rule, computed from data up to 2005:

- not knocking: no paper listing A as a secondary arXiv category cited W;
- not next door: no paper whose primary area is one of A's 3 nearest areas
  (highest co-citation share F[A | B], B ≠ A) cited W.

Important jump = at least **5** A-papers cite W in 2006–2015.

## Threshold, fixed by counts

Sizing (`sizing/count23.json`, counts only): surprising pairs and the
important jumps among them, by span.

| span ≥ | surprising pairs | crossed | important jumps | works |
|---:|---:|---:|---:|---:|
| none | 306,376 | 11,984 | 493 | 441 |
| 4.65 (Phase 21's wide) | 236,656 | 6,778 | **255** | 231 |
| 5.00 | 205,885 | 4,971 | 173 | 161 |
| 5.84 (Phase 21's far) | 135,776 | 2,340 | 95 | 90 |

Rule: the stricter of Phase 21's two thresholds with at least 100 important
jumps. **Primary: span ≥ 4.65 bits** (5.84 has 95).

For comparison, the catch-on rate is 5.0% for knocking pairs, 1.1% for next
door and **0.16%** for surprising (no span threshold).

## Models and grain

Exactly Phase 22's: logistic regression, BASE (three size controls, span,
breadth, home-area and target-area indicators) against BASE+SIM, out-of-fold
scores from 5-fold cross-validation grouped by work. Score: the
**within-route AUC** if the jumps fall on at least 10 routes that also hold
non-jumps and those routes hold at least 100 jumps; otherwise within target
area; otherwise underpowered. Seed **20261013**. Intervals: 95%, from 1,000
bootstrap draws resampling works.

## Test

### H1 — among surprising pairs, does similarity forecast important jumps?

Within-stratum AUC(BASE+SIM) − AUC(BASE), primary population:

| outcome | verdict |
|---|---|
| interval above 0, difference ≥ 0.03 | **similarity forecasts surprising jumps** |
| interval above 0, difference < 0.03 | **detectable, small** |
| interval contains 0 | **no measurable help** |
| interval below 0 | **similarity hurts** |

Prediction: detectable, small.

### Reported, not tested

- Jumps and pairs by target area and top routes.
- The difference at the other grain and with no strata; similarity alone.
- The same test at span ≥ 5.84 (95 jumps, labelled underpowered) and with no
  span threshold (493 jumps).
- Important jumps in the top 100 and top 1,000 (no strata) under both models,
  against chance.
- The **top 100** under BASE+SIM with each pair's work, route, citers,
  breadth, span, similarity and papers 2006–2015. Titles and record types of
  the works are looked up from OpenAlex after the run.

## Out of scope

- Any other cutoff, window, threshold, feature or label rule. Anything the
  results suggest is reported as exploratory in its own section.

## Run and budget

One AWS m6i.4xlarge (the Phase 12 launcher, `USERDATA=phase23`),
self-terminating, idle-log watchdog; smoke pass first (every 4th paper,
catch-on lowered to 1 paper). Under $1. Teardown verified.

---

## Results

*Appended after the run. Nothing above this line changed.* Run
`noema-p12-20260930-200148` (the Phase 12 launcher with `USERDATA=phase23`),
one m6i.4xlarge, 9 minutes, about $0.15, torn down and verified. Numbers from
`results/phase23.json`; titles and record types from OpenAlex in
`results/names.json`.

236,656 surprising pairs at span ≥ 4.65 bits, 255 important jumps, on 133
usable routes: grain **route**.

### Verdict

| test | within-route AUC, BASE → BASE+SIM | difference [95%] | verdict |
|---|---|---|---|
| **H1** (span ≥ 4.65, 255 jumps) | 0.705 → 0.816 | **+0.111 [+0.075, +0.147]** | **similarity forecasts surprising jumps** |
| span ≥ 5.84 (95 jumps) | 0.665 → 0.805 | +0.141 [+0.085, +0.196] | underpowered |
| no span threshold (493 jumps) | 0.705 → 0.819 | +0.114 [+0.087, +0.139] | similarity forecasts surprising jumps |

Similarity alone, within route: 0.824. The prediction (detectable, small) was
too cautious: the gain is larger than in Phase 22 (+0.064), where knocking and
next-door pairs were included.

### Reported, not tested (primary)

- Difference within target area +0.058; with no strata +0.038.
- Important jumps in the top 100: BASE 3, **BASE+SIM 13**, chance 0.11. Top
  1,000: 34 and **59**, chance 1.1.
- Targets of the jumps: optimization and control 44, dynamical systems 28,
  numerical analysis 23, rings and algebras 17, classical analysis 16. Top
  routes: probability → dynamical systems 17, probability → optimization 16,
  PDE → optimization 11.

### What the top 100 looks like

More research papers than before (57 articles, 35 books), and the list reads
as a map of real cross-field movements of 2006–2015, not only textbooks:

- **Backward stochastic differential equations** into control, PDE and
  numerical analysis: Pardoux–Peng (1990), El Karoui–Peng–Quenez (1997),
  Ma–Protter–Yong (1994). 4 of the 13 hits, and more BSDE pairs just below.
- **Mathematical finance** reaching optimization (minimal entropy martingale
  measures, optional decomposition, no-arbitrage valuation): ranked high, did
  not catch on in arXiv math.OC.
- Others: symbolic dynamics into ring theory (Lind–Marcus, a hit), Knutson–Tao
  honeycombs into classical analysis, Jerrum–Sinclair's permanent, Smale's
  problems for the next century, Flaschka–Newell deformations.
- Hits that are textbooks: Hartman's *ODEs*, Ladyzhenskaya's parabolic
  equations, Brézis's maximal monotone operators, Rockafellar's *Convex
  Analysis* (probability → dynamical systems), Ellis's *Entropy, Large
  Deviations*, Karatzas–Shreve, Hoeffding's inequality.

### What this establishes

- **Among pairs with no prior contact and no neighbouring contact,
  similarity forecasts which will catch on**, within a route, with a larger
  gain than on all far pairs. The surprising jumps are where similarity does
  the most work, not the least.
- The top of the list now contains real cross-field programmes (BSDEs, the
  finance-to-optimization wave), alongside textbooks.

### What it does not establish

- **Independence of the hits.** 4 of the 13 top-100 hits are one research
  programme (BSDEs, 3 works). The count "13 against 3" is partly one theme.
- **Anything after 2015.** One cutoff, one window.
- **That these are breakthroughs.** "Surprising" here is a mechanical rule
  about prior contact, and catching on still means 5 papers. Several top
  entries are textbooks.
