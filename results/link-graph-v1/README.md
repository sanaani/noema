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
