# Reproduce the task-design continuation

The [protocol](strategy-transfer-protocol-v1.md) was frozen at `3972d94`; the
assignment freeze and implementation were committed at `8cdd31d` before scoring.
Both the power study and headroom screen launched from that clean revision.
These are local Git preregistrations, not an independently timestamped registry.
The encoder does not receive theorem IDs, program labels, subtree addresses,
proof order, transfer outcomes, or external metadata.

## Fast archive checks

Install the base [locked dependencies](../requirements.lock) and package, then:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python scripts/verify-strategy-headroom.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python scripts/verify-adversarial-result.py
```

This reconstructs all nine baselines, every per-triplet distance, both premise
strata, confidence bounds and the gate from archived vectors. It also regenerates
the entire eligible seven-leaf population, confirms all frozen program banks,
and explicitly replays transfer attempts in both directions. It does not need
model weights or Lean. The checks are same-code reproduction, not independent
statistical replication.

The second command reconstructs all 18 Horn interventions, both context-swap
alignments and every variance field, and audits the context/goal census and
recorded certificate responses. It reads the canonical corpus directly from its
archive; it does not extract arbitrary paths or rerun the Lean kernel.

Verify file integrity from each archive directory:

```bash
cd results/strategy-transfer-v1
sha256sum -c SHA256SUMS
```

Use `results/adversarial-v1/SHA256SUMS` similarly for the Horn diagnosis.

## Regenerate the development screen

Follow the [Lean/MiniLM bootstrap](reproduction.md), then install the additional
Lean-trained encoder dependency and fetch the hash-checked author export:

```bash
python -m pip install -r requirements-reprover.lock
python scripts/bootstrap-reprover.py
python -m noema.strategy_transfer design \
  --output outputs/my-strategy-development.json
python -m noema.strategy_transfer power \
  --output outputs/my-strategy-power
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python -m noema.strategy_transfer headroom \
  --plan outputs/my-strategy-development.json \
  --output outputs/my-strategy-headroom
```

The generated plan must have SHA-256 equal to `plan_sha256` in the committed
[assignment freeze](../results/strategy-transfer-v1/assignment-freeze.json).
Outputs must be new paths. The headroom command verifies its fixed 24-proof
fixture before encoding, records the actual Lean responses, and checks all 120
pre-rotation states against the symbolic renderer. It excludes initial and
terminal states when building the eight-point clouds. Full proof trajectories
and tactic strings are audit data, not representation input.

ReProver runs on CPU with singleton batches and two intra-op threads. The
870,637,892-byte model export is converted to int8_float32 in memory. The frozen
607 unique statement/state strings take substantially longer than MiniLM on
this four-thread machine. No GPU, training run, paid API, or mathlib corpus
acquisition is needed. The implementation rejects overlength inputs and hashes
model.bin, config.json and vocabulary.json on load. Large weights remain outside
Git; all vectors needed for reproduction are committed.

An ancillary reflexivity-state smoke check compares float32 and int8_float32
execution of the same author export: cosine similarity .99770, normalized L2
drift .06780. This is one unrelated input, not a task-wide quantization bound;
it changes neither the frozen arm nor its decision rules. Details are in the
[encoder smoke record](../results/strategy-transfer-v1/encoder-smoke.json).

The primary [LeanDojo/ReProver model table](https://github.com/lean-dojo/ReProver#retrieval)
identifies the encoder as a Lean 4 premise retriever. Its
[retrieval implementation](https://github.com/lean-dojo/ReProver/blob/main/retrieval/model.py)
uses a masked mean of hidden states and L2 normalization. The author's
[CTranslate2 export](https://huggingface.co/kaiyuy/ct2-leandojo-lean4-retriever-byt5-small/tree/8612469b496b72bdb2f0d6ccd5316c100200581e)
and the [ByT5 tokenizer implementation](https://github.com/huggingface/transformers/blob/main/src/transformers/models/byt5/tokenization_byt5.py)
support the frozen runtime/tokenization choices. This is a quantized Lean-trained
arm, not a claim that it is identical numerically to the original float model or
that premise-retrieval training guarantees strategy-transfer performance.

## Reproduce the Horn intervention

Extract the archived canonical corpus into `outputs/canonical-corpus-v3/` if it
is absent, using the [canonical reproduction guide](reproduction-v3.md). With
the Lean and MiniLM tools installed:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python -m noema.adversarial --output outputs/my-adversarial-diagnosis
```

The command reads the committed canonical sampling freeze and original vector
caches. It produces all intervention matrices, 12 constructive Lean equivalence
certificates and extended vector caches. The original centroid results must
match the archived canonical result. New intervention vectors retain the same
encoder and preprocessing choices as that study.

## Decision boundaries

This continuation has no Phase 5 or automatic mathlib-acquisition command. The
headroom CLI scores only cheap controls; it does not compute energy distances.
The preregistered conditional sampling check and confirmation are authorized
only if their upstream gates pass. A closed gate is recorded with its empirical
reason. Changing a failed task, budget or decision rule requires a fresh,
explicitly labeled design, not overwriting this study's assignments or outcome.
