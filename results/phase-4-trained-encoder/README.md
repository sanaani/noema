# Phase 4 — is the encoder the bottleneck?

**Pre-registration.** Everything in this file was written and committed before
any encoder was trained. Results go in a section appended below; nothing above
that section changes.

## Why

Phase 3 settled that the angle between ReProver centroids ranks hard-subset
connections above chance — cross-area pairs sharing under 5% of their
vocabulary — at 3.9 σ, and that the effect is small: AUC 0.561 plain, 0.598
with kind-aware ranking. Every number the project has was measured with one
instrument, the pinned ReProver ByT5 retriever, a 2023 model trained for
premise retrieval, not for this question. So "the signal is small" and "the
instrument is weak" cannot yet be told apart.

Mendoza-Smith (arXiv 2606.28572, June 2026) trained small self-supervised
encoders on Mathlib proofs — no labels, a masked-token objective — and found
a sharp geometric signature (AUC 0.847) for a property of proofs, dependence
on the axiom of choice, that Lean itself certifies. That is evidence that an
encoder trained on Mathlib alone can see structure. Phase 4 asks whether one
sees *this* structure better than ReProver does.

## The corpus, the label, the pairs

Phase 3's, unchanged: 24,916 theorems, the committed 2026 dependency graph,
phase 1's eligibility rule, 23,583 eligible positives, of which 2,284 in the
hard subset. The same subset definitions, the same pair kinds, the same
centroid rule (mean of a theorem's state vectors, states in more than half of
all theorems dropped), the same size-corrected cluster null. Only the vectors
change.

## The encoders

All trained from scratch, self-supervised, on 2024 Mathlib data the corpus
already holds. Training never sees the 2026 graph, the eligibility rule, the
subsets, or any positive; the only thing it predicts is masked tokens of its
own input. Reusing the corpus's own 2024 texts for training is deliberate:
nothing in them encodes which pairs Mathlib later connected.

**A — ReProver (the baseline).** Phase 3's vectors, unchanged.

**B — a proof-state encoder trained on Mathlib (the primary arm).** Reads the
same 88,498 texts A read: every kept proof state of the 24,916 theorems and
the statement (initial goal) of the 10,211 observed ones. The recipe is the
paper's full-source encoder, applied to proof states instead of proof source:

| | |
|---|---|
| tokenizer | byte-level BPE, 16,384 tokens, trained on the 88,498 texts |
| model | Transformer encoder, 6 layers, d_model 256, 8 heads, d_ff 1,024, dropout 0.1, learned positions |
| input | first 512 tokens of each text; the fraction truncated is reported |
| objective | whole-word masked-token cross-entropy, 15% of words masked |
| training | 30 epochs, batch 64, AdamW lr 3e-4, weight decay 0.01, cosine schedule, seed 20260926 |
| held out | 10% of texts, for the loss curve only; the model kept is the last epoch |
| vector | mean-pooled final hidden state over non-pad tokens, 256-d, L2-normalised |

The vocabulary size is half the paper's 32,768 because the corpus is smaller.
No other setting is chosen, and nothing is tuned against any label.

**C — a tactic-sequence encoder, the paper's own recipe (secondary).** Each
observed theorem becomes its sequence of tactic heads: from its captured
tactic nodes, one per source position in source order, keeping nodes whose
text is a single line, is not `·` alone, does not begin with `by`, and is not
`<failed to pretty print>`; the head is the text's first identifier. Heads seen
fewer than five times become `[UNK]`. Model as the paper's main encoder: 4
encoder and 2 decoder layers, d_model 128, 4 heads, 20% of heads masked, 20
epochs, batch 128, lr 3e-4, maximum 64 heads, same seed; vector is the pooled
encoder state. Unlike the paper, it trains on all observed theorems, not a
constructive subset, because this question is not about choice. C only exists
for observed theorems, so it is scored only on observed–observed pairs.

Both train on one rented GPU, once each. If a run diverges (non-finite loss),
it is rerun once with the learning rate halved, and that is disclosed.

