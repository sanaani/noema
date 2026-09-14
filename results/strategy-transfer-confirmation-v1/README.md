# Threshold-free nine-leaf confirmation archive

The population, proof acquisition, independent reconstruction, and syntax/MiniLM
encoding are complete. The user cancelled the original CPU ReProver acquisition
at 7,270/8,500 cached inputs after the complete separate GPU result was available.
No partial CPU confirmation was scored. See `cancellation.json` and the
[status report](../../docs/strategy-transfer-confirmation-results-v1.md).

The archive includes the frozen 512-triplet plan, source/protocol checksums,
72-row power calculation, independent full bank/transfer and assignment checks,
all 6,144 recorded Lean proofs and 30,720 intermediate-state checks, complete
syntax and MiniLM vectors, and acquisition provenance. Incomplete CPU ReProver
checkpoints remain locally; their counts and hashes are in `cancellation.json`.
There is intentionally no complete CPU `run/report.json`.

The complete GPU vector/analysis archive is `../gpu-execution-check-v1/`.
It references this population and the completed syntax/MiniLM vectors, and keeps
its GPU ReProver arm separate. Its supplementary designation and the later CPU
cancellation are preserved rather than relabeled as the original primary result.

Reproduce population, proof-bank, transfer-label and recorded Lean checks with:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/verify-transfer-confirmation.py
```

Add `--regenerate-assignments` to repeat the full deterministic search; its exact
match is already recorded in `assignment-reproduction.json`. Neither command
requires rerunning Lean or downloading encoder weights. The full GPU numerical
study is reproduced with `python scripts/verify-gpu-execution.py`.
