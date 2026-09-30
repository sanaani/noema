# Phase 18 — the longest-reaching citations up to 2015, and which caught on

**Pre-registration.** Everything in this file is written and committed before
any Phase 18 number is computed. Results go in a section appended below;
nothing above that section changes.

## Why

Phases 11–16 modelled all of arXiv math, so ordinary papers set the target.
The project cares about rare, surprising jumps. Phase 17 found that in the
five landmark papers the decisive idea arrives through **one reference from
far away**, or through none. So Phase 18 defines groundbreaking from the
citation graph itself, before a hard cutoff (end of 2015):

> a citation that carries a work into an area far from where it has been used,
> and that the new area then keeps using.

It also tests an assumption this rests on: that areas which rarely cite each
other are also far apart in content. They may not be. Ideas from different
fields can say similar things in different words, and that case (far by
citations, close by content) is a hidden bridge.

Already seen before this file was written: the results of Phases 11–17,
including Phase 17's landmark bibliographies. No Phase 18 number has been
looked at.

## Data

Phase 11's arXiv math papers (1992–2026) and their OpenAlex references. A
paper's **area** is its arXiv primary category (28 areas). A **work** is
anything cited, identified by its OpenAlex id. Only papers up to 2015 are used
to learn anything (the co-citation table, the text model, the time window,
the top 1% threshold). Later papers are used only to judge the landmarks and,
if needed, for the peek below.

## Definitions

- **Arrival.** For a work W and an area A, W *arrives* in A in the first year
  y in which an A-paper cites W. The **arriving papers** are the A-papers
  citing W in year y. A cell (W, A, y) is **eligible** if W has at least **5
  prior citers** (papers citing W in years before y; none are in A by
  construction). Five gives W a usage profile to be far from.
- **Co-citation table.** From citations by papers up to 2015: for areas A and
  B, F[A | B] = of the works cited by some B-paper, the share also cited by
  some A-paper. It measures how much two areas use the same works, from data,
  not from a map of fields.
- **Span** of a cell (the citation distance):

  span = −log₂ Σ_B s(B) · F[A | B]

  where s(B) is the share of W's prior citers in area B. It is how surprising
  it is, in bits, for area A to use a work used the way W has been used. A
  work already cited from many areas (a handbook) has a spread-out s that
  includes areas close to A, so its span into A is low: generic references are
  discounted by the formula, without a separate rule.
- **Content similarity** (the content distance, turned around): titles and
  abstracts as TF-IDF (Phase 11's settings), reduced to 256 dimensions by
  truncated SVD, both fitted on papers up to 2015 only. Similarity = cosine
  between the mean vector of the arriving papers and the mean vector of W's
  prior citers.
- **Follow-on**: A-papers citing W in the years after y. A cell **caught on**
  within T years if at least **5** follow-on A-papers cite W in years y+1 to
  y+T (Phase 13's "took hold" count).

## The time window T, from the data

T is not chosen; it is measured on the earliest cohort:

- Cohort: eligible cells arriving in 1998–2002. Each can be followed for 13
  years without passing 2015 (2002 + 13).
- Among cohort cells that caught on within 13 years, the year (after arrival)
  in which each reached its fifth follow-on paper.
- **T = the 80th percentile of that year**: the wait after which four in
  five routes that catch on have done so. Median and 90th percentile are
  reported alongside.

Cells arriving after 2015 − T cannot be judged by 2015. They are **not yet
judged**, not failures, and are left out.

## Populations

- **Learn window** (primary, no peek): eligible cells arriving in years up to
  2015 − T, caught-on judged by 2015.
- **Top 1%**: the learn window's cells with the highest span (threshold: the
  99th percentile of span over the learn window).
- **Groundbreaking**: top 1% and caught on.
- **Peek** (used only if needed, see H2): eligible cells arriving up to 2015,
  caught-on judged over y+1 to y+T even when that passes 2015 (the arXiv data
  run to 2026, so arrivals up to 2026 − T). Later citations are used only to
  judge catching on; every feature is computed from years before y, with
  models fitted on papers up to 2015. Results from the peek are labelled as
  such.

## Tests

Seed **20261008**. Intervals are 95%, from 1,000 bootstrap draws resampling
works.

### H1 — do citation distance and content distance agree?

Spearman correlation between span and content similarity over the learn
window's eligible cells (a negative value means: farther by citation, less
similar in content).

| \|rho\| | verdict |
|---|---|
| ≥ 0.5 | **mostly the same thing** |
| 0.2 – 0.5 | **related but different** |
| < 0.2 | **different things** |

Prediction: related but different.

### H2 (primary) — among the longest-reaching arrivals, does content closeness pick the ones that catch on?

On the top 1%, positive = caught on. Logistic regression, 5-fold
cross-validation grouped by work (Phase 13's code), BASE = (log prior citers,
arrival year, log papers in A that year, span) against BASE + content
similarity. AUC(BASE+CONTENT) − AUC(BASE):