## Checks before any bridge score is read

1. **Training health.** For B and C: held-out masked-token loss falls over
   training and ends below the loss of predicting each masked token from its
   training-set frequency. An encoder that fails this is reported as untrained
   and its bridge scores are not interpreted.
2. **The paper's positive control, on C.** 3,676 of the corpus's observed
   theorems are in the paper's published population with a choice label
   (`manifest/proof_population.csv`): 1,125 constructive, 298 classical at
   dependency distance 2. k-NN anomaly score (mean cosine distance to the 10
   nearest constructive theorems, excluding itself); AUC of distance-2
   classical against constructive. The paper reports 0.847 with an encoder
   trained on constructive proofs only; C trains on both, so a lower figure is
   expected. **≥ 0.65: C reproduces the paper's direction.** Below that, C's
   bridge results are reported with the note that it did not. The same number
   is reported for A and B for comparison, not as a gate.

## Hypotheses and what each outcome means

### H1 (primary) — does B rank hard-subset connections better than A?

On the hard subset, all 2,284 positives, both encoders ranked by the
kind-aware percentile phase 3 made the default. Statistic: B's AUC minus A's,
positive by positive on the same pairs, with a 95% interval from a 2,000-draw
pigeonhole endpoint bootstrap (phase 3's H3 procedure).

| outcome | verdict |
|---|---|
| difference ≥ +0.05 and interval above 0 | **the encoder was the bottleneck**: a Mathlib-trained encoder is the better instrument, and the project continues with it |
| interval above 0, difference < +0.05 | **real but small gain**: better, not enough to change what the project can do |
| interval's upper end < +0.05 | **the encoder is not the bottleneck**: a gain of 0.05 is ruled out; the signal, not the instrument, is small |
| anything else | **inconclusive**, reported as such |

Rows are checked in order and the first that applies is the verdict.
Prediction: difference between
−0.03 and +0.05, i.e. the third row. The prediction is not the threshold.

### R1 — the same comparison on fresh pairs only

H1 restricted to pairs with at least one endpoint from phase 3's new draw
(1,883 positives). Not a gate. If H1 and R1 point opposite ways, that is
reported as a contradiction.

### H2 — is B above chance on its own?

B's hard-subset AUC, plain and kind-aware, against the cluster null, both
designs, smaller z quoted — the same test phase 3's H1 put A through. z ≥ 3
supported, 2–3 inconclusive, < 2 not supported. Needed so that a win in H1
cannot come from A getting worse on some pairs rather than B seeing anything.

### H3 — does proof style predict connections? (C)

On observed–observed hard-subset pairs, C's angle AUC against A's on the same
pairs, same bootstrap. Phase 3 had 309 positives here, so this is
low-powered by construction. Verdicts as H1's rows, stated with the positive
count. C sees only which tactics a proof used, never what it is about; a C
above A on cross-area pairs would say proof style carries the connection.

### Reported, not tested

- Every subset × kind × origin cell for B, as phase 3 reported for A.
- Top-k enrichment on the hard subset for B, k = 100, 1,000, 10,000.
- B's statement vectors against B's proof-state centroids on
  observed–observed pairs (phase 3's H3, repeated under B).
- The calibration table (hits per angle band, phase 2's pairs predicting
  fresh ones) for B.
- Truncation: the share of texts over 512 tokens under B's tokenizer.

## What is out of scope

- **Tuning.** No setting of B or C is chosen by looking at any positive,
  subset or AUC. There is one training run per arm.
- **A later label snapshot** and **a new capture.** Same data as phase 3.
- **Combining encoders** or combining the angle with other features. If B
  wins, that is the next phase.

## Budget

One GPU worker (g6e.xlarge or the next type with capacity), self-terminating,
tokenizer + two trainings + embedding, estimated under an hour: ~$2–5. Ceiling
$15. The IAM role, security group, instance and task object are torn down
after, and the teardown is verified.
