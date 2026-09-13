# Noema synthetic validation

Gate: **not_qualified**. Development run or insufficient trials/permutations; no metric freeze.

Synthetic results assess the measurement pipeline only. No formal proofs or theorem-geometry hypotheses have been tested.

Configuration SHA-256: `c2c65287f225601b1499a01efc8860deaaea926105e3e5e575ff4390e97b5337`

Seed 20260913; 12 trials per stratum; 199 permutations; alpha 0.05.

Primary test: pooled-bandwidth MMD². BH family: 336 tests.

Rejection rates use raw p-values for calibration/power. BH rates use the entire run as one family. Intervals are pointwise 95% Wilson intervals, not simultaneous bounds. Same-closer compares MMD²(anchor, replicate) with MMD²(anchor, comparison).

| Scenario | n | d | Noise | Reject (95% CI) | BH discoveries | Same closer |
|---|---:|---:|---:|---:|---:|---:|
| branches_vs_ring | 32 | 2 | 0.05 | 1.00 (0.76–1.00) | 0.92 | 1.00 |
| branches_vs_ring | 32 | 64 | 0.05 | 0.92 (0.65–0.99) | 0.75 | 1.00 |
| branches_vs_ring | 64 | 2 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |
| branches_vs_ring | 64 | 64 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |
| partial_overlap | 32 | 2 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |
| partial_overlap | 32 | 64 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |
| partial_overlap | 64 | 2 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |
| partial_overlap | 64 | 64 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |
| ring_vs_disk | 32 | 2 | 0.05 | 0.42 (0.19–0.68) | 0.25 | 1.00 |
| ring_vs_disk | 32 | 64 | 0.05 | 0.33 (0.14–0.61) | 0.08 | 1.00 |
| ring_vs_disk | 64 | 2 | 0.05 | 0.75 (0.47–0.91) | 0.75 | 0.92 |
| ring_vs_disk | 64 | 64 | 0.05 | 0.75 (0.47–0.91) | 0.67 | 1.00 |
| same_gaussian | 32 | 2 | 0.05 | 0.08 (0.01–0.35) | 0.08 | 0.50 |
| same_gaussian | 32 | 64 | 0.05 | 0.08 (0.01–0.35) | 0.08 | 0.50 |
| same_gaussian | 64 | 2 | 0.05 | 0.00 (0.00–0.24) | 0.00 | 0.50 |
| same_gaussian | 64 | 64 | 0.05 | 0.00 (0.00–0.24) | 0.00 | 0.33 |
| same_ring | 32 | 2 | 0.05 | 0.00 (0.00–0.24) | 0.00 | 0.58 |
| same_ring | 32 | 64 | 0.05 | 0.08 (0.01–0.35) | 0.08 | 0.50 |
| same_ring | 64 | 2 | 0.05 | 0.08 (0.01–0.35) | 0.08 | 0.33 |
| same_ring | 64 | 64 | 0.05 | 0.00 (0.00–0.24) | 0.00 | 0.25 |
| separated | 32 | 2 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |
| separated | 32 | 64 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |
| separated | 64 | 2 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |
| separated | 64 | 64 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |
| unimodal_vs_mixture | 32 | 2 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |
| unimodal_vs_mixture | 32 | 64 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |
| unimodal_vs_mixture | 64 | 2 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |
| unimodal_vs_mixture | 64 | 64 | 0.05 | 1.00 (0.76–1.00) | 1.00 | 1.00 |

## Metric diagnostics

Medians across trials; smaller distances indicate more similarity. Radius coverage is a diagnostic with larger values indicating more overlap. Its radius is half the pooled kernel bandwidth and changes between pairs; compare cautiously.

