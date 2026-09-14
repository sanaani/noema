# Reproduce the revised-plan continuation

Install the base and encoder dependencies and pinned Lean/MiniLM tools using
the [original reproduction guide](reproduction.md). All commands run from the
repository root with the local virtual environment active. Limit BLAS threads:

```bash
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
```

No paid API, model training service, or remote compute is required. Bulk working
outputs remain ignored; compact evidence is committed in `results/`.

## Power grid and independently frozen replication

```bash
python -m noema.cluster_power --config configs/cluster-power-v1.json \
  --output outputs/reproduced-cluster-power
python -m noema.cluster_power \
  --config configs/cluster-replication-v1/config.json \
  --selected configs/cluster-replication-v1/selected.json \
  --output outputs/reproduced-cluster-replication
```

`--resume` continues an interrupted power run after checking its configuration
and implementation hashes. Completed outputs cannot be overwritten. Every
stratum has an atomic checkpoint. Seeds depend on the full stratum and trial
identity, not the execution order. Configuration and source versions must match
the original run when resuming.

The selection script reconstructs the independently frozen replication rows:

```bash
python scripts/select-cluster-replication.py \
  outputs/reproduced-cluster-power/report.json outputs/reproduced-selection
```

Compare its selected strata and configuration with the committed files.
Provenance timestamps and launch revisions make whole-report hashes differ
across reruns even when every seeded numerical trial is identical.

For standard plotting and compact archives:

```bash
python -m pip install -r requirements-plots.lock
python scripts/archive-cluster-power.py outputs/reproduced-cluster-power \
  outputs/reproduced-power-archive --plots
```

The raw JSON retains every trial; CSV retains every metric/stratum power rate
and Wilson interval. PNG plots supplement these machine-readable records.

## Nongeometric pilots and acquisition selection

The old corpus is available in `results/corpus-v1/corpus.tar.gz`. Extract it
into a new directory as described in the original guide, then run:

```bash
python -m noema.corpus_pilot --config configs/corpus-pilot-v2.json \
  --manifest outputs/old-corpus/manifest.json --output outputs/native-pilot
python -m noema.corpus_pilot --config configs/corpus-pilot-canonical-v3.json \
  --manifest outputs/old-corpus/manifest.json --output outputs/canonical-pilot
python -m noema.matched_corpus prepare --pilot outputs/canonical-pilot \
  --calibration outputs/reproduced-cluster-power/report.json \
  --replication outputs/reproduced-cluster-replication/report.json \
  --output outputs/reproduced-acquisition.json
```

Pilots use a new output directory and checkpoint each completed theorem; they
are deterministic bounded searches, not accepted-proof corpora. They do not
currently expose a resume option. Their compact reports, state metadata and
exhaustive support calculations are already archived. Candidate banks can be
regenerated from the configurations. The native pilot's reported common
capacity is zero; canonical replay supplies the selected structural budget.

A full rerun's provenance hashes will differ, so compare selected theorem IDs,
proof identities, length quotas and splits rather than pretending timestamps
are numerical reproducibility failures. To reproduce the **exact archived
acquisition**, use its committed plan:

```bash
gzip -dc results/canonical-v3/acquisition-plan.json.gz > outputs/exact-acquisition.json
python -m noema.matched_corpus collect --plan outputs/exact-acquisition.json \
  --output outputs/reproduced-canonical-corpus
```

Collection verifies the frozen 1,864-script union in isolated batches of eight.
It checks Lean 4.33.1, the pinned REPL revision, absence of axioms/admitted proofs,
actual tactic length and normalized-state-sequence uniqueness. `--resume`
continues completed batches after checking the acquisition plan, toolchain and
saved source hashes. Verification errors are preserved; missing required proofs
prevent the analysis freeze. L, i and u metadata are external to encoder inputs.

## Freeze the verified corpus before analysis

```bash
python -m noema.matched_experiment freeze --plan outputs/exact-acquisition.json \
  --corpus outputs/reproduced-canonical-corpus --output outputs/reproduced-freeze.json
python -m noema.matched_experiment run --corpus outputs/reproduced-canonical-corpus \
  --freeze outputs/reproduced-freeze.json --output outputs/reproduced-matched-analysis
```

The freeze regenerates proof sources, checks verifier evidence and full state
extraction, rejects duplicate identities/sequences, checks disjoint comparisons,
and verifies identical length/raw-depth histograms across all primary groups.
It also fixes alternative proof splits and stricter diversity eligibility before
embedding. Commit the freeze before using a fresh population for research.

Analysis uses the frozen energy estimator, pinned encoders, 9,999 theorem-label
permutations and 2,000 paired theorem-bootstrap draws. One primary BH family
contains the nine full-content matched comparisons. Unmatched, goal-only and
alternative-split results are secondary diagnostics. No proof navigation or
geometric pair mining is hidden in this command.

Analysis `--resume` checks the corpus, split freeze, model, dependency versions
and implementation hashes. Vector caches and comparison checkpoints are atomic.
The latest completed comparison is retained; an interrupted comparison may be
recomputed. A final report marks completion and cannot be overwritten.

## Verify archived results

The canonical archive contains the proof sources and complete Lean evidence,
the exact acquisition and state freeze, all distances/baselines/uncertainty,
three vector caches, and checksum manifests. Extract it into a new directory:

```bash
mkdir outputs/archived-canonical-check
tar -xzf results/canonical-v3/corpus.tar.gz -C outputs/archived-canonical-check
python scripts/verify-matched-result.py --corpus outputs/archived-canonical-check \
  --result results/canonical-v3 --output outputs/reproduced-validation.json
```

The verifier re-audits the frozen corpus and recomputes all comparisons, primary
p/q values, baselines, intervals and advancement decisions using saved vectors.
It requires exact agreement and errors if any needed vector is missing. This
is same-implementation numerical reproduction in a fresh process, not an
independent statistical replication or an independent implementation audit.

Checksum verification is read-only:

```bash
(cd results/cluster-power-v1 && sha256sum -c SHA256SUMS)
(cd results/cluster-replication-v1 && sha256sum -c SHA256SUMS)
(cd results/canonical-v3 && sha256sum -c SHA256SUMS)
```
