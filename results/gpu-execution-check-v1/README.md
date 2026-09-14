# Complete GPU execution check

The 512-triplet strategy-transfer study is complete. ReProver cloud
accuracy is 53.91%, centroid54.49%; paired gain -0.59 points, marginal bootstrap
95% interval [-2.54,+1.37] points. All cheap-control headroom diagnostics pass;
none of the nine paired superiority comparisons passes. See the complete
[report](../../docs/gpu-execution-results-v1.md).

The user subsequently cancelled the original CPU confirmation. No partial CPU outcome was scored; the complete GPU run supplies the
experimental result. Its verified proofs,
assignment and completed syntax/MiniLM vectors are shared from
`../strategy-transfer-confirmation-v1/`; CPU cancellation is recorded there.

Files:
- `inputs.json`: every input string, source hashes and provenance; no task labels.
- `run/`: all 8,500 GPU vectors, device manifest and acquisition completion record.
- `headroom.json`: cheap-control diagnostic saved before GPU cloud scoring.
- `report.json`: all three cloud arms, nine controls, paired comparisons and
  original-plan proof controls. CPU syntax/MiniLM and GPU ReProver are explicit.
- `validation.json`, `full-validation.json`: numerical and source/input reproduction.
- `acquisition.log`: complete GPU acquisition progress and manifest.
- `figures/`: shareable effect-interval plots.

With the repository's pinned base Python environment, no GPU, model weights,
network access or Lean installation is needed to reproduce the saved numbers:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/verify-gpu-execution.py
```

To repeat encoding on a CUDA machine, install `requirements-reprover.lock` and
the pinned NumPy version, bootstrap the model with `scripts/bootstrap-reprover.py`,
then run:

```bash
python scripts/encode-reprover-gpu.py \
  --inputs results/gpu-execution-check-v1/inputs.json \
  --model .tools/reprover --output outputs/new-gpu-encoding
```

The output directory must be new. Retain singleton batches and the frozen
int8_float32 configuration. Do not treat CPU and GPU output caches as identical.
The cloud/centroid inference code is the original frozen implementation; the
hardware check adds no minimum-gain threshold or alternative success route.
