# Phase 11 — which tools will enter which areas? (arXiv + OpenAlex)

**Pre-registration.** Everything in this file is written and committed before
any Phase 11 data is downloaded beyond the feasibility samples described
below. Results go in a section appended below; nothing above that section
changes.

## Why

Phases 5–10 asked whether a map of Mathlib's statements knows where rare
jumps between areas happen. The signal was real and small (Phase 10, 0.54),
and popularity beat it every time. The decade's landmark results suggest why.
A great jump brings a tool that is *ordinary at home* into an area that has
never used it: modular forms into sphere packing, Hodge theory into
combinatorics, eigenvalues into Boolean functions. The ends are popular. What
is rare is the *pairing*.

Phase 11 moves from lemmas to papers and asks the question at that level.
Take every popular cited work (a **tool**) and every area of mathematics that
has never cited it. Which of those empty cells fill in over the next five
years, and does a tool's **demand profile** (the text of the papers that have
used it) predict that beyond popularity and area-to-area citation habits?

## Feasibility, seen before this file

- zbMATH Open's subject codes are too slow to download (about 8 days for a
  polite single stream; 6 of 8 parallel requests were refused). arXiv
  categories are used instead: the author picks them.
- Samples: 403 arXiv math records (March 2016 datestamps); 46% carry MSC codes,
  19% a journal DOI. Of 200 looked up in OpenAlex by arXiv DOI, 141 were
  found and 97 had references; 29 of 31 journal DOIs had references.
- No score of any kind was computed.

## Data

- **Papers**: arXiv records whose *primary* category is `math.*`, excluding
  `math.GM` (general) and `math.HO` (history). A paper's **area** is its
  primary category. Its **date** is the year of its arXiv identifier. Harvested
  from arXiv's OAI-PMH service (`set=math`, `metadataPrefix=arXiv`).
- **References**: from OpenAlex, the union of the referenced works of the
  paper's arXiv DOI (`10.48550/arXiv.<id>`) and its journal DOI, if any. Papers
  with no references found are kept as papers but cite nothing.
- **Tools**: any OpenAlex work cited by at least one paper. A book, a pre-arXiv
  paper and an arXiv paper all count.
- **Text**: the paper's arXiv title and abstract.

## Windows

| | history | outcome |
|---|---|---|
| **fit** | papers dated ≤ 2010 | 2011–2015 |
| **test** | papers dated ≤ 2015 | 2016–2020 |

Every feature is computed from the history window only.

## The cells

For a window: a **cell** is (tool T, area A) with
- T cited by at least 20 history papers (popular);
- no history paper in A citing T (absent);
- T not itself an arXiv paper whose primary area is A.

A cell is **positive** if at least 2 distinct outcome papers in A cite T.

## Features (history only)

| feature | meaning |
|---|---|
| `cites` | log(1 + history papers citing T) |
| `recent` | log(1 + those from the last 5 history years) |
| `reach` | number of areas with a paper citing T |
| `size` | log(1 + A's papers in the last 5 history years) |
| `flow` | Σ over areas B of (share of T's citers in B) × (share of A's citations, last 5 history years, that go to arXiv papers whose primary area is B) |
| **`shape`** | cosine between the TF-IDF of the titles and abstracts of T's citers, and the TF-IDF of A's titles and abstracts in the last 5 history years |

TF-IDF: scikit-learn `TfidfVectorizer(sublinear_tf=True, min_df=5,
max_df=0.5, stop_words="english")`, fitted on the history window's texts,
each profile the mean of its papers' L2-normalised rows.

## Models and tests

Two logistic regressions (standardised features, L2, C = 1, scikit-learn
defaults otherwise) are fitted on the **fit** window's cells and scored on the
**test** window's cells, with no refitting:

- **BASE**: cites, recent, reach, size, flow.
- **BASE+SHAPE**: the same plus shape.

### H1 (primary) — does a tool's demand profile predict where it goes next?

AUC(BASE+SHAPE) − AUC(BASE) on the test cells. 95% interval from 1,000
bootstrap draws resampling tools. Seed **20261002**.

| outcome | verdict |
|---|---|
| interval above 0, difference ≥ 0.01 | **the demand profile adds to popularity and citation habits** |
| interval above 0, difference < 0.01 | **detectable, too small to matter** |
| interval contains 0 | **no measurable difference** |
| interval below 0 | **the demand profile hurts** |

Prediction: the demand profile adds.

### Reported, not tested

- AUC of each feature alone, and of BASE, on the test cells.
- Positives among the top 1,000 and 10,000 test cells of each model, against
  chance.
- H1's difference within quintiles of BASE's score.
- **Landmark cells.** For each of these papers, every test cell (T, its
  area) where T is one of its references: the cell's percentile rank under
  BASE and under BASE+SHAPE.
  - Viazovska, sphere packing in dimension 8, arXiv:1603.04246
  - Cohn, Kumar, Miller, Radchenko, Viazovska, dimension 24, arXiv:1603.06518
  - Croot, Lev, Pach, arXiv:1605.01506
  - Ellenberg, Gijswijt, arXiv:1605.09223
  - Huang, sensitivity conjecture, arXiv:1907.00847

  A landmark whose references OpenAlex does not have is reported as missing.
- Coverage: papers per year, share with references, per area.

## Out of scope

- zbMATH, Mathlib, encoder B.
- Any second threshold, window or feature set. Anything the results suggest is
  reported as exploratory in its own section.

## Run and budget

One small AWS worker, self-terminating, smoke pass first (one month of arXiv,
every stage). It harvests arXiv (polite, following the server's retry-after),
looks up OpenAlex by DOI, and runs the analysis. Estimated under 12 hours and
under $5; ceiling $15. The role, instance profile, security group, instance
and task object are torn down and the teardown verified.

---
