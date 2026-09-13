# Checkpoint 2: executable synthetic foundation

Checkpoints 1 and 2 of the [implementation plan](implementation-plan.md) are complete. The private repository was created under `sanaani`, and the initial commit `c8937aa` preserved the original proposal before implementation began. The preserved document's SHA-256 is `71879a5fb462f8decfd0ad329347b5e4932792a933636d4dc0ea09e52d599f5a`.

Implementation commit `9a8c41b38028838b9ee5138b65a4202e01b182a0` contains the measurement package, configurable experiment CLI, tests, dependency pins, and CI. The [reference report](../results/reference-smoke/report.md) and [full trial records](../results/reference-smoke/report.json) were generated from that clean revision. The earlier development run and clean-revision run reproduced every scientific output exactly; only provenance differed.

## Validation

- 40 tests passed, including direct permutation references, a small exact permutation distribution, and repeated null/alternative experiments.
- Ruff lint, format verification, and Git whitespace checks passed.
- The reference experiment completed all 336 comparisons using the committed smoke configuration.
- Every output records configuration, seeds, dependency versions, source revision, and statistical family. The report refuses scientific qualification for development settings.

## Observations from the smoke run

The following counts aggregate four size/dimension strata for a compact execution summary. They are descriptive; the report retains each stratum and its uncertainty separately.

| Scenario | Raw MMD rejections at alpha 0.05 |
|---|---:|
| Independent Gaussian samples | 2 / 48 |
| Independent ring samples | 2 / 48 |
| Partial-overlap Gaussian populations | 48 / 48 |
| Separated Gaussian populations | 48 / 48 |
| Ring versus disk | 27 / 48 |
| Gaussian versus mixture | 48 / 48 |
| Branches versus ring | 47 / 48 |

Ring-versus-disk detection was weakest: at n=32, the raw rejection rates were 0.42 in d=2 and 0.33 in d=64; at n=64, both were 0.75. These cases have equal population centroids, and the candidate pipeline does not yet detect this distribution change reliably at the smaller sample count. No parameters or gates were changed in response to these results.

The geometry code contains holes/branches as synthetic inputs but does not estimate persistent homology. Sliced transport and radius coverage remain diagnostics. There is no Lean integration or learned encoder yet.

## Next checkpoint

Run the committed pilot configuration to characterize sample count, ambient dimension, and noise sensitivity. Investigate ring-versus-disk sensitivity using calibration data before proposing any metric revisions. Then commit a held-out qualification protocol with adequate trials and permutation resolution. The current gate is **not qualified**, and metric selection remains open. Formal-proof collection begins only after the measurement gate is resolved.
