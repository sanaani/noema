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

## Results

*Appended after the run. Nothing above this line changed.* Numbers from
`results/phase11.json`, written by `scripts/run-phase11.py analyze` on one AWS
m6i.4xlarge.

**Data.** 597,860 arXiv papers with a `math.*` primary category (excluding
GM and HO), 28 areas. 526,506 of them were found in the OpenAlex snapshot of
2026-09-23; 303,714 have references. Papers with references: 61–64% in the
1990s, 75–81% in 1998–2013, 64–66% in 2016–2019, then falling (21% in 2022,
5% in 2025), which does not reach either window.

| window | history papers | popular tools | cells | positives |
|---|---:|---:|---:|---:|
| fit (≤ 2010 → 2011–15) | 98,660 | 6,578 | 148,381 | 2,359 |
| test (≤ 2015 → 2016–20) | 211,769 | 17,647 | 403,587 | 3,330 |

### Verdict

| test | prediction | result | verdict |
|---|---|---|---|
| **H1** AUC(BASE+SHAPE) − AUC(BASE) | the demand profile adds | 0.870 − 0.813 = **+0.057** [+0.053, +0.062] | **the demand profile adds to popularity and citation habits** |

For the first time in the project, a pre-registered test of "where will a
connection appear" passes by a clear margin over popularity.

### Reported, not tested

**Each feature alone** (AUC on the test cells): shape **0.846**, flow 0.744,
size 0.656, reach 0.652, recent 0.647, cites 0.600. Shape alone beats all
five BASE features combined (0.813).

**Short lists.** Positives among the top-ranked test cells:

| | top 1,000 | top 10,000 |
|---|---:|---:|
| BASE+SHAPE | **245** | **1,034** |
| BASE | 87 | 610 |
| chance | 8 | 83 |

A quarter of BASE+SHAPE's top 1,000 cells were filled within five years, 30×
chance and 2.8× BASE.

**Within equal BASE scores**, shape still adds 0.13–0.21 in every quintile
(BASE 0.55–0.65, BASE+SHAPE 0.77–0.79). It is not a proxy for popularity or
citation habits.

**Coefficients** (standardised, BASE+SHAPE): shape +1.00, recent +1.13, cites
−0.97, size +0.51, flow +0.34, reach +0.23. Holding recent use fixed, *more*
total citations predict *less* spread: established tools have already gone
where they will go.

**Landmarks: none tested.** Every landmark paper was found, but none of its
references forms a test cell:
- Viazovska (both papers) and Croot–Lev–Pach are filed under **math.NT**,
  the home area of the modular-form and polynomial tools they use. At the level
  of the author's primary category, the jump is invisible: the paper is filed
  where the tool lives, not where the problem lives (sphere packing, cap sets).
- Ellenberg–Gijswijt (math.CO, 5 references) cites nothing that is both
  popular (≥ 20 citing papers) and new to math.CO.
- Huang (math.CO): OpenAlex holds no references for it.

### What this establishes

- On 2016–2020 arXiv mathematics, a model fitted only on 2011–2015 predicts
  which popular works will be cited in areas that have never cited them. The
  text of the papers that already use a tool, compared with the text of the
  target area, adds 0.057 AUC over popularity, recency, breadth, area size and
  area-to-area citation habits, and nearly triples the hits in the top 1,000.

### What it does not establish

- **That shape sees deep structure.** A cell is "absent" by *primary*
  category only. Papers cross-listed in area A (A as a secondary category) may
  already cite the tool, and their abstracts would make the tool's profile
  look like A. Shape may be partly detecting that the tool is already used
  next door. This was not controlled for; it is the first thing to check.
- **Anything about landmark jumps.** None could be scored, for the reasons
  above.
- **That the cells are surprising.** A positive needs only two papers in five
  years; many will be routine spread (a standard reference reaching a
  neighbouring area).

### Deviations

- **References came from the OpenAlex snapshot, not the API.** The first
  worker harvested arXiv, then the OpenAlex API returned 429 with a 17-hour
  Retry-After at 40,000 of 717,075 DOIs. The worker obeyed it and idled for
  about 6.5 hours before it was noticed and torn down. The `snapshot` stage
  reads the same records (`id`, `doi`, `referenced_works`) from the quarterly
  parquet release of 2026-09-23.
- **Two launches failed their smoke pass**, in about a minute each: DuckDB
  needed a home directory under cloud-init, and the smoke read the three
  oldest snapshot files, which hold none of these papers. The smoke now reads
  the newest three and fails if the join finds nothing.
- **Shape is computed in chunks of 2,000 tools.** The result is the same
  cosine as registered; only the memory use changes.
- **The found-count log was wrong** in both reference stages (it counted every
  paper). The data written was not affected.
- Guardrails added after the idle worker: requested waits over 10 minutes
  fail the job, and an on-worker watchdog stops a job whose log is idle for 30
  minutes.

### Cost and teardown

About $4 in total: roughly $3.60 for the first worker (m6i.2xlarge, about
9.3 hours, 6.5 of them idle), then three m6i.4xlarge launches of 2, 2 and 17
minutes. Every instance, role, instance profile, security group and task
object was deleted, and the deletion was verified.

### Exploratory: is shape only seeing use next door? (planned before the run)

*Written and committed before the check was run. Not pre-registered with
the phase; reported as exploratory, as the rules above require.*

A cell is empty by *primary* category. A paper listed under area A as a
*secondary* category may already cite the tool, and its abstract would make
the tool's profile look like A. Two checks, same data, windows, models and
seed + 1 (`run-phase11.py analyze --check-xlist`):

- **X1.** Add `xlist` = log(1 + history papers citing T with A as a secondary
  category) to BASE. Compare BASE+X with BASE+X+SHAPE.
- **X2.** Keep only cells with no such paper at all (xlist = 0), in both
  windows. Compare BASE with BASE+SHAPE there.

Reading: if shape's gain stays at 0.03 or more with its interval above 0 in
both, shape is not mainly detecting next-door use. If it falls near 0, it
was.
