# Active State-object dataset

**102 theorem groups, 813 source proof records, 16,592 recorded states and
16,592 separate physical vector rows.** Every state of each admitted theorem is
retained, including repeated inputs and equal coordinates. No deduplication.

Open [the active explorer](explore.html). This is exploratory geometry of recorded
goal displays; proof eligibility does not establish complete internal state capture
or validate the encoder as a model of mathematical relationships.

The enforced admission rule excludes six theorem groups with Lean-verified
contradictory assumptions (44 source proof records and 558 states). It holds
148 other groups with unresolved theorem identity or incomplete inventoried
proof evidence/trace coverage (9,670 recorded states). Held does not mean false.
There are no partially admitted theorem groups and no state caps.

`admission.json` gives every decision and pins its evidence. The full 26,820-row
archive remains in `../state-object-records-v1/` for recovery and repair; it is no
longer the active analysis dataset. Proof sources and failed attempts remain
in `../state-object-v1/`. No historical data were destroyed.

The new uncompressed NPY chunks physically store every admitted row. Coordinates
are bitwise identical to their saved encoder outputs. The projection and all-pairs
results were rebuilt for this admitted set; neither includes excluded/held groups.

```sh
python scripts/verify-theorem-admission-archive.py
python scripts/verify-state-record-vectors.py --records results/state-objects-admitted-v1
OPENBLAS_NUM_THREADS=1 python scripts/analyze-state-record-objects.py \
  --records results/state-objects-admitted-v1
```

Read the [remediation report](../../docs/theorem-admission-remediation-v1.md)
for the remaining acquisition and interpretation issues. A failed contradiction
search is never counted as proof of consistency.