| outcome | verdict |
|---|---|
| interval above 0, difference ≥ 0.03 | **content closeness picks the far routes that catch on** |
| interval above 0, difference < 0.03 | **detectable, small** |
| interval contains 0 | **no measurable help** |
| interval below 0 | **content closeness hurts** |

Population: the learn window's top 1% if it holds ≥ 100 cells that caught on.
Otherwise the peek's top 1% (threshold recomputed on the peek), and the report
says so. Fewer than 100 there too: **underpowered**. Prediction: detectable,
small.

### Reported, not tested

- The cohort's time-to-catch-on distribution (years 1–13) and T.
- Catch-on rate by span decile, and in the top 1%.
- Area level: Spearman between −log₂ of the symmetric co-citation
  (mean of F[A | B] and F[B | A]) and the cosine of the two areas' mean
  vectors, over the 378 area pairs.
- **Hidden bridges**: top-1% cells whose content similarity is at or above the
  learn window's median; how many, and their catch-on rate against the other
  top-1% cells.
- Content similarity's AUC alone on the H2 population.
- The **50 groundbreaking cells with the highest span**: work, the area most
  of its prior citers are in, target area, arrival year, first arriving paper,
  follow-on count, span, content similarity. Titles of works that are not
  arXiv papers are looked up from OpenAlex after the run.

### The landmarks (reported, not tested)

