# Noema synthetic validation

Gate: **candidate_pass_requires_protocol_review**. A candidate pass still requires a preregistered held-out run and protocol freeze.

Synthetic results assess the measurement pipeline only. No formal proofs or theorem-geometry hypotheses have been tested.

Configuration SHA-256: `a75a52c39064ab17f4825de1368d566d92215587671063cc52eba8f3f0104c9b`

Seed 927046118; 200 trials per alternative/exploratory stratum; 1000 trials per null stratum; 999 permutations; alpha 0.05.

Primary test: pooled-bandwidth MMD². BH family: 9000 tests.

Rejection rates use raw p-values for calibration/power. BH rates use the entire run as one family. Intervals are pointwise 95% Wilson intervals, not simultaneous bounds. Same-closer compares MMD²(anchor, replicate) with MMD²(anchor, comparison).

| Scenario | n | d | Noise | Reject (95% CI) | BH discoveries | Same closer |
|---|---:|---:|---:|---:|---:|---:|
| branches_vs_ring | 128 | 2 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| branches_vs_ring | 128 | 64 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| branches_vs_ring | 128 | 256 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| partial_overlap | 128 | 2 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| partial_overlap | 128 | 64 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| partial_overlap | 128 | 256 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| ring_vs_disk | 128 | 2 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| ring_vs_disk | 128 | 64 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| ring_vs_disk | 128 | 256 | 0.02 | 1.00 (0.98–1.00) | 0.99 | 1.00 |
| same_gaussian | 128 | 2 | 0.02 | 0.05 (0.04–0.06) | 0.02 | 0.50 |
| same_gaussian | 128 | 64 | 0.02 | 0.05 (0.04–0.07) | 0.02 | 0.49 |
| same_gaussian | 128 | 256 | 0.02 | 0.05 (0.04–0.07) | 0.01 | 0.50 |
| same_ring | 128 | 2 | 0.02 | 0.05 (0.04–0.07) | 0.02 | 0.47 |
| same_ring | 128 | 64 | 0.02 | 0.05 (0.04–0.07) | 0.01 | 0.50 |
| same_ring | 128 | 256 | 0.02 | 0.04 (0.03–0.06) | 0.01 | 0.49 |
| separated | 128 | 2 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| separated | 128 | 64 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| separated | 128 | 256 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| unimodal_vs_mixture | 128 | 2 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| unimodal_vs_mixture | 128 | 64 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| unimodal_vs_mixture | 128 | 256 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |

## Metric diagnostics

Medians across trials; smaller distances indicate more similarity. Radius coverage is a diagnostic with larger values indicating more overlap. Its radius is half the pooled kernel bandwidth and changes between pairs; compare cautiously.

| Scenario | n | d | Noise | MMD² | Energy | Sliced W1 | Coverage | Centroid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| branches_vs_ring | 128 | 2 | 0.02 | 0.0982 | 0.2068 | 0.3362 | 0.5391 | 0.0833 |
| branches_vs_ring | 128 | 64 | 0.02 | 0.0902 | 0.1778 | 0.0497 | 0.5000 | 0.0852 |
| branches_vs_ring | 128 | 256 | 0.02 | 0.0742 | 0.1405 | 0.0227 | 0.3555 | 0.0901 |
| partial_overlap | 128 | 2 | 0.02 | 0.2386 | 0.4762 | 0.4813 | 0.9180 | 0.7538 |
| partial_overlap | 128 | 64 | 0.02 | 0.2332 | 0.4646 | 0.0760 | 0.8984 | 0.7540 |
| partial_overlap | 128 | 256 | 0.02 | 0.2084 | 0.4345 | 0.0379 | 0.7812 | 0.7534 |
| ring_vs_disk | 128 | 2 | 0.02 | 0.0425 | 0.0981 | 0.2229 | 0.9141 | 0.0864 |
| ring_vs_disk | 128 | 64 | 0.02 | 0.0404 | 0.0896 | 0.0347 | 0.8984 | 0.0897 |
| ring_vs_disk | 128 | 256 | 0.02 | 0.0336 | 0.0727 | 0.0162 | 0.8398 | 0.0925 |
| same_gaussian | 128 | 2 | 0.02 | 0.0053 | 0.0116 | 0.0740 | 0.9844 | 0.0716 |
| same_gaussian | 128 | 64 | 0.02 | 0.0057 | 0.0127 | 0.0124 | 0.9805 | 0.0760 |
| same_gaussian | 128 | 256 | 0.02 | 0.0055 | 0.0140 | 0.0068 | 0.8164 | 0.0837 |
| same_ring | 128 | 2 | 0.02 | 0.0040 | 0.0158 | 0.0828 | 1.0000 | 0.1021 |
| same_ring | 128 | 64 | 0.02 | 0.0044 | 0.0177 | 0.0145 | 1.0000 | 0.1105 |
| same_ring | 128 | 256 | 0.02 | 0.0041 | 0.0176 | 0.0078 | 1.0000 | 0.1086 |
| separated | 128 | 2 | 0.02 | 1.1982 | 4.4182 | 1.9061 | 0.0391 | 3.0068 |
| separated | 128 | 64 | 0.02 | 1.1788 | 4.3286 | 0.3014 | 0.0391 | 2.9919 |
| separated | 128 | 256 | 0.02 | 1.1374 | 4.2158 | 0.1495 | 0.0273 | 3.0032 |
| unimodal_vs_mixture | 128 | 2 | 0.02 | 0.1424 | 0.2609 | 0.3478 | 0.8633 | 0.0807 |
| unimodal_vs_mixture | 128 | 64 | 0.02 | 0.1331 | 0.2331 | 0.0526 | 0.8320 | 0.0830 |
| unimodal_vs_mixture | 128 | 256 | 0.02 | 0.1098 | 0.1899 | 0.0244 | 0.6953 | 0.0895 |

## Interpretation limits

- Same-shape samples are independent, not identical arrays.
- Ring/disk, Gaussian/mixture, and branches/ring share population centroids; finite-sample centroids fluctuate.
- Noise is per ambient coordinate; increasing dimension increases total noise.
- Sliced Wasserstein averages 1D projections; it is not full-dimensional transport.
- Candidate metrics and thresholds are not yet scientifically qualified or frozen.
- Proof states are correlated; future proof experiments require proof/theorem-level sampling and nulls rather than this iid permutation test.
