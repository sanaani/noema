# Phase 8 — does the 2024 map know where *rare* bridges land?

**Pre-registration.** Everything in this file is written and committed before
any Phase 8 score is computed. Results go in a section appended below; nothing
above that section changes.

## Why

The project exists to find the connections that are rare, surprising and
valuable: two lemmas from distant areas that nobody used much, joined for the
first time. Phases 5 and 7 drifted from that. Phase 5 counted a new theorem as
a bridge whenever it joined two areas, even through an everyday lemma
(`Nat.cast_one`, `Finset.sum_congr`). Phase 7 asked which pairs 2026 Mathlib
would join, and popularity won because most new joins run through popular
lemmas. Neither says where the *rare* jumps happen.

Phase 8 reruns Phase 5 with the rare jumps as the target (Part A), then turns
the question into a map that needs nothing from 2026: for every rarely cited
2024 lemma, will it become one end of a rare jump by 2026? (Part B.) Part B's
map is the one a later test on an outside proof, such as OpenAI's
Navier–Stokes formalization, would use.

## What is already known

This phase reuses Phase 5's data, so some of it has been seen:

- Phase 5 found bridges land in *sparser* parts of the map than within-area
  theorems (AUC of density 0.394), and published its ten highest-mixing
  bridges.
- To set the rarity threshold below, the 2024 citation counts of the corpus
  were looked at (median 1; 96% at 10 or fewer; 0.13% above 200), and the
  number of rare bridges was counted at thresholds 5, 10 and 20 (462, 655, 951
  before the 2024 co-citation rule below). No score was computed on them.

## Definitions

Everything from Phase 3 and Phase 5 is unchanged: the corpus (24,916
theorems), the map (encoder B on each theorem's 2024 statement), eligible
pairs, "cross-area", the 10,368 connectors and their 2026 statement vectors.

- **Citations** of a corpus lemma: the number of 2024 theorems citing it
  (`link-graph-v1`, Mathlib `f0957a7`).
- **Rare lemma**: 10 citations or fewer.
- **Rare pair**: an eligible cross-area pair, both ends rare, not cited
  together by any 2024 theorem.
- **Rare bridge**: a Phase 5 bridge that joins at least one rare pair.
- **Ordinary bridge**: every other Phase 5 bridge.
- **Within-area**: Phase 5's within-area connectors, unchanged.

## The scores

As in Phase 5, k = 50 nearest corpus theorems by cosine, and no other k:

- **M, mixing**: 1 − (count of the most common area among the 50) / 50.
- **S, sparsity**: 1 − the mean cosine to the 50.
- **M_V, word mixing** (reported only): M with the 50 nearest by identifier
  Jaccard, as in Phase 5.

## Part A — where rare bridges land (Phase 5 rerun)

Scores are taken at each connector's 2026 statement, as in Phase 5.

### A1 (primary) — does mixing mark rare-bridge spots?

AUC of M, rare bridges against within-area connectors. Verdict rows as Phase
5's H1 (≥ 0.60 with interval above 0.5: **the map locates rare-bridge spots**;
interval above 0.5: **real but weak**; contains 0.5: **not supported**; below:
**contradicted**).

Prediction: real but weak, 0.55–0.62.

### A2 — does the map tell rare jumps from ordinary crossings?

AUC of M and AUC of S, rare bridges against ordinary bridges, Holm at 0.05
across the two (one-sided, the share of draws at or below 0.5).

| outcome, per score | verdict |
|---|---|
| passes Holm | **the map tells rare jumps from ordinary crossings** |
| interval contains 0.5 | **no measurable difference** |
| interval below 0.5 | **rare jumps sit on the other side** |

Prediction: S passes (rare jumps sit in emptier parts of the map); M shows no
measurable difference.

### Reported, not tested

- M_V on A1's labels, and M − M_V.
- How many corpus theorems a connector cites, as a score on A1 and A2, and A2
  within its strata (2, 3–5, 6 or more). A theorem citing more lemmas has more
  chances to include a rare pair.
- Rare-bridge share by decile of S.
- The 15 rare bridges with the highest S, with the rare pairs they join, in
  full, so a reader can judge whether they look like discoveries.

## Part B — a map of where rare jumps will start, from 2024 alone

- **Population**: rare corpus lemmas still present by name in the 2026 graph.
- **Positive**: an end of at least one rare pair that a 2026 connector joins.
- **Scores** at the lemma's own 2024 position, over the 50 nearest *other*
  corpus theorems: M and S.

### B1, B2 — do mixing and sparsity mark future rare-jump lemmas?

AUC of M (B1) and of S (B2), positives against the rest of the population,
Holm at 0.05 across the two. Verdict rows as A2, with "**the 2024 map marks
where rare jumps will start**". If there are fewer than 100 positives, both are
reported as underpowered and not tested.

Prediction: S passes, M is real but weak.

### Reported, not tested

- The lemma's own citation count (0 to 10) as a score, and B1 and B2 within
  citation strata (0, 1–2, 3–10), so a map that only tracks popularity shows
  itself.
- The 15 positives and the 15 negatives with the highest S.

## Statistics

95% intervals from 2,000 bootstrap draws. Part A resamples connectors by
their 2026 source file (as Phase 5). Part B resamples lemmas by their 2024
source file. Seed **20260928**.

## Out of scope

- Any new encoder, model or training. Everything is computed from Phase 3–5
  artifacts on a laptop CPU; no AWS.
- Any second rarity threshold, k or score. Anything the results suggest is
  reported as exploratory in its own section.
- The Navier–Stokes test. It is the next phase, and uses Part B's map only if
  Part B passes.

---
