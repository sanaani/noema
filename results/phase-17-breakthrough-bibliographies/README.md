# Phase 17 — what do breakthrough bibliographies look like? (descriptive, 5 papers)

**Not pre-registered.** A first look, asked for directly: the reference lists
of the five landmark papers, tagged with expert-assigned area codes, against
ordinary papers of the same area and year. Five papers support no test; the
numbers below are descriptions.

## Why

Phases 11–16 modelled all of arXiv, and ordinary papers set the target. The
project's aim is the rare breakthrough, so the next phases learn from a
curated set of breakthroughs before a hard cutoff (end of 2015) and test on
ones after. This phase starts with the five landmarks' citation patterns.

## Method

- **Area codes**: MSC 2020 (Mathematics Subject Classification), assigned by
  zbMATH Open's reviewers. A work's area is its first code; its 2-digit prefix
  is the broad area (11 number theory, 52 convex and discrete geometry, 68
  computer science, …).
- **Landmark references**: OpenAlex (union of arXiv-DOI and journal-DOI
  records); Huang's from his arXiv LaTeX bibliography, since OpenAlex has none.
  Each is matched in zbMATH by DOI, else by title. 59 of 78 references got a
  code (`scripts/landmark-bibliographies.py`, `data/landmarks.json`).
- **Baseline**: up to 300 zbMATH papers with the same primary 2-digit area and
  publication year, each with at least 5 coded references; zbMATH codes their
  reference lists itself (`scripts/bibliography-spread.py`, `data/spread.json`).
- **Scores per paper**, over coded references:
  - far share: references outside the paper's own 2-digit areas;
  - diversity: mean pairwise distance, where 0 = same 3-character code,
    0.5 = same 2-digit area, 1 = different area (Rao–Stirling, equal weights);
  - areas: the number of distinct 2-digit areas.

## Results

| paper | own area | references coded | far share (pct) | diversity (pct) | areas (pct) |
|---|---|---:|---|---|---|
| Viazovska, dim 8 | 52 | 18 | 0.11 (9th) | 0.78 (59th) | 5 (40th) |
| CKMRV, dim 24 | 52 | 16 | 0.44 (59th) | 0.65 (30th) | 3 (10th) |
| Croot–Lev–Pach | 11 | 7 | 0.00 (0th) | 0.00 (0th) | 1 (0th) |
| Ellenberg–Gijswijt | 11 | 5 | 0.20 (62nd) | 0.80 (85th) | 3 (42nd) |
| Huang | 05 | 13 | 0.85 (100th) | 0.41 (45th) | 3 (48th) |

Percentile = share of the 88–101 baseline papers below the landmark.

What the references are:
- **Viazovska**: 7 modular-form works (11) and 7 sphere-packing works (52).
  Her own codes include 11H31, so the modular forms count as "own area". The
  bridge is two areas, cited in equal measure.
- **Croot–Lev–Pach**: all 7 coded references are additive number theory.
  The polynomial method that made the result is not cited at all.
- **Ellenberg–Gijswijt**: 5 references, one from probability (a
  large-deviations text).
- **Huang**: 10 of 13 are computer science (68). The problem came from
  complexity theory. The tool that solved it, eigenvalue interlacing, appears
  once, as a short-proof note that zbMATH did not match.

## What this suggests

- **Breakthrough bibliographies are not unusually spread.** On diversity and
  number of areas the five sit between the 0th and 85th percentile of ordinary
  papers. A score over the whole reference list would not have picked them out.
- **The decisive tool is a single citation, or none.** The idea that made
  each result is carried by one reference or by no reference: Croot–Lev–Pach
  cite nothing for the polynomial method, and Huang cites eigenvalue
  interlacing once. The reference list mostly describes the *problem's* area.
- **Huang is the exception on far share** (100th percentile), because the
  problem's home is computer science and the paper is filed under
  combinatorics.

## What it does not establish

- Anything general: five papers, three from one year and one topic cluster.
- The scores use each reference's first code only, and 19 of 78 references
  could not be matched.

## Next

A much larger curated set, fixed before looking at outcomes: breakthroughs to
the end of 2015 to learn from, and 2016 onwards to test on. Also candidates
for delayed recognition (papers whose citations took off years later).
