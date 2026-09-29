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

## Results

*Appended after the run. Nothing above this line changed.* Numbers from
`results/phase8.json`, written by `scripts/analyze-phase8.py`, run once on a
laptop CPU from Phase 3–5 artifacts. No AWS.

**Counts.** 596 rare bridges, 3,244 ordinary bridges, 5,358 within-area
connectors, none dropped. Part B: 20,116 rare lemmas present in 2026, 1,060 of
them ends of a rare pair joined by 2026.

### Verdicts

| test | prediction | result | verdict |
|---|---|---|---|
| **A1** AUC(M), rare bridges vs within-area | real but weak, 0.55–0.62 | **0.561** [0.530, 0.593] | **real but weak** |
| **A2** AUC(M), rare vs ordinary bridges | no measurable difference | 0.492 [0.461, 0.522], p = 0.70 | **no measurable difference** |
| **A2** AUC(S), rare vs ordinary bridges | passes | 0.517 [0.483, 0.549], p = 0.15 | **no measurable difference** |
| **B1** AUC(M), future rare-jump lemmas | real but weak | 0.493 [0.466, 0.524], p = 0.67 | **no measurable difference** |
| **B2** AUC(S), future rare-jump lemmas | passes | 0.474 [0.445, 0.507], p = 0.94 | **no measurable difference** |

Only A1 went as predicted, and it repeats Phase 5: the map tells a spot where a
new theorem joins two areas from one where it stays in one area, a little
better than chance. It does not tell a rare jump from an ordinary crossing
(A2), and from 2024 alone it cannot say which rarely cited lemmas will become
the ends of a rare jump (B1, B2). Three of the four predictions for the new
questions failed.

### Reported, not tested

- **Sparsity on A1's labels: 0.617** [0.584, 0.648]. Rare bridges land in
  emptier parts of the map than within-area theorems. The rare-bridge share
  rises from about 5–9% in the densest six tenths of the map to 18% in the
  emptiest tenth. This is Phase 5's density finding again. A2 shows it is
  true of bridges in general, not of rare ones in particular.
- **Word mixing on A1: 0.572** [0.539, 0.605]; M − M_V −0.011 [−0.035,
  +0.012], no measurable difference.
- **Citation count wins again.** How many corpus lemmas a connector cites
  scores 0.815 on A1 and 0.692 on A2. Within count strata, A2's M and S sit
  at 0.43–0.52. In Part B, a rare lemma's own 2024 count (0 to 10) scores
  0.706: even among rarely cited lemmas, the less rare ones are likelier to
  become jump ends. Within count strata, B's M and S sit at 0.46–0.56; the
  highest is M among never-cited lemmas, 0.557 (201 positives).

### Exploratory: the rarity label is itself weak

The 15 rare bridges with the highest sparsity (`top_rare_bridges_by_S`)
include real cross-area work (Eisenstein series with the upper half plane,
Gromov–Hausdorff completeness, Lindemann–Weierstrass). But many of their rare
pairs pass through lemmas that are basic, not rare: `four_ne_zero`,
`Nat.cast_pos'`, `tsub_tsub`, `div_le_iff₀`. These have few *explicit*
citations in the 2024 graph because tactics (`simp`, `norm_num`, `positivity`)
use them without naming them. Counting citations in the dependency graph
does not measure rarity in the sense this project means. This was not tested
and suggests the next step.

### What this establishes

- The 2024 map's weak signal for cross-area spots (Phase 5) holds for rare
  bridges too (A1), and sits mostly in sparsity.
- Neither mixing nor sparsity separates rare jumps from ordinary crossings, or
  predicts from 2024 which rare lemmas will start one.
- Popularity, even within the rare band, again beats the map.

### What it does not establish

- That rare jumps are unpredictable. The rarity label counts explicit
  citations, which undercounts tactic-used lemmas and mixes basic facts into
  "rare". A label measuring rarity by what a lemma *says* (how specialised its
  statement is) may behave differently.
- Anything about a learned score. Only M and S were tested.

### Hands to the Navier–Stokes test

Part B did not pass, so as pre-registered, its map is not carried to the
Navier–Stokes proof.
