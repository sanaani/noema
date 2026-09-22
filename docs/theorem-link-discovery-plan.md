# Theorem-Link Discovery: Research Plan

> **Status, 2026-09-21.** This is a prediction record, not a live plan, and its
> body is left exactly as written. What happened since: stages 1 and 4 were
> taken, stages 2 and 3 were not. The ranker of stage 2 was built over theorem
> *statements*, beat the frozen encoder on held-out families but not the lexical
> baseline, and its training corpus was removed from the tree on 09-21 — see
> [`history.md`](history.md). The project went to stage 4's state-level
> trajectories instead, which is the proof-state geometry the results directories
> now measure. Stage 4's second half — proposing unknown links and letting Lean
> confirm them — remains the open question.

## Hypothesis

Mathematical relatedness between theorems is learnable from **denoised
theorem↔theorem edges**: two theorems are linked when they depend on the same
lemmas, regardless of vocabulary. An encoder trained to rank such links above
lexical lookalikes will place genuinely connected theorems (e.g.,
`Real.sin_add` ↔ `Complex.exp_add`) nearer than surface-similar but
unrelated ones (e.g., `Real.sin_add` ↔ `Real.cos_add`) — the exact ranking
current encoders invert.

## What we predict

1. A ranker trained on shared-citation edges will beat the Qwen structural
   baseline on target-vs-lexical rank while holding target-vs-background.
2. Gains will generalize to **held-out families** (train on 4, test on 2),
   proving the model learned relatedness, not pair memorization.
3. Proof routes, tactic traces, and duplicate proofs add nothing: ablating
   them out should not hurt, and may help.

## How we arrived here (the shift)

1. **Invariance (done).** Typed structural capture certifies α-renaming and
   definitional equality; encoders are consistent on certified equivalents.
   Consistency ≠ usefulness.
2. **Text null (done).** Five encoders on textual displays showed no
   cross-area geometry worth keeping.
3. **Structural signal + lexical dominance (done).** Qwen on complete Lean
   states: targets rank 1–9/64 vs background in 5 of 6 families — but rank
   last against lexical lookalikes in 4 of 6. The geometry tracks
   "talks about the same things" over "says the linked thing."
4. **Bridge expansion (done).** Mined 3 new cross-area triples from the
   Mathlib catalog, machine-checked 9 typed centers on a pinned host,
   extended the benchmark to 6 cases. New bridges replicate the pattern
   (FTC ranks 2–4/64; Euler criterion 9/64).
5. **Denoising decision (this plan).** Full proof paths are noise: 400 proofs
   of one theorem collapse to one node. What survives is the bipartite
   theorems↔lemmas graph. JEPA-on-trajectories and RL proposal were
   considered and deferred: trajectories are unrecaptured, and RL is
   overkill while supervised links abound.

## Closest related work

- Premise selection (Sledgehammer → FormulaNet → ReProver): ranks lemmas
  *useful for a proof step*; lexical match is signal there, noise here.
- MELD (Ye et al., Jun 2026): same equivalence-vs-lexicon question on
  natural-language statements with informal↔formal contrastive fix. Ours is
  formal-only, typed-state inputs, cross-area triples with lexical controls.

## Execution stages

1. **Dependency edges.** Host job over pinned Mathlib: per theorem, the set
   of lemmas its proof term references (dedupe to one edge per pair).
   Artifact: `results/phase-1-recognition/link-graph-v1/edges.json`.
2. **Ranker.** Contrastive/ranking loss on shared-citation pairs; negatives
   = lexical lookalikes + background. Train on 4 families, hold out 2.
3. **Referee.** The 6-case structural benchmark, target-vs-lexical rank as
   the deciding metric. Ship only on held-out gains.
4. **Later, if stage 3 plateaus:** state-level trajectories + JEPA masking;
   then RL proposal of unknown links rewarded by Lean confirmation.

## Non-goals

Truncating inputs to fit context (reject explicitly instead); mixing CPU
and GPU vectors without a drift gate; claiming discovery from n=6 without
held-out replication.
