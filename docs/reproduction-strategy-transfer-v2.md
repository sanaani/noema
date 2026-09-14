# Reproduce the structurally matched continuation

The [v2 protocol](strategy-transfer-protocol-v2.md) was committed at `2a58c84`.
Fresh eight-leaf assignments and analysis source were frozen at `9c3d21e`;
`ccfbe1e` only formatted the premeasurement feasibility script. Power and headroom
record that clean revision. These local Git freezes precede candidate embeddings
and scores. No v1 cloud distances were opened or old assignments reused.

Use Python 3.12 and the base, MiniLM and ReProver dependency locks and pinned
tools from the [v1 reproduction guide](reproduction-strategy-transfer-v1.md).
All commands below run at the repository root.

## Frozen inputs, power and headroom

```bash
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
python scripts/transfer-v2-feasibility.py --output outputs/my-v2-feasibility.json
python -m noema.transfer_v2 design --output outputs/my-v2-development.json
python -m noema.transfer_v2 power --output outputs/my-v2-power
python -m noema.transfer_v2 headroom \
  --plan outputs/my-v2-development.json --output outputs/my-v2-headroom
```

The development plan's byte hash must match the
[assignment freeze](../results/strategy-transfer-v2/assignment-freeze.json).
Generation uses source/target clade masks and exact program sets; embeddings
never enter eligibility. No shortest program or theorem endpoint pair is reused
across the 64 triplets. The feasibility run uses a different seed and has no
encoder or task-performance stage.

Power simulates 90,000 experiments, each with nine paired tests, across three
sample sizes and three conditions. Raw arrays retain all 810,000 paired gains
and p-values. The smallest qualified conditional-confirmation budget is 512
triplets under the registered .80-versus-.65 planning alternative. This model
does not estimate the actual eventual cloud effect.

## Resume after interruption

```bash
python -m noema.transfer_v2 headroom \
  --plan outputs/my-v2-development.json --output outputs/my-v2-headroom --resume
```

Each completed 20-state batch is saved by atomic replacement of a compressed
vector cache. At most one batch needs repeating after a process interruption.
The resume path checks the plan, protocol, analysis source hashes and encoder
manifest. The complete fixture audit is reused only after its successful summary
was written. Encoders skip existing texts; cached vectors are not recomputed.
Tests deliberately interrupt a batch and verify that only missing states are
encoded on resume.

## Conditional cloud check

Only if BOTH headroom and power qualify:

```bash
python -m noema.transfer_v2 geometry \
  --plan outputs/my-v2-development.json --headroom outputs/my-v2-headroom \
  --power outputs/my-v2-power/report.json --output outputs/my-v2-geometry
```

Use `--resume` after an interruption. The command refuses failed upstream gates
or changed plans/source. It copies initial vectors into a separate cache, adds
only states required by the 100 fixed resampling draws, and leaves the headroom
cache intact. Every draw compares energy with centroids recomputed from the
same proof sample. This is a conditional development feasibility test, not an
independent replication. Confirmation is allowed only by the protocol's further
stability gate; no automatic Phase 5 or mathlib acquisition occurs.

The recorded run completed all 100 draws and failed this gate (0 qualified,
80 required), so nine-leaf confirmation was not opened. Geometry used the same
six frozen source files and completed at clean revision `f1cf916`; `a73aef2`
archived the passing headroom and power before geometry began. Changes between
those revisions strengthen archive validation only.

## Archive-only verification

```bash
python scripts/verify-transfer-v2.py
```

This needs base dependencies but no model weights or Lean installation. It
regenerates assignments, checks exact clade and strategy exclusions, explicitly
replays transfer labels, validates the recorded Lean proof sources and states,
and recomputes all headroom scores. If a conditional geometry archive exists,
it reconstructs all 100 proof samples, cloud scores, matched centroid controls
and the stability gate. The power arrays independently reconstruct their
reported joint outcomes and selected budget.

The same-machine archives may reproduce bit for bit. Across BLAS CPU kernels,
float reductions can differ in their last bits. A recorded v1 check with the
NEHALEM kernel changes 106 distances by at most 1.11e-16 and changes no outcomes.
The verifier reports such differences and allows only 1e-12 absolute/relative
numeric tolerance, with exact discrete outcomes and gate decisions. This is
an archive-verification tolerance; it changes no experimental decision rule.

Check the archive's SHA256SUMS from its own directory. Raw encoder manifests,
source freezes and original checkpoints are retained alongside the report.
