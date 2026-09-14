# Canonical replay: matched theorem-cloud experiment

Two discovery algorithms, one replay convention; fresh restricted Horn population.

Regime: {'metric': 'energy_statistic', 'm': 32, 'n': 4, 'd': 384, 'noise': 0.02}. Primary tests: 9 (one BH family).

| Encoder | Comparison | Cloud win | Centroid win | Gain | p | Primary q |
|---|---|---:|---:|---:|---:|---:|
| syntax | cross | 1.0000 | 1.0000 | 0.0000 | 0.0001 | 0.0001 |
| syntax | backward | 1.0000 | 1.0000 | 0.0000 | 0.0001 | 0.0001 |
| syntax | forward | 1.0000 | 1.0000 | 0.0000 | 0.0001 | 0.0001 |
| syntax | unmatched | 1.0000 | 1.0000 | 0.0000 | 0.0001 | secondary |
| syntax | goal_diagnostic | 0.9545 | 0.9091 | 0.0455 | 0.0001 | secondary |
| syntax | cross_alternative | 1.0000 | 1.0000 | 0.0000 | 0.0001 | secondary |
| truth | cross | 0.9318 | 0.9167 | 0.0152 | 0.0001 | 0.0001 |
| truth | backward | 0.9697 | 0.9773 | -0.0076 | 0.0001 | 0.0001 |
| truth | forward | 0.9848 | 0.9697 | 0.0152 | 0.0001 | 0.0001 |
| truth | unmatched | 0.7576 | 0.7500 | 0.0076 | 0.0002 | secondary |
| truth | goal_diagnostic | 0.9318 | 0.9167 | 0.0152 | 0.0001 | secondary |
| truth | cross_alternative | 0.9773 | 0.9697 | 0.0076 | 0.0001 | secondary |
| minilm | cross | 1.0000 | 1.0000 | 0.0000 | 0.0001 | 0.0001 |
| minilm | backward | 1.0000 | 1.0000 | 0.0000 | 0.0001 | 0.0001 |
| minilm | forward | 1.0000 | 1.0000 | 0.0000 | 0.0001 | 0.0001 |
| minilm | unmatched | 1.0000 | 1.0000 | 0.0000 | 0.0001 | secondary |
| minilm | goal_diagnostic | 0.9470 | 0.9091 | 0.0379 | 0.0001 | secondary |
| minilm | cross_alternative | 1.0000 | 1.0000 | 0.0000 | 0.0001 | secondary |

Gate: {'matched_text_reproducibility': True, 'added_information_over_centroid': False, 'noncollapsed': True, 'advance': False, 'interpretation': 'stop conditional discovery: matched reproducibility or added-information gate failed'}

Primary comparisons have exactly identical length/raw-depth histograms across all groups.
Unmatched uses the unrestricted candidate bank at the same proof/state count. Goal-only
and alternative proof splits are diagnostics. Secondary p-values are descriptive, not
additional confirmatory discoveries. Full baseline matrices, paired theorem-bootstrap
intervals, diversity coverage and representation audits are retained in JSON.
