# Reproducing the bounded study

Use a fresh checkout and new output directories. The compact committed artifacts
are evidence from the reference execution; reruns record their own timestamp,
platform, source revision and dependency versions. They must not overwrite it.

## Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install -r requirements-encoders.lock
python -m pip install --no-deps -e .
bash scripts/bootstrap-lean.sh
bash scripts/bootstrap-encoder.sh
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
```

The Lean bootstrap pins the compiler archive checksum and REPL commit. This
fragment uses the compiler's standard library, with no Mathlib dependency.
The encoder bootstrap pins the model revision and both artifact checksums.
Formal analysis checks model hashes at load time. External training-data
contamination cannot be exhaustively ruled out for this general-text model.
Expect roughly 4 GiB of tool downloads/unpacked files and about 1.6 GiB peak
verifier memory. Verifier processes are sequential, with eight isolated proofs
per import-only environment. Collection and CPU embedding can each take minutes
to tens of minutes depending on the machine.

## Recreate proofs and freeze sampling

```bash
noema corpus --output outputs/my-corpus --theorems 24 --proofs 64
noema audit --corpus outputs/my-corpus/manifest.json --output outputs/my-audit
```

Inspect/commit `outputs/my-audit/audit.json` and the exact split freeze before
computing embeddings for a new study. The reference study's freeze is archived
in `results/corpus-v1/splits.json.gz` and predates the reference embedding run.
The seed, theorem/proof selection, state sampling and protocols are fixed in
source and versioned design documents; no geometric selection is performed by
the audit command. Source and verifier evidence are checked against deterministic
proof generation. Auditing saved evidence does not rerun Lean; collection does.

To continue collection after interruption, run the same command with `--resume`.
Only a saved complete-theorem checkpoint is reused. Configuration and source-file
checksums must match; completed outputs are never overwritten.

## Reuse the archived corpus

```bash
(cd results/corpus-v1 && sha256sum -c SHA256SUMS)
mkdir -p outputs/archived-corpus
# This archive contains only the manifest and generated .lean proof sources.
tar -xzf results/corpus-v1/corpus.tar.gz -C outputs/archived-corpus
gzip -dc results/corpus-v1/splits.json.gz > outputs/reference-splits.json
noema audit --corpus outputs/archived-corpus/manifest.json --output outputs/rechecked-audit
cmp outputs/reference-splits.json outputs/rechecked-audit/splits.json
```

Regenerated corpora have different provenance timestamps, so their overall corpus
hash differs even when mathematical records agree. Use the corresponding newly
created freeze; do not pair a new corpus with the reference freeze.

## Run the formal comparisons

```bash
noema formal --corpus outputs/archived-corpus/manifest.json \
  --freeze outputs/reference-splits.json --output outputs/my-formal
```

For a newly generated corpus, substitute its manifest and audit freeze paths.
The run records full primary distance matrices, baseline rankings, uncertainty,
representation-collapse checks, proof/state sampling sensitivities, stricter
diversity eligibility, graph fidelity, and the unchanged feasibility decision.
A single BH family covers reported primary encoder/view/direction tests; secondary
sensitivity reruns are descriptive. Inference permutes complete theorem labels,
not individual correlated proof states.

The output also saves encoder vector caches and atomic progress checkpoints.
Use the same command plus `--resume` after interruption. Corpus, split freeze,
model, dependency and analysis-source fingerprints must agree. `report.json`
and `report.md` signify a completed run; `checkpoint.json` alone does not.
An interruption within a comparison repeats that comparison from its saved
cache; no partial result is treated as complete.

## Synthetic evidence and validation

```bash
noema synthetic --config configs/smoke.json --output outputs/my-smoke
noema stress --config configs/stress-v1.json --output outputs/my-stress
ruff check .
ruff format --check .
python -m pytest
```

The qualified, restricted synthetic run can be recreated with
`configs/qualification-v2.json`; it includes 9,000 comparisons. The failed v1
qualification and the noisy pilot are retained alongside it. The stress run is
exploratory and does not expand the frozen qualification scope.

CI runs the base numerical/unit tests, formatting, lint and a synthetic smoke run.
Lean and actual pretrained-encoder integration checks require the bootstrapped
local tools; their absence is reported as a skip, not a verification success.
The full local validation includes those tools.

Archive a completed corpus and its freeze with:

```bash
bash scripts/archive-study.sh outputs/my-corpus outputs/my-audit results/my-corpus
```

All archive contents have deterministic compression metadata and SHA-256 checksums.