For each of the five landmarks (Viazovska; Cohn–Kumar–Miller–Radchenko–
Viazovska; Croot–Lev–Pach; Ellenberg–Gijswijt; Huang), every reference in
the data is scored as a cell (W, landmark's area, landmark's year) with prior
citers before that year: span, content similarity (the landmark's own vector
against W's prior citers), and whether the landmark is among W's first
arrivals in the area. Reported:

- where the **decisive reference** ranks by span within its landmark's
  bibliography, and its span percentile among all eligible cells arriving
  the same year. Decisive references, fixed now from Phase 17:
  - Viazovska and CKMRV: Zagier's *Elliptic Modular Forms and Their
    Applications* (W116915404) and Diamond–Shurman's *A First Course in
    Modular Forms* (W1537136047);
  - Ellenberg–Gijswijt: Croot–Lev–Pach (W2347034157);
  - Huang: Fisk's *A very short proof of Cauchy's interlace theorem*
    (math/0502408, W2156858248). Huang has no OpenAlex references, so this is
    his only scored reference;
  - Croot–Lev–Pach: none (the polynomial method is not cited).
- The same with the landmark's area set to its first math secondary category
  (Viazovska's papers are filed under number theory, cross-listed to metric
  geometry).

## Out of scope

- Any other grain, cutoff, threshold or feature. Anything the results suggest
  is reported as exploratory in its own section.

## Run and budget

One AWS m6i.4xlarge, self-terminating, idle-log watchdog, 2-hour power-off;
smoke pass first (every 4th paper, small SVD). Estimated 20–40 minutes, under
$1; ceiling $3. Teardown verified.

---

## Results

*Appended after the run. Nothing above this line changed.* Run
`noema-p12-20260930-134915` (the Phase 12 launcher with `USERDATA=phase18`),
one m6i.4xlarge, 6 minutes, about $0.10, torn down and verified. Numbers from
`results/phase18.json`; titles of non-arXiv works looked up from OpenAlex in
`results/names.json`.

### The time window, measured

2,948 cells arrived in 1998–2002; 1,181 caught on within 13 years. Years from
arrival to the fifth follow-on paper:

| years | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cells | 7 | 69 | 93 | 136 | 118 | 129 | 122 | 124 | 99 | 78 | 85 | 57 | 64 |

Median 7 years, 80th percentile **T = 10**, 90th percentile 12. Catching on is
slow and spread out: no single year dominates. With T = 10, the learn window
is arrivals up to 2005.

### Sample size: too small

197,770 eligible cells in all years, but only 9,699 in the learn window
(arrivals 1994–2005; arXiv math was small then). Its top 1% is 97 cells, of
which **6 caught on**. The peek (arrivals up to 2015, judged to 2025) has 867
top-1% cells and **12 caught on**. Both are far under 100.

### Verdict

| test | result | verdict |
|---|---|---|
| **H1** span vs content similarity, cell level | Spearman −0.18 | **different things** |
| **H2** content closeness among the top 1% (peek) | −0.012 [−0.132, +0.078], 12 caught on | **underpowered** |

H1's prediction (related but different) was slightly off: at the level of
single citations, how far apart two areas are by citation says little about
how similar the papers are in content.

### Reported, not tested

- **Area level**: Spearman −0.77 between co-citation distance and content
  distance over the 378 area pairs. Areas that rarely share references also
  write about different things; individual long-reaching citations often do
  not.
- **Catch-on falls with span** (learn window, lowest to highest decile): 30%,
  33%, 29%, 31%, 28%, 23%, 25%, 18%, 18%, 12%; top 1%: 6%. Long reaches are
  rarely followed.
- **Hidden bridges**: 35 of the 97 top-1% cells are at or above median content
  similarity. 4 of them caught on (11%), against 2 of the other 62 (3%). The
  direction the hypothesis expects, on six cells.
- **Groundbreaking cells** (peek, 12 in all, highest span first):

  | work | from → to | arrived | follow-on |
  |---|---|---:|---:|
  | Santos, *Higher Lawrence configurations* | OC → AC | 2013 | 5 |
  | Kahle, *Random Geometric Complexes* | PR → AT | 2015 | 5 |
  | Kallenberg, *Foundations of Modern Probability* | PR → LO | 2009 | 5 |
  | Vapnik–Chervonenkis, *Uniform Convergence of Relative Frequencies* | ST → LO | 2010 | 7 |
  | Joyal, *Une théorie combinatoire des séries formelles* (species) | CO → CT | 2007 | 10 |
  | Harary, *Graph Theory* | CO → GN | 2008 | 5 |
  | Geiger–Meek–Sturmfels, *On the toric algebra of graphical models* | ST → AC | 2008 | 7 |
  | van den Dries–Miller, *Geometric categories and o-minimal structures* | AG → LO | 2005 | 11 |
  | Furstenberg, *Recurrence in Ergodic Theory and Combinatorial Number Theory* | DS → GN | 2014 | 5 |
  | Écalle, *Fonctions analysables et … conjecture de Dulac* | DS → LO | 2011 | 5 |
  | Rudin, *Principles of Mathematical Analysis* | CA → LO | 2011 | 6 |
  | Tao, *Norm convergence of multiple ergodic averages* | DS → LO | 2009 | 7 |

  Most are recognised cross-field programmes, not textbooks: VC dimension
  entering model theory (NIP theories), Tao's finitary ergodic theorem
  entering proof mining, random complexes entering topological data analysis,
  graphical models entering algebraic statistics, Joyal's species entering
  category theory, Écalle's transseries entering logic. Three are generic
  textbooks (Kallenberg, Harary, Rudin).

### The landmarks

Rank of each reference by span within its own bibliography (references with
at least 5 prior citers), and the span's percentile among all cells arriving
the same year.

| landmark | area used | decisive reference | rank | percentile |
|---|---|---|---:|---:|
| Viazovska | NT (primary) | Zagier; Diamond–Shurman | 12, 14 of 15 | 0th |
| Viazovska | MG (secondary) | Zagier; Diamond–Shurman | **3, 2 of 15** | 94th, 95th |
| CKMRV | NT (primary) | Zagier | 10 of 11 | 0th |
| CKMRV | MG (secondary) | Zagier | **1 of 11** | 94th |
| Ellenberg–Gijswijt | CO | Croot–Lev–Pach | not scored (no prior citers) | — |
| Huang | CO | Fisk (interlacing) | 1 of 1 | 4th |
| Croot–Lev–Pach | — | none cited | — | — |

With sphere packing (MG) as the area, the five highest-span references in
Viazovska's bibliography are all modular-form or theta-function works (Borcherds,
Diamond–Shurman, Zagier, Mumford's *Tata Lectures on Theta*, the Selberg
trace formula): the greatest-span rule picks out the bridge exactly. Filed
under number theory, as arXiv files it, the same references are home ground.
Huang's interlacing reference had already been used in combinatorics, so it
is not far.

### What this establishes

- **Catching on takes about 10 years** (80% of routes that catch on have done
  so by then; median 7). A window chosen by hand at 5 years would have missed
  most of them.
- **Distance by citation is not distance by content** for single citations
  (Spearman −0.18), though the two agree for whole areas (−0.77). The two
  must be measured separately.
- **The greatest-span reference can be the decisive one**: for both
  sphere-packing papers, scored against sphere packing, the modular-form
  references rank at or near the top of the bibliography.
- **The longest reaches that caught on look like real cross-field
  programmes**, not the textbook noise of Phases 15–16.

### What it does not establish

- **Whether content closeness predicts which far routes catch on (H2).**
  Twelve cases: underpowered. The citing side is arXiv math only, and arXiv
  math before 2006 is small; a 10-year window leaves little to judge by 2015.
- **Label dependence.** The sphere-packing result turns on which arXiv
  category is the paper's area. The primary category (number theory) hides
  the bridge. A rule for choosing the area was not fixed in advance beyond
  "primary, then first secondary".
- **Huang and Croot–Lev–Pach**: the rule cannot see a decisive idea that is
  cited from nearby or not cited at all.

### Next, to fix the sample size

The graph needs more citing papers before 2016, not more years: all of
OpenAlex's mathematics (journals, not only arXiv), labelled by OpenAlex
subfield or MSC. That is roughly ten times the papers in the learn window.
