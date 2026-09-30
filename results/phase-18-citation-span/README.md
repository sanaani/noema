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
