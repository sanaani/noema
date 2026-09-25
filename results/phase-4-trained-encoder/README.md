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

## Results

**H1: the encoder was the bottleneck.** On the hard subset, a proof-state
encoder trained on Mathlib alone ranks the 2,284 connections at kind-aware
AUC **0.692**, against ReProver's 0.598: **+0.095, 95% interval +0.044 to
+0.145**. Replicated on fresh pairs (+0.094). B is above chance on its own at
**8.3 σ**, against ReProver's 3.9. But the gain is in the body of the ranking,
not its top: among the closest 100,000 hard pairs ReProver finds 61 true
connections and B 19. Both are true, and the second decides what B is good for.

### What was run

- **Training:** one g6e.xlarge (L40S), 15 minutes of training
  (`results/training-report.json`), from the committed inputs
  (`results/inputs-manifest.json`, checked by digest on the worker). One run per
  encoder, no divergence, no rerun, last epoch kept. Cost about $0.70. The
  role, security group, instance and task object were torn down and the
  teardown verified; no noema instance, role or security group remains.
- **Scoring:** `scripts/analyze-phase3.py` on B's vectors (H2 and the reported
  cells); on A's centroids with C's vectors in the statement slot (H3);
  `scripts/analyze-phase4.py control` and `compare` (the positive control, H1,
  R1). Run with ReProver in both slots, `compare` returns phase 3's figures
  exactly (0.5612, 0.5977, 0.5638), and the second `analyze-phase3.py` run
  reproduces phase 3's H1 z of 3.90.
- **Deviations from the plan:** none.

### Checks before the result was read

| check | B | C | bar |
|---|---:|---:|---|
| held-out masked-token loss, last epoch | 0.311 | 2.667 | below unigram |
| unigram frequency predictor, same positions | 5.218 | 3.083 | |
| k-NN anomaly AUC, distance-2 classical vs constructive | 0.758 | **0.722** | C ≥ 0.65 |

Both encoders trained; C reproduces the paper's direction on the 1,423
labelled theorems it shares with the corpus. ReProver scores 0.804 on the same
control — higher than either trained encoder, a reminder that this control
does not separate proof structure from topic here, as the paper's own
controls did. 1.9% of texts exceeded B's 512-token window and were truncated.

### H1 — B against A on the hard subset

| | positives | A | B | B − A | 95% interval |
|---|---:|---:|---:|---:|---|
| **kind-aware (pre-registered)** | 2,284 | 0.598 | **0.692** | **+0.095** | +0.044 – +0.145 |
| plain angle | 2,284 | 0.561 | 0.654 | +0.093 | +0.045 – +0.141 |
| R1, fresh pairs, kind-aware | 1,883 | 0.598 | 0.693 | +0.094 | +0.042 – +0.144 |

Verdict by the table fixed in advance: difference ≥ +0.05 with the interval
above zero — **the encoder was the bottleneck.** The prediction (−0.03 to
+0.05, "not the bottleneck") was wrong.

B is better in every cell, not in one: full set 0.722 against 0.675,
cross-area 0.634 against 0.580, vocabulary < 5% 0.675 against 0.582, and on
the hard subset in every pair kind (OO 0.675 against 0.603, OS 0.675 against
0.596, SS 0.728 against 0.599) (`results/b-phase3.txt`,
`../phase-3-doubled-corpus/results/phase3.txt`).

### H2 — B above chance on its own

Hard-subset AUC 0.654 plain, 0.692 kind-aware. Cluster null, smaller z of the
two designs: **8.3 σ** plain (permutation; substitution 13.4), **10.6 σ**
kind-aware. Supported. Fresh pairs alone: 0.654, 8.2 σ.

### H3 — C, proof style only, against A

On the 309 observed–observed hard-subset positives: C 0.665, A 0.603,
C − A +0.062, interval −0.055 to +0.143. **Inconclusive.** On all
observed–observed pairs (2,595 positives) A is better, 0.715 against 0.629
(interval for A − C +0.014 to +0.168): the sequence of tactic names alone
knows less than the proof states about which theorems connect overall, and
whether it knows more on the hard pairs this sample cannot say.

### The top of the ranking (exploratory)

Run after the results above were read (`scripts/topk-phase4.py`,
`results/topk.txt`). Hard subset, true connections among the k closest pairs:

| k | chance | A plain | B plain | A kind-aware | B kind-aware |
|---:|---:|---:|---:|---:|---:|
| 10,000 | 0.4 | 8 | 2 | **16** | 4 |
| 100,000 | 4 | 26 | 8 | **61** | 19 |
| 1,000,000 | 40 | 79 | 80 | **238** | 163 |
| 5,000,000 | 198 | 293 | 367 | 542 | **601** |

AUC averages over the whole ranking; a tool reads the top. ReProver's closest
pairs are three times richer than B's; B overtakes it only past a million
pairs, and wins the AUC by ordering the long middle better. So B is the better
*instrument* — it measures the relation more faithfully across all pairs —
and ReProver is the better *finder*. They are plainly seeing different things,
which is the case for combining them.

### Reported, not tested

- **Statement against proof states, under B:** on observed–observed pairs B's
  statement vector beats B's proof-state centroid, 0.812 against 0.766 overall
  (interval for proof − statement −0.066 to −0.024) and 0.738 against 0.675 on
  the hard part (−0.134 to −0.001). Under ReProver phase 3 found no
  difference. With an encoder trained on Mathlib, the statement is the better
  object; the premise that the proof's trajectory adds something is now
  contradicted on these pairs, not just unsupported.
- **Calibration under B** (`results/calibration-b.txt`): B's angles are
  compressed (most pairs sit at 55–75°), so phase 2's degree bands do not
  transfer; the curve is monotone, and in the three nearest bands the fresh
  pairs' counts are 74–85% of the prediction, against about half under
  ReProver.

### What this establishes

- **The instrument was holding the project back.** A small encoder trained in
  15 minutes on the corpus's own 2024 texts, with no label, lifts the
  hard-subset AUC by 0.09, beyond its interval, on fresh pairs too.
- **The statement carries more than the proof states** under the encoder
  that sees the signal best.
- **Better AUC is not a better short list.** For finding bridges the top of
  the ranking matters, and there ReProver still leads.

### What it does not establish

- That B's architecture or settings are good ones: they were fixed, not
  searched. The gain is a floor for what a trained encoder can do.
- Anything about discovery. Every positive is a connection people made.

### Files added

| file | what it is |
|---|---|
| `results/compare.json` | H1 and R1 |
| `results/b-phase3.json`, `.txt` | H2, every cell, top-k and H3-under-B, for B |
| `results/ac-phase3.json`, `.txt` | H3 (C in the statement slot) and A re-run |
| `results/control.json` | the positive control |
| `results/training-report.json`, `SHA256SUMS`, `inputs-manifest.json`, `c-vocab.json` | the training run |
| `results/calibration-b.json`, `.txt`, `topk.json`, `.txt` | exploratory |

B's per-text vectors (2.6 GB with their texts), model weights and centroids are in
`outputs/phase-4-trained-encoder/`, not committed, and are rebuilt by
`scripts/run-train-aws.sh` then `scripts/analyze-phase4.py prepare`.
