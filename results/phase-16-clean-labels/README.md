# Phase 16 — Phase 15 without broken records and off-field topics

**Pre-registration.** Everything in this file is written and committed before
any Phase 16 score is computed. Results go in a section appended below;
nothing above that section changes.

## Why

Phase 15 found that shape's top 1,000 cold topic cells held 75 cold jumps
(BASE: 28, chance 0.28), but its reading lists showed two kinds of label
noise:

- **Broken tool records.** All of shape's top 20 were one OpenAlex record
  (`W4285719527`) that OpenAlex no longer serves and whose 577 history citers
  span unrelated fields: a catch-all that unrelated references were resolved
  to.
- **Off-field topics.** OpenAlex's topic classifier covers all of science,
  and some arXiv math papers get topics like "Species Distribution and Climate
  Change". A jump into such a topic may be a jump into a wrong label.

Phase 16 asks whether the lift survives when both are removed.

Already seen before this file was written: Phase 15's published results
(including its two reading lists of 20 cells) and the OpenAlex metadata
below. No new outcome has been looked at.

## Labels

`scripts/phase16-labels.py` fetched, from the OpenAlex API, metadata for
Phase 15's 2,241 popular tools and all 4,147 topics (`data/tools.json`,
`data/topic-fields.json`). Metadata only: titles, types and fields.

- **Broken tool**: OpenAlex no longer serves the record, or serves it with no
  title. 37 tools. (Record types were considered and rejected as a rule: many
  real textbooks are typed "book-review" or "other".)
- **Near-math topic**: the topic's OpenAlex field is Mathematics, Computer
  Science, Physics and Astronomy, Engineering, Decision Sciences, or
  Economics, Econometrics and Finance. 1,171 of 4,147 topics. These fields hold
  93% of the papers by primary topic.
- **Mathematics topic**: field Mathematics. 82 topics.

## Cells and model

Exactly Phase 15's: the same cells, ladder, features, window (history ≤ 2006,
outcome 2007–2021) and model, 5-fold cross-validation grouped by tool. Only
the cold (rung 6) cells are used. The model is **refitted** on each
population below. Seed **20261007**.

| population | cold cells kept |
|---|---|
| **B** (primary) | tool not broken, target topic near-math |
| A | tool not broken |
| C | tool not broken, target topic in Mathematics |

## Tests

### H1 (primary) — does shape still find cold jumps on B?

AUC(BASE+SHAPE) − AUC(BASE) on B, positive = cold jump, 95% interval from
1,000 bootstrap draws resampling tools. Verdict table as Phase 15: interval
above 0 and difference ≥ 0.03, **shape predicts cold jumps**; above 0 and
< 0.03, **detectable on cold cells, small**; contains 0, **no measurable
help**; below 0, **shape hurts**. Fewer than 400 cold jumps: **underpowered**.
Prediction: detectable, small (as Phase 15).

### H2 — took hold (≥ 5 outcome papers), on B

The same scores and table. Fewer than 100 that took hold: **underpowered**.
Prediction: detectable, small.

### Reported, not tested

- **Phase 15's 75 hits.** Phase 15's top 1,000 recomputed with its code and
  seed (check: 75 jumps, the same AUCs). Of the 75 hits: how many use a
  broken tool, how many target an off-field topic, how many survive into B
  and into C. How many of the 1,000 cells are broken-tool or off-field.
- Populations A and C: H1 and H2, 200 bootstrap draws each.
- Jumps in the top 100 and 1,000 of each model on B, A and C, against chance.
- B's top 20 cells under BASE+SHAPE and all hits in its top 1,000, with tool
  titles and topic names.

## Out of scope

Any other rule for broken records or topics, any other population, window or
feature. Anything the results suggest is reported as exploratory in its own
section.

## Run and budget

One AWS m6i.4xlarge (the Phase 12 launcher, `USERDATA=phase16`),
self-terminating, idle-log watchdog, 2-hour power-off; smoke pass first.
About 20 minutes, under $1. Teardown verified.

---

## Results

