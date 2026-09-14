# State-input identity audit

See the [findings and corrected interpretation](../../docs/state-input-identity-audit-v1.md).
The original `state-object-v1` corpus and coordinates are unchanged.

- `summary.json`: exhaustive repetition counts and risk flags.
- `state-records.json.gz`: every one of 26,820 provenance-identified state records,
  each with an explicit reference to its archived vector chunk/row.
- `input-groups.json.gz`: all 3,659 input strings, record memberships, source and
  environment associations, and semantic-identity status (unverified).
- `Counterexamples.lean`, `counterexamples-lean49.log`,
  `counterexample-verification.json`: compiled Lean4.9 counterexamples showing
  that identical printed goals need not identify identical internal goals or
  complete proof states. The fixture contains no `sorry`.
- `shared-local-goal-sources.json`: every source proof and observation involved
  in the only nonempty input shared between theorem IDs.
- `audit-manifest.json`: source archive and script fingerprints; no new encoder
  or GPU compute was used and no original coordinates were modified.
- `lean-runtime.json`: pinned compiler download and executable hashes.
- `SHA256SUMS`: artifact integrity checks.

To reproduce the corpus audit without Lean or GPU:

```sh
OPENBLAS_NUM_THREADS=1 python scripts/audit-state-object-inputs.py \
  --archive results/state-object-v1 --output outputs/state-identity-recheck
```

To rerun the controlled compiler examples, add `--lean /path/to/lean-4.9.0/bin/lean`.
They import only Lean and require no Mathlib download. Tests also check the
archived counterexample source hash and recompute the corpus-wide counts.

Environment-label differences, parent-theorem-expression differences and visible
elision are risk flags, not counts of proven false semantic merges. The actual
number of such merges is unknown because internal state snapshots were not
retained. Every original record and vector association is preserved.
