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
