# Phase 24 — would the forecast have pointed at known breakthroughs?

**Pre-registration.** Everything in this file, the curated list
(`curated.json`) and the eligibility check (`eligible.json`) are written and
committed before any Phase 24 score is computed. Results go in a section
appended below; nothing above that section changes.

## Why

Phases 21–23 showed that content similarity helps rank which (work, area)
pairs become important jumps, most of all for surprising jumps (Phase 23:
within-route AUC +0.111 [+0.075, +0.147]). But "important jump" is a mechanical
label (at least 5 target-area papers citing the work within 10 years), and
Phase 23's hits included textbooks and one research programme counted four
times.

The project's goal is the breakthroughs mathematicians themselves recognise
(standing memory: *model breakthroughs, not all of math*). Phase 24 asks
directly: take a list of well-documented cross-field jumps of 2006–2015,
chosen from the history of mathematics and not from our data, and check where
the 2005 forecast would have ranked each one.

Already seen before this file was written: all results of Phases 11–23,
including Phase 23's top 100 (so backward SDEs and Knutson–Tao are left off
the list).

## The curated list (`curated.json`)

27 jumps, one per research programme. Each is (a work that existed by 2005,
the arXiv area it reached in 2006–2015), with the documented reason. Examples:
Lyons's rough paths reaching PDE (Hairer's KPZ and regularity structures);
o-minimality reaching number theory (Pila–Zannier); the Hitchin fibration
reaching the Langlands programme (Ngô's fundamental lemma); optimal transport
reaching metric geometry (Lott–Villani–Sturm); model categories reaching logic
(homotopy type theory). The list was fixed from memory of the literature
before any lookup in our data. One entry (Deift–Zhou → representation theory)
was removed before any lookup, as too weakly documented.

## Eligibility (`scripts/resolve-phase24.py`, `eligible.json`)

Using papers **up to 2005 only** (no outcomes, no scores):

- **Work id**: OpenAlex title search; ids whose normalised title matches (the
  first 30 characters, or the whole title if shorter) within 3 years of the
  curated year (`openalex-ids.json`). The id used is the one with the most
  corpus citers up to 2005.
- **Eligible**: at least 5 citers up to 2005 (Phase 20's candidate rule), and
  no citer whose primary area is the target (not yet connected).

**12 of 27 are eligible**, 12 distinct programmes:

| work | target |
|---|---|
| Lyons, Differential equations driven by rough signals (1998) | math.AP |
| Otto, The geometry of dissipative evolution equations (2001) | math.MG |
| Fomin–Zelevinsky, Cluster algebras I (2002) | math.GT |
| Johnson–Lindenstrauss, Extensions of Lipschitz mappings (1984) | math.NA |
| Chen–Donoho–Saunders, Atomic decomposition by basis pursuit (1998) | math.PR |
| van den Dries, Tame topology and o-minimal structures (1998) | math.NT |
| Szemerédi, Regular partitions of graphs (1978) | math.LO |
| Hitchin, Stable bundles and integrable systems (1987) | math.NT |
| Gromov, Endomorphisms of symbolic algebraic varieties (1999) | math.DS |
| Connes, Classification of injective factors (1976) | math.LO |
| Tibshirani, Regression shrinkage and selection via the lasso (1996) | math.OC |
| Wolff, Local smoothing type estimates on L^p for large p (2000) | math.NT |

The 15 left out were already connected by 2005 (6: Lasserre → AG, Host–Kra →
NT, Diaconis–Sturmfels → ST, Macdonald → PR, Wolff's Kakeya bound → CO,
Burago–Burago–Ivanov → PR), too little cited on arXiv by 2005 (6: sum-product,
Combinatorial Nullstellensatz, Benjamini–Schramm, Sznitman, Vapnik–Chervonenkis,
Gleason), or not found (3) in OpenAlex's records cited by the corpus (Hovey's
*Model categories*, persistence, Erdős–Rényi). OpenAlex's daily budget ran
out during lookups; the ids already returned are cached in
`openalex-ids.json`, and no entry was added or changed after that.

## Build and model

Phase 23's build, unchanged: Phase 11's arXiv papers and OpenAlex references
up to 2005, co-citation table, span, TF-IDF + 256-dimension SVD, similarity.
Population: **every unconnected (work, area) pair at 2005** (work with at
least 5 citers, no citer in the area), with no span or label filter.

Models (logistic, as Phases 21–23): BASE = log citers, log recent citers,
log area size, span, breadth, home and target area dummies; BASE+SIM adds
similarity. Outcome: important jump (at least 5 area papers citing the work in
2006–2015). Scores are out-of-fold, 5 folds grouped by work, so a curated
pair's own outcome is never used to score it. Seed **20261014**.

Each curated pair's **percentile** = share of all candidate pairs scoring
below it (ties half), under BASE, BASE+SIM and similarity alone.

## Tests

### H1 (primary) — would the forecast have pointed at them?

Median BASE+SIM percentile over the eligible curated pairs:

| median percentile | verdict |
|---|---|
| ≥ 99 | **points at known breakthroughs** |
| 90–99 | **flags them, not sharply** |
| 50–90 | **weak** |
| < 50 | **misses them** |

Fewer than 8 curated pairs in the population: **underpowered**. Prediction:
flags them, not sharply.

### H2 — does similarity lift them?

For each pair, percentile(BASE+SIM) − percentile(BASE). Exact two-sided sign
test: p < 0.05 with more improved than worsened is **similarity lifts known
breakthroughs**; p < 0.05 the other way is **similarity lowers them**;
otherwise **no clear effect**. The mean difference and a 95% interval
(1,000 bootstrap draws over pairs) are reported. Prediction: no clear effect
(12 pairs is little for a sign test).

### Reported, not tested

- For each curated pair: home area, citers, span, similarity, label
  (knocking / next door / surprising), target papers citing it 2006–2015,
  whether it counts as an important jump in our data, rank and percentile
  under each score, percentile within its target area.
- Curated pairs in the top 100, top 1,000, top 1% and top 10%.
- Comparison: the median percentile of all important jumps, and of the
  surprising important jumps, under each score.

## Out of scope

Any other cutoff, list, or model. The 15 ineligible entries are not scored.

## Run and budget

One AWS m6i.4xlarge via the Phase 12 launcher (`USERDATA=phase24`),
self-terminating, idle-log watchdog, 2-hour power-off; smoke pass first. About
10 minutes, under $0.30. Teardown verified.

---

## Results

*Appended after the run. Nothing above this line changed.* Run
`noema-p12-20260930-203814` (`USERDATA=phase24`), one m6i.4xlarge, about 3
minutes, under $0.10, torn down and verified. Numbers from
`results/phase24.json`.

Population: 401,302 unconnected pairs at 2005, 2,528 important jumps. All 12
eligible curated pairs were in it.

### Verdict

| test | result | verdict |
|---|---|---|
| **H1** | median BASE+SIM percentile **92.3** (BASE 86.5, similarity alone 94.3) | **flags them, not sharply** (as predicted) |
| **H2** | similarity raised **11 of 12**, lowered 1; sign test p = 0.006; mean +9.2 points [+2.7, +18.4] | **similarity lifts known breakthroughs** (predicted: no clear effect) |

Curated pairs near the top (BASE / BASE+SIM / similarity alone): top 100
0 / 0 / 0; top 1,000 0 / 1 / 1; top 1% (4,013) 2 / 4 / 2; top 10% 5 / 6 / 8.

For comparison, the median BASE+SIM percentile is 97.2 for all important jumps
and 90.0 for surprising important jumps. The curated breakthroughs sit with
the surprising jumps, below the typical jump.

### The twelve

| work → target | label | papers 2006–15 | BASE | BASE+SIM | sim alone |
|---|---|---:|---:|---:|---:|
| basis pursuit → PR | knocking | 4 | 99.7 | **100.0** (rank 104) | 99.1 |
| rough paths → AP | next door | 9 | 96.2 | **99.6** | 98.2 |
| o-minimality → NT | knocking | 5 | 99.1 | **99.5** | 97.1 |
| Johnson–Lindenstrauss → NA | next door | 5 | 98.5 | **99.3** | 94.7 |
| lasso → OC | surprising | **83** | 84.9 | **97.6** | 99.9 |
| Hitchin → NT | next door | 0 | 96.3 | 96.8 | 94.0 |
| Gromov sofic → DS | knocking | 17 | 74.2 | 87.9 | 87.1 |
| cluster algebras → GT | knocking | 6 | 88.1 | 87.7 | 76.9 |
| Otto → MG | knocking | 7 | 74.0 | 86.5 | 91.7 |
| Szemerédi regularity → LO | surprising | 1 | 32.9 | **83.4** | 94.8 |
| Wolff local smoothing → NT | surprising | 1 | 80.1 | 81.6 | 64.7 |
| Connes injective factors → LO | surprising | 1 | 27.0 | 42.1 | 72.0 |

### What this establishes

- **Similarity moves real breakthroughs up.** 11 of 12 moved up, with the
  largest gains on the surprising ones: Szemerédi → logic from the 33rd to the
  83rd percentile, the lasso → optimization from 85th to 98th. This is the
  first check against breakthroughs chosen from the history of mathematics,
  not from our own jump label, and it agrees with Phases 21–23.
- **But not sharply enough to be a shortlist.** The typical breakthrough
  lands in the top 8% of 401,302 pairs, about 31,000 pairs deep. Four of 12
  make the top 1% (about 4,000 pairs); none makes the top 100.
- **Similarity alone does as well as the full model on these** (median 94.3
  vs 92.3), because BASE rewards works already close to the target, and the
  real breakthroughs are often not.

### What it does not establish

- Twelve pairs, one cutoff, and a list drawn from one person's memory of the
  literature. 15 of 27 could not be tested (already connected, too few arXiv
  citers by 2005, or not found).
- **Our jump label misses some real breakthroughs.** 5 of the 12 do not count
  as important jumps in our data. Hitchin → number theory has 0 target-area
  papers because Ngô's work is filed under algebraic geometry. The arXiv
  primary category is a coarse stand-in for "which community adopted it".

### Next

The ranking is too coarse at the top. Two ways to sharpen it: a finer grain
than 28 arXiv areas (so "target" means a community, not a whole field), or a
second signal that says *when* a pair is ripe (for example, a rise in
similarity over the years before the jump).
