# Phase 14 — did the predicted jumps do real work, or were they passing mentions?

**Pre-registration.** Everything in this file is written and committed before
any paper text is downloaded or judged. Results go in a section appended
below; nothing above that section changes.

## Why

Phase 13's model ranked (tool, area) cells with no visible route between them,
and about 1 in 5 of its top 1,000 became **cold jumps**: two or more papers in
the area cited the tool within 15 years. But a citation can be a passing
mention ("see [T] for background"). If most hits are like that, the 1-in-5 is
not a useful lead rate. Phase 14 reads the citing sentences and asks whether
the tool **did work** in the new area's papers.

## Cells

From Phase 13's window (history ≤ 2006, outcome 2007–2021), recomputed with
Phase 13's code and seed so the scores are identical (checked: 213 cold jumps
in the top 1,000). Three groups, 60 cells each, drawn at random with seed
**20261005**:

| group | cells drawn from |
|---|---|
| **G1 model hits** | cold jumps in BASE+SHAPE's top 1,000 cold cells |
| **G2 other cold jumps** | cold jumps outside that top 1,000 |
| **G3 ordinary spread** | rung-1 (shared paper) cells that became jumps |

For each cell, up to 3 of the outcome papers in the area that cite the tool,
drawn at random with the same seed.

## Evidence

For each citing paper: its arXiv source (`export.arxiv.org/e-print/<id>`,
one request every 3 seconds). The tool's title and first author's surname
come from OpenAlex. A bibliography entry (`\bibitem` or `.bib`/`.bbl` entry)
**matches** the tool if it contains the first author's surname and at least
80% of the title's content words (at least 2). For a matched entry, every
`\cite`-family command naming its key gives a **context**: about 600
characters before and 400 after, with the enclosing section heading. Up to 5
contexts per paper. A paper with no source, no match or no citation command
is reported and not judged.

## Judging

Every judgeable paper is labelled by **two independent judges** (Claude
subagents, same rubric, run separately). They see the tool's title, the
citing paper's title and area, and the contexts. They do not see the group,
the model's scores or the other judge's labels. Items are shuffled.

| label | meaning |
|---|---|
| **used** | a result, method or construction from the tool is applied in the paper's own argument: a proof, computation, construction or estimate relies on it |
| **passing** | cited only as background, survey, related work, notation or a pointer, not applied |
| **unclear** | the contexts do not show which |

A paper counts as **used** only if both judges say used. A cell **did real
work** if at least one of its judged papers counts as used. A cell with no
judged paper is excluded and reported.

## Tests

### H1 (primary) — did the model's hits do real work?

Share of judged G1 cells that did real work.

| share | verdict |
|---|---|
| ≥ 50% | **the hits mostly did real work** |
| 25–50% | **mixed: a real minority** |
| < 25% | **mostly passing mentions** |

Fewer than 30 judged G1 cells: **underpowered**, no verdict. Prediction:
mixed.

### H2 — are the model's hits more substantive than other cold jumps?

Share (G1) − share (G2), with a 95% interval from 2,000 bootstrap draws
resampling cells within each group. Reported as: G1 higher (interval above 0),
no measurable difference (contains 0), G1 lower (below 0). Prediction: no
measurable difference.

### Reported, not tested

- The same share for G3 (ordinary spread), and G1 − G3.
- Per-paper label counts per group, and the judges' agreement (share and
  Cohen's kappa).
- Coverage: cells and papers drawn, with source, with a matched entry, judged.
- Five G1 cells that did real work, with a quoted context, for reading.

## Out of scope

- Any other group, sample size, matching rule or label. Anything the results
  suggest is reported as exploratory in its own section.

## Run and budget

One AWS m6i.4xlarge recomputes the cells and fetches the sources (about 540
papers at 3 seconds each, about 30 minutes), with the idle-log watchdog and
a 2-hour power-off; smoke pass first. Under $1. Judging runs locally. The
role, instance profile, security group, instance and task object are torn
down and the teardown verified.

---
