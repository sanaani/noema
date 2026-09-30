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

---

## Results

*Appended after the run. Nothing above this line changed.* Run
`noema-p12-20260930-212955` (`USERDATA=phase25`), one m6i.4xlarge, 11
minutes, about $0.15, torn down and verified. Numbers from
`results/phase25.json`; the lists themselves, readable, in `lists.md`.

### H1 — Phase 23 replicated at 2011, and stronger

Population at 2011: 869,210 surprising pairs at ≥ 4.65 bits, **158 important
jumps** (fewer than 2005's 255, from a bigger pool) in 74 usable routes; grain
route.

| | AUC BASE | AUC BASE+SIM | difference | 95% interval | verdict |
|---|---:|---:|---:|---|---|
| 2011 (this phase) | 0.664 | 0.839 | **+0.175** | [+0.123, +0.233] | **similarity forecasts surprising jumps** |
| 2005 (Phase 23) | 0.705 | 0.816 | +0.111 | [+0.075, +0.147] | same |

Similarity alone: 0.841. Top 100 out-of-fold: 12 jumps with similarity, 3
without (chance 0.02). Top 1,000: 34 vs 18. The prediction (+0.05 to +0.15)
was beaten. Standardised coefficients of the fitted BASE+SIM model:
similarity **+1.18**, recent citers +0.36, span −0.35, area size +0.14,
citers −0.12, breadth +0.02.

### The lists at 2021

3,314,791 surprising pairs at 2021. **math.DS has none**: dynamical systems
is co-cited with everything, so no pair reaches 4.65 bits or every area is
one of its neighbours. 27 lists, **540 pairs**, in `lists.md`. 58 works
came back from OpenAlex without a title (mostly `W29…` records, arXiv
duplicates that OpenAlex has since merged) and are shown by id.

### Forward check (lower bounds)

Of 3.3 million pairs, 1,527 (0.046%) have at least one 2022–2025 target-area
citer in our corpus; none has 5, because most references after 2021 are
missing. The 540 listed pairs contain 7: **lift 28×** (predicted > 2). The
global top 560 by score: BASE+SIM 56×, similarity alone 44×, BASE 36×.
Numbers this small say only that the ranking points the right way.

### Reading the lists (exploratory)

The lists are mixed, and the failure mode is specific: **word collisions**.
TF-IDF sees words, not meanings, so

- commutative algebra's list is led by *analytic ideals* from set theory and
  *order ideals of posets* from combinatorics ("ideal");
- PDE's list is led by set-theoretic solutions of the *Yang–Baxter equation*
  from ring theory ("equation", "solutions");
- logic's list includes a mis-resolved OpenAlex record (a Turkish medical
  paper cited by 23 arXiv papers under the wrong id).

Other lists read as real hidden bridges, in the project's sense of far by
citation and close in content:

- **symplectic geometry ← symplectic integrators** (numerical analysis): 3
  of its 20 already met in 2022–2025, the most of any area;
- **operator algebras ← hyperplane-arrangement face semigroups**
  (Bidigare–Hanlon–Rockmore, Brown), the random-walk-on-semigroups thread;
- **numerical analysis and optimization ← persistent homology** (applied
  topology, still absent from both areas' citations at 2021);
- **statistics ← electrical impedance tomography** and the factorization
  method (PDE inverse problems);
- **group theory ← harmonic analysis on nilpotent groups**;
- **category theory ← derived categories of Grassmann flops and Enriques
  surfaces** (algebraic geometry).

Some lists are long on textbooks (representation theory, number theory,
algebraic geometry), the Phase 22 pattern: a textbook is cited by many
fields, so nearly every area counts as unconnected to it.

### What this establishes

- The Phase 23 result holds at a second cutoff, with a larger effect
  (+0.175 vs +0.111). Similarity is the strongest term in the model.
- The lists can be made and are readable. Roughly a third of the entries
  looked at are word collisions or bad records, a third are textbooks, and a
  third are candidate bridges a specialist could judge in minutes.

### What it does not establish

- Whether any listed pair is worth a mathematician's time: that is the
  reading the user offered to do.
- Forward outcomes: 2022–2025 references are too sparse for a test.

### Next

Read the lists for one or two areas. If the candidate-bridge third holds up,
the obvious fix for the collision third is a text model that sees meaning
rather than words (sentence embeddings of the abstracts in place of TF-IDF),
and for the textbook third a cap on how many areas already cite a work.
