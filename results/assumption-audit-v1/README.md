# Assumption audit evidence

Read the [audit report](../../docs/assumption-audit-v1.md) for interpretation.
These files annotate the existing sample; they do not remove or merge any state.

- `summary.json`: counts, source hashes, remaining limitations and numerical regressions.
- `duplicate-script-groups.json`: exact script copies within theorem groups.
- `replay-checks.json`: source/environment checks for 1,429 attempts and exact-target
  axiom checks for all 1,317 accepted attempts.
- `theorem-annotations.json`: claim limitations for all 256 theorem groups and the
  known inconsistent-assumptions example. Unverified flags are not exclusion rules.
- `Vacuous.lean`, `vacuity-verification.json`: independently checked inconsistency
  of the assumptions of `workbook:lean_workbook_plus_5257`, using Lean4.9.0.
- `negative-weight-before.json`: reproduced incorrect intersections from commit
  `8c42e6d`, before the numerical validation fix.
- `SHA256SUMS`: integrity of this evidence.

Recompute the census and retrospective checks without an encoder or GPU:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/audit-state-object-assumptions.py \
  --output outputs/repeated-assumption-audit
```

Recheck `Vacuous.lean` with Lean4.9.0. It imports only Lean, not Mathlib.
The saved verification pins the binary and fixture hashes and records stdout and
exit status. This diagnostic establishes one finding; other theorem assumptions
were not exhaustively checked for consistency.
