# Reproduce the confirmation without a minimum gain margin

Use the pinned Python, Lean, REPL, MiniLM and ReProver dependencies in the
[v1 guide](reproduction-strategy-transfer-v1.md). The experimental definitions
remain those frozen for v2; the new module supplies the amended inference and
full-corpus proof audit. The [protocol](strategy-transfer-confirmation-protocol-v1.md)
was frozen before confirmation assignments and measurements.

## Sequential path

From the repository root, with the environment activated:

```bash
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
python -m noema.transfer_v2 design --split confirmation --count 512 \
  --output outputs/my-confirmation-plan.json
python -m noema.transfer_confirmation power --output outputs/my-confirmation-power.json
python -m noema.transfer_confirmation run \
  --plan outputs/my-confirmation-plan.json --output outputs/my-confirmation
```

Resume the last command with `--resume`. Completed triplets and 20-input encoder
batches are reused. Resume rejects changed plan, protocol or analysis source.
Each saved triplet has a proof-audit hash and a block-assignment hash; every
actual Lean context and intermediate goal is checked before its checkpoint is
marked complete. The run verifies 6,144 proofs and 30,720 states before encoding.

## Parallel acquisition path

The sequential runner must be stopped before starting these workers. Retain its
initialized output directory and run freeze. Use the same plan and output path
throughout. In two separate processes, execute the proof command with shard 0
and shard 1 respectively:

```bash
python scripts/confirmation-acquisition-worker.py proofs \
  --plan outputs/my-confirmation-plan.json --run outputs/my-confirmation --shard 0
python scripts/confirmation-acquisition-worker.py proofs \
  --plan outputs/my-confirmation-plan.json --run outputs/my-confirmation --shard 1
```

The two workers own disjoint even/odd triplets. Repeat a command after an
interruption; completed proof checkpoints are retained. Once both finish:

The remaining stages can be automated while those workers run:

```bash
python scripts/finish-confirmation-acquisition.py \
  --plan outputs/my-confirmation-plan.json --run outputs/my-confirmation
```

This waits for both proof-completion records, validates the full proof summary,
runs the two encoder workers, merges complete caches and resumes the frozen
analysis. Its separate encoder logs are written beside the run directory.
The equivalent manual steps follow, beginning after both proof workers finish:

```bash
python scripts/confirmation-acquisition-worker.py proof-summary \
  --plan outputs/my-confirmation-plan.json --run outputs/my-confirmation
```

Then run the following two commands in separate processes, with one shard each:

```bash
python scripts/confirmation-acquisition-worker.py encode \
  --plan outputs/my-confirmation-plan.json --run outputs/my-confirmation --shard 0
python scripts/confirmation-acquisition-worker.py encode \
  --plan outputs/my-confirmation-plan.json --run outputs/my-confirmation --shard 1
```

Each worker sorts the same frozen input set, takes alternating entries and
uses the original encoder factory. It changes scheduling only. Once both finish:

```bash
python scripts/confirmation-acquisition-worker.py merge \
  --plan outputs/my-confirmation-plan.json --run outputs/my-confirmation
python -m noema.transfer_confirmation run --resume \
  --plan outputs/my-confirmation-plan.json --output outputs/my-confirmation
```

Merge requires complete, disjoint input coverage and matching encoder manifests.
Any vector already present in the sequential cache must match bit for bit.
The final frozen runner validates all checkpoints, reconstructs the baselines
before energy scores, and computes the exact paired tests and 10,000 paired
triplet-bootstrap intervals. No sample-size adjustment follows observed scores.

## Archive-only verification

```bash
python scripts/verify-transfer-confirmation.py
```

This re-enumerates every selected complete shortest-proof bank, explicitly
replays transfer labels and reproduces all 72 exact-power calculations. After
the measurement archive is present it checks all recorded proof sources,
axiom audits, actual contexts/states, cached vectors, component tests and
bootstrap intervals without model downloads or a Lean installation.

Add `--regenerate-assignments` to repeat the full deterministic population search;
this takes several minutes and more memory. The faster selected-bank audit is
already independent of the assignment generator's bank records. Across platforms,
tiny float differences use the same reported 1e-12 archive tolerance, with exact
discrete outcomes and decisions. This does not change the experimental tie rule.