*Appended after the run. Nothing above this line changed.* Run
`noema-p12-20260930-095137` (the Phase 12 launcher with `USERDATA=phase16`),
one m6i.4xlarge, 8 minutes, about $0.10, torn down and verified. Numbers from
`results/phase16.json`; names from `data/`.

### Phase 15's 75 hits

The recomputation matched Phase 15 exactly (AUCs 0.9690 → 0.9756, 75 jumps in
the top 1,000).

| of Phase 15's top 1,000 cold cells | cells | jumps |
|---|---:|---:|
| broken tool | 867 | 29 |
| good tool, off-field topic | 96 | 44 |
| good tool, near-math topic (B) | 37 | **2** |

Phase 15's top list was almost entirely noise: 87% of it came from broken
records (mostly the one catch-all), and 73 of its 75 hits were broken or
off-field.

### Verdict (population B: good tools, near-math topics; model refitted)

2,053,698 cold cells, 969 cold jumps, 106 that took hold.

| test | AUC BASE → BASE+SHAPE | difference [95%] | verdict |
|---|---|---|---|
| **H1** cold jump | 0.958 → 0.972 | +0.014 [+0.011, +0.017] | **detectable on cold cells, small** |
| **H2** took hold | 0.964 → 0.982 | +0.018 [+0.010, +0.028] | **detectable on cold cells, small** |

Both as predicted. Shape's lift doubled compared with Phase 15 (+0.0065), but
it is still under the 0.03 bar.

### Reported, not tested

- **Top of the list**, jumps among each model's top N (chance = base rate × N):

  | population | cold jumps | top 100 BASE / +SHAPE | top 1,000 BASE / +SHAPE | chance (1,000) |
  |---|---:|---|---|---:|
  | B near-math | 969 | 2 / **22** | 21 / **126** | 0.47 |
  | A good tools, any topic | 1,929 | 2 / 41 | 27 / 203 | 0.27 |
  | C mathematics topics | 260 | 5 / 17 | 32 / 90 | 3.3 |

  Took hold, B: top 100, 0 / 8; top 1,000, 3 / 24.
- **A**: +0.006 [+0.004, +0.008], detectable, small; took hold +0.010
  [+0.007, +0.013]. **C**: +0.073 [+0.058, +0.092] and +0.057 [+0.025,
  +0.090], both **underpowered** (260 < 400 jumps, 36 < 100 took hold).
- **B's 126 hits** come from 88 tools and 52 topics. The target fields are
  Mathematics 31, Computer Science 28, Engineering 22, Physics 22, Decision
  Sciences 13, and Economics 10. The strongest:
  - *Handbook of Mathematical Functions* → fractional differential equations
    (16).
  - Loève's *Probability Theory* → probabilistic engineering design (13).
  - Témam's *Infinite-Dimensional Dynamical Systems* → tumour-growth models
    (11).
  - Kloeden and Platen's *Numerical Solution of SDEs* → numerical methods for
    differential equations (10).
  - Horn and Johnson's *Matrix Analysis* → financial risk and volatility
    (10).
  - Stein's *Singular Integrals* → tumour-growth models (9).
- **B's top 20**: 3 became cold jumps (10, 3 and 2 outcome papers); 17 did
  not.

### What this establishes

- Phase 15's headline list (75 hits in the top 1,000) was an artefact of
  label noise; only 2 of those hits were clean.
- With the noise removed and the model refitted, shape's lift is real and
  larger: its top 1,000 clean cold cells hold 126 jumps (1 in 8), against 21
  for BASE and 0.5 by chance. Its top 100 hold 22, against 2.

### What it does not establish

- **Noise left over.** The rules catch dead records and far-off fields only.
  Series titles ("Graduate Texts in Mathematics", 3 hits) still pass as tools,
  and some near-math topics are still mis-tags for math papers ("Research Data
  Management Practices" is the target of 13 hits).
- **Surprise.** Most clean hits are classic analysis and probability
  textbooks reaching applied topics (numerics, mathematical biology, finance,
  engineering design). They are real cold jumps between topics, but not
  unexpected ones to a mathematician.
- **Real work.** Not checked at this grain (Phase 14 was at arXiv areas).
