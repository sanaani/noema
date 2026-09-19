# Link graph v1: theorem dependency edges

## Source

Pinned Mathlib (`f0957a75`, Lean 4.9.0), full-environment sweep with
`Deps.lean`: per non-internal `Mathlib.*` theorem, the set of constants its
proof term references. Giant proof terms (>3M nodes) are recorded as
`{"skipped":"oversize"}` instead of traversed.

## Files

- `Deps.lean` — the elaborator (core-only Lean, no Batteries).
- `edges.jsonl.gz` — 206,889 theorems → dependency name lists
  (1,056 oversize-skipped; raw `edges.jsonl` kept locally, over GitHub's
  file limit).
- `train-pairs.jsonl.gz` — 245,628 training pairs sharing ≥2 rare lemmas
  (lemma document frequency 2–200), proof-helper (`proof_*`) pairs removed,
  all 115 benchmark names excluded. Ranked by shared count, top 400k kept.

## Validation

All 6 benchmark families share citations across their (A, B, bridge)
triples (1–39 shared names, mostly typeclass/transport machinery).
Held-out referee: `results/bridge-expansion-v1/evaluation-v1`
(6-case structural benchmark).

## Training texts

- `training-texts.jsonl.gz` — 10,602 `{name, sexpr}` records from bulk
  `centers.jsonl.gz`, byte-gated at 100KB raw line (1,192 oversize gated,
  0 malformed). Covers 10,602 of 58,642 pair names; 50,955 of 245,628
  pairs have texts on both endpoints.
- Referee universe (18 case + 64 background + 12 hard-control + ranking
  names = 91 unique) has ZERO overlap with bulk texts → targeted capture
  in `RefereeCenters.lean` (all 91 verified as recorded theorems in
  `edges.jsonl.gz`). Train/referee split: 4 families train, Fourier +
  Euler-criterion held out.

## Bridge triples (near-miss intersections)

`scripts/scan-bridge-triples.py` → `bridge-triples.json.gz` (top 4,000 by score).

For every theorem C, take the proofs sharing ≥2 rare citations with it (df 2–200,
rarity-weighted, top 150 per C) and keep pairs (A, B) from that neighbourhood with:
**zero** shared rare citations between A and B, all three in different top-level
Mathlib areas, and no citation among any of the three. Score = min of the two
rarity-weighted overlaps. 205,833 theorems → 94,200 rare lemmas → 121,604 with ≥2
rare citations → 4,000 triples, 145s.

### Landmark filter

A shared citation counts only if it is itself a recorded theorem in `edges.jsonl`
(excluding definitions, classes, instances and typeclass projections, which never
appear as keys) whose own proof cites at least 20 constants — the median theorem
size, which drops `Prod.fst_zero`-style trivia. Tactic internals are excluded by
name. `--raw` disables the filter and reproduces `bridge-triples.json.gz`.

| | raw | theorem-only | + median size |
|---|---|---|---|
| rare landmarks | 94,200 | 48,603 | 27,373 |
| theorems with >=2 | 121,604 | 60,209 | 26,620 |
| runtime | 145s | 28s | 12s |

Filtering makes the scan faster, not slower. It also reshuffles the ranking
almost completely: only 716 of the raw top-4,000 pairs survive into the
theorem-only top-4,000, and 466 into the final one. The score is therefore not
a stable ordering — treat a triple as a candidate to verify, never as a result.
`bridge-triples-landmarks.json.gz` is the filtered run.

Unlike shared-citation pairs, a triple names its own bridge. Top hit of the raw run:
`RingHom.isSemisimpleRing_of_surjective` (RingTheory) and
`Module.isTorsionBySet_span_singleton_iff` (Algebra), bridged by
`Module.End.isSemisimple_of_squarefree_aeval_eq_zero` (LinearAlgebra), which routes
semisimplicity through K[X]-torsion. Many lower-ranked triples share only typeclass
projections or auto-generated auxiliaries; a plumbing filter is not yet applied.

`Bridge-sinKernel-polarization.lean` — Lean 4.9 check of the `sinKernel_def` /
`inner_map_polarization'` embedding candidate: polarization generalized to any
primitive n-th root of unity (n ≥ 3), `n = 4` recovering Mathlib's lemma, `n = 2`
landing on `Complex.re`. Verdict: the embedding pair is a proof-style false positive.
