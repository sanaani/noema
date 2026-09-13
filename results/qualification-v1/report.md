# Noema synthetic validation

Gate: **failed**. One or more target strata failed the fixed calibration/power thresholds.

Synthetic results assess the measurement pipeline only. No formal proofs or theorem-geometry hypotheses have been tested.

Configuration SHA-256: `d4ed8146b0567a76354e70c1ae9fc151bfa5cc12ece0792e7b7216eab8a461ff`

Seed 608193427; 200 trials per stratum; 999 permutations; alpha 0.05.

Primary test: pooled-bandwidth MMD². BH family: 4200 tests.

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
| ring_vs_disk | 128 | 256 | 0.02 | 1.00 (0.98–1.00) | 1.00 | 1.00 |
| same_gaussian | 128 | 2 | 0.02 | 0.06 (0.03–0.10) | 0.05 | 0.46 |
| same_gaussian | 128 | 64 | 0.02 | 0.08 (0.05–0.13) | 0.05 | 0.59 |
| same_gaussian | 128 | 256 | 0.02 | 0.04 (0.02–0.07) | 0.01 | 0.52 |
| same_ring | 128 | 2 | 0.02 | 0.04 (0.02–0.08) | 0.03 | 0.43 |
| same_ring | 128 | 64 | 0.02 | 0.04 (0.02–0.07) | 0.01 | 0.48 |
| same_ring | 128 | 256 | 0.02 | 0.07 (0.05–0.12) | 0.05 | 0.48 |
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
| branches_vs_ring | 128 | 2 | 0.02 | 0.0993 | 0.2087 | 0.3367 | 0.5430 | 0.0877 |
| branches_vs_ring | 128 | 64 | 0.02 | 0.0917 | 0.1807 | 0.0499 | 0.4980 | 0.0865 |
| branches_vs_ring | 128 | 256 | 0.02 | 0.0742 | 0.1406 | 0.0228 | 0.3633 | 0.0993 |
| partial_overlap | 128 | 2 | 0.02 | 0.2385 | 0.4790 | 0.4822 | 0.9141 | 0.7543 |
| partial_overlap | 128 | 64 | 0.02 | 0.2298 | 0.4644 | 0.0761 | 0.9004 | 0.7533 |
| partial_overlap | 128 | 256 | 0.02 | 0.2065 | 0.4365 | 0.0377 | 0.7871 | 0.7600 |
| ring_vs_disk | 128 | 2 | 0.02 | 0.0423 | 0.0989 | 0.2212 | 0.9180 | 0.0900 |
| ring_vs_disk | 128 | 64 | 0.02 | 0.0413 | 0.0905 | 0.0343 | 0.8984 | 0.0972 |
| ring_vs_disk | 128 | 256 | 0.02 | 0.0339 | 0.0740 | 0.0163 | 0.8398 | 0.0979 |
| same_gaussian | 128 | 2 | 0.02 | 0.0052 | 0.0113 | 0.0737 | 0.9844 | 0.0736 |
| same_gaussian | 128 | 64 | 0.02 | 0.0058 | 0.0129 | 0.0126 | 0.9805 | 0.0793 |
| same_gaussian | 128 | 256 | 0.02 | 0.0055 | 0.0142 | 0.0067 | 0.8066 | 0.0837 |
| same_ring | 128 | 2 | 0.02 | 0.0039 | 0.0155 | 0.0831 | 1.0000 | 0.0985 |
| same_ring | 128 | 64 | 0.02 | 0.0042 | 0.0167 | 0.0140 | 1.0000 | 0.1058 |
| same_ring | 128 | 256 | 0.02 | 0.0044 | 0.0182 | 0.0078 | 1.0000 | 0.1128 |
| separated | 128 | 2 | 0.02 | 1.1965 | 4.4009 | 1.9088 | 0.0391 | 2.9966 |
| separated | 128 | 64 | 0.02 | 1.1815 | 4.3574 | 0.3005 | 0.0352 | 2.9984 |
| separated | 128 | 256 | 0.02 | 1.1360 | 4.2151 | 0.1482 | 0.0234 | 3.0000 |
| unimodal_vs_mixture | 128 | 2 | 0.02 | 0.1431 | 0.2600 | 0.3483 | 0.8633 | 0.0862 |
| unimodal_vs_mixture | 128 | 64 | 0.02 | 0.1325 | 0.2300 | 0.0528 | 0.8320 | 0.0860 |
| unimodal_vs_mixture | 128 | 256 | 0.02 | 0.1062 | 0.1834 | 0.0241 | 0.6953 | 0.0888 |

## Interpretation limits

- Same-shape samples are independent, not identical arrays.
- Ring/disk, Gaussian/mixture, and branches/ring share population centroids; finite-sample centroids fluctuate.
- Noise is per ambient coordinate; increasing dimension increases total noise.
- Sliced Wasserstein averages 1D projections; it is not full-dimensional transport.
- Candidate metrics and thresholds are not yet scientifically qualified or frozen.
- Proof states are correlated; future proof experiments require proof/theorem-level sampling and nulls rather than this iid permutation test.
