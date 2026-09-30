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
