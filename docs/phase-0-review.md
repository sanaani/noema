# Phase 0 review and bounded protocol freeze

The higher-precision preregistered replication **passed every target stratum**. The restricted synthetic measurement protocol is frozen at source revision `e9df8a3953024c9748fd1480c291d887ce74af1f`. Protocol v1 remains a failed run; v2 is reported separately rather than replacing it.

## Evidence reviewed

- `configs/qualification-v2.json` matches the output configuration hash.
- Provenance records the preregistration commit and a clean working tree at launch.
- All 9,000 comparisons and 21 scenario/dimension summaries are present.
- Every null stratum has 1,000 trials; every alternative/exploratory stratum has 200.
- Null rejection rates ranged from 0.042 to 0.054; their 95% Wilson upper bounds ranged from about 0.056 to 0.070, all below 0.10.
- Each designated alternative had 200/200 detections in every dimension, with lower Wilson bound about 0.981, above 0.80.
- Formulas, bandwidth policy, alpha, and acceptance thresholds were unchanged between v1 and v2. The increased null replication budget resolved the precision concern without changing the decision rule.

The frozen definitions are in [protocol v1](protocol-v1.md), with the replication design in [protocol v2](protocol-v2.md). The [v2 report](../results/qualification-v2/report.md) retains all per-stratum results. The earlier [failed v1 report](../results/qualification-v1/report.md) and [high-noise pilot failures](../results/pilot-v1/report.md) remain part of the evidence.

## What this permits

Proceed to a small verified formal-corpus feasibility study. The synthetic qualification applies to 128 iid points from the specified two-dimensional shapes, embedded isometrically into dimensions 2,64,256 with per-coordinate noise 0.02. It does not establish arbitrary embedding robustness, meaningful topology, or any mathematical theorem-geometry hypothesis. In particular, the higher-noise regime failed calibration.

The formal experiment remains exploratory because its states are correlated, its representation distribution is different, and its general-text encoder has not been validated as a mathematical encoder. Whole-theorem label permutations replace iid point permutations. Corpus adequacy, encoder robustness, shared-premise controls, and added information beyond centroids remain live gates.