| Scenario | n | d | Noise | MMD² | Energy | Sliced W1 | Coverage | Centroid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| branches_vs_ring | 32 | 2 | 0.05 | 0.1248 | 0.2662 | 0.3569 | 0.5469 | 0.2269 |
| branches_vs_ring | 32 | 64 | 0.05 | 0.0775 | 0.1669 | 0.0493 | 0.1641 | 0.1685 |
| branches_vs_ring | 64 | 2 | 0.05 | 0.0975 | 0.2096 | 0.3336 | 0.6055 | 0.1229 |
| branches_vs_ring | 64 | 64 | 0.05 | 0.0732 | 0.1451 | 0.0483 | 0.2656 | 0.1173 |
| partial_overlap | 32 | 2 | 0.05 | 0.2461 | 0.5008 | 0.4680 | 0.8203 | 0.7451 |
| partial_overlap | 32 | 64 | 0.05 | 0.2025 | 0.4465 | 0.0753 | 0.2812 | 0.7304 |
| partial_overlap | 64 | 2 | 0.05 | 0.2285 | 0.4836 | 0.4808 | 0.8828 | 0.7493 |
| partial_overlap | 64 | 64 | 0.05 | 0.1956 | 0.4120 | 0.0682 | 0.2852 | 0.7294 |
| ring_vs_disk | 32 | 2 | 0.05 | 0.0660 | 0.1575 | 0.2699 | 0.9141 | 0.2254 |
| ring_vs_disk | 32 | 64 | 0.05 | 0.0545 | 0.1383 | 0.0428 | 0.5781 | 0.2199 |
| ring_vs_disk | 64 | 2 | 0.05 | 0.0446 | 0.1101 | 0.2378 | 0.9414 | 0.0601 |
| ring_vs_disk | 64 | 64 | 0.05 | 0.0364 | 0.0847 | 0.0348 | 0.7188 | 0.1161 |
| same_gaussian | 32 | 2 | 0.05 | 0.0280 | 0.0594 | 0.1623 | 0.9141 | 0.1601 |
| same_gaussian | 32 | 64 | 0.05 | 0.0257 | 0.0639 | 0.0301 | 0.1328 | 0.1792 |
| same_gaussian | 64 | 2 | 0.05 | 0.0128 | 0.0261 | 0.1041 | 0.9688 | 0.1000 |
| same_gaussian | 64 | 64 | 0.05 | 0.0126 | 0.0315 | 0.0210 | 0.2461 | 0.1313 |
| same_ring | 32 | 2 | 0.05 | 0.0175 | 0.0713 | 0.1839 | 1.0000 | 0.2171 |
| same_ring | 32 | 64 | 0.05 | 0.0163 | 0.0710 | 0.0306 | 1.0000 | 0.2291 |
| same_ring | 64 | 2 | 0.05 | 0.0055 | 0.0235 | 0.1021 | 1.0000 | 0.1204 |
| same_ring | 64 | 64 | 0.05 | 0.0065 | 0.0324 | 0.0224 | 1.0000 | 0.1257 |
| separated | 32 | 2 | 0.05 | 1.1636 | 4.3744 | 1.8929 | 0.0234 | 2.9922 |
| separated | 32 | 64 | 0.05 | 1.1268 | 4.3217 | 0.3144 | 0.0000 | 3.0544 |
| separated | 64 | 2 | 0.05 | 1.1677 | 4.4144 | 1.9053 | 0.0234 | 2.9997 |
| separated | 64 | 64 | 0.05 | 1.1056 | 4.1554 | 0.3082 | 0.0156 | 3.0052 |
| unimodal_vs_mixture | 32 | 2 | 0.05 | 0.1648 | 0.2972 | 0.3584 | 0.6953 | 0.1979 |
| unimodal_vs_mixture | 32 | 64 | 0.05 | 0.1197 | 0.2406 | 0.0549 | 0.2578 | 0.2222 |
| unimodal_vs_mixture | 64 | 2 | 0.05 | 0.1376 | 0.2589 | 0.3426 | 0.8242 | 0.1225 |
| unimodal_vs_mixture | 64 | 64 | 0.05 | 0.1043 | 0.1795 | 0.0492 | 0.3711 | 0.1035 |

## Interpretation limits

- Same-shape samples are independent, not identical arrays.
- Ring/disk, Gaussian/mixture, and branches/ring share population centroids; finite-sample centroids fluctuate.
- Noise is per ambient coordinate; increasing dimension increases total noise.
- Sliced Wasserstein averages 1D projections; it is not full-dimensional transport.
- Candidate metrics and thresholds are not yet scientifically qualified or frozen.
- Proof states are correlated; future proof experiments require proof/theorem-level sampling and nulls rather than this iid permutation test.
