# Phase 25 — the matchmaker lists

**Pre-registration.** Everything in this file is written and committed before
any Phase 25 number is computed. Results go in a section appended below;
nothing above that section changes.

## Why

Phases 21–24 established that content similarity forecasts which far,
not-yet-connected (work, area) pairs will meet, best of all for surprising
pairs (Phase 23: within-route AUC +0.111), and that it lifts real
breakthroughs (Phase 24: 11 of 12, p = 0.006) without ranking them sharply
enough for a global shortlist (median 92nd percentile of 401,302 pairs).

The decision was not to sharpen the statistics further but to make the thing
the project is for: **per-area lists** short enough for a mathematician to
read, of works from far-off fields that their field's recent papers resemble
but nobody in their field has cited. A 92nd-percentile detector is enough
for a list of 20 read by an expert; it is not enough for a global top 100.

Already seen before this file was written: all results of Phases 11–24.

## Data and cutoffs

Phase 11's arXiv math papers and OpenAlex references (28 areas,
`W4285719527` dropped). References collapse after 2021 (79% of 2022 papers
and 95% of 2025 papers have none), so:

| cutoff | role | outcome years |
|---|---|---|
| **2011** | train, and replicate Phase 23's test | 2012–2021 (full 10-year window, references intact) |
| **2021** | live lists | 2022–2025, sparse: lower bounds only |

## Build, population, model

Phase 23's, unchanged, at each cutoff: co-citation table, span, TF-IDF +
256-dimension SVD, similarity to the area's last 5 years. Population: the
**surprising** unconnected pairs (work with at least 5 citers; no citer in
the area, none listing it as a secondary category, none in the area's 3
nearest areas by co-citation) with **span ≥ 4.65 bits** (Phase 23's primary
threshold). BASE = log citers, log recent citers, log area size, span,
breadth, home and target dummies; BASE+SIM adds similarity. Logistic
regression, features standardised on the 2011 population and the same
standardisation applied at 2021. Seed **20261015**.

## Tests

### H1 — Phase 23 at a second cutoff

At 2011, 5-fold cross-validation grouped by work; within-route AUC
(BASE+SIM) − AUC(BASE), 95% interval from 1,000 bootstrap draws over works;
Phase 22's grain rule (route if ≥ 100 jumps in ≥ 10 usable routes, else
target area, else underpowered). Phase 23's verdict table:

| outcome | verdict |
|---|---|
| interval above 0, difference ≥ 0.03 | **similarity forecasts surprising jumps** |
| interval above 0, difference < 0.03 | **detectable, small** |
| interval contains 0 | **no measurable help** |
| interval below 0 | **similarity hurts** |

Prediction: similarity forecasts surprising jumps, difference between +0.05
and +0.15.

### The lists (the product; reported, not tested)

Both models fitted on the whole 2011 population, applied unchanged at 2021.
For each of the 28 areas: the **20 surprising pairs with the highest BASE+SIM
score** whose target is that area, with the work's title, home area, citers,
span, similarity, global rank, and the **3 recent (2017–2021) papers of the
area most similar to the work's citers** (so a reader can see *why* it was
paired). 560 pairs in all. Titles of non-arXiv works are looked up from
OpenAlex during the run (batched; if the lookup fails they are filled in
after).

### Forward check (reported, not tested)

For each pair, target-area papers of 2022–2025 citing the work, from the
corpus's references. These are **lower bounds** because most references
after 2021 are missing. Reported: the share of the 560 listed pairs with at
least 1 such paper, against the share among all surprising pairs at 2021
(the **lift**), for BASE, BASE+SIM and similarity alone; and per area.
Prediction: lift of BASE+SIM above 2. Not a test, because the missing
references make the base rate itself unreliable.

### The real test is reading

The lists are the deliverable. Whether they are worth a mathematician's
afternoon is judged by reading them, not by these counts.

## Out of scope

Any other cutoff, threshold, grain or feature. Anything the lists suggest is
reported as exploratory in its own section.

## Run and budget

One AWS m6i.4xlarge via the Phase 12 launcher (`USERDATA=phase25`),
self-terminating, idle-log watchdog, 2-hour power-off; smoke pass first
(every 4th paper). Two builds, the 2021 one on about 500,000 papers: about
20–30 minutes, under $1. Teardown verified.
