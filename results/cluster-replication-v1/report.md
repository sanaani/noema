# Clustered proof/state power envelope

held_out_replication

Proof-block permutations; alpha .05. Minima require power Wilson lower bound >=.80 and both null upper bounds <=.10. Unqualified cells are retained. These are grid minima under the specified correlation model, not universal bounds.

| Metric | d | Noise | Family | Effect | Minimum tested m × n |
|---|---:|---:|---|---:|---|
| mmd_squared | 256 | 0.02 | separated | 0.5 | 16 × 2 |
| energy_statistic | 256 | 0.02 | separated | 0.5 | 16 × 2 |
| mmd_squared | 256 | 0.02 | separated | 1.0 | 16 × 2 |
| energy_statistic | 256 | 0.02 | separated | 1.0 | 16 × 2 |
| mmd_squared | 256 | 0.15 | separated | 0.5 | 16 × 4 |
| energy_statistic | 256 | 0.15 | separated | 0.5 | 16 × 4 |
| mmd_squared | 256 | 0.15 | separated | 1.0 | 16 × 4 |
| energy_statistic | 256 | 0.15 | separated | 1.0 | 16 × 4 |
| mmd_squared | 384 | 0.02 | gaussian_mixture | 1.0 | 32 × 4 |
| energy_statistic | 384 | 0.02 | gaussian_mixture | 1.0 | 32 × 4 |
| mmd_squared | 384 | 0.02 | separated | 0.5 | 32 × 4 |
| energy_statistic | 384 | 0.02 | separated | 0.5 | 32 × 4 |
| mmd_squared | 384 | 0.02 | separated | 1.0 | 32 × 4 |
| energy_statistic | 384 | 0.02 | separated | 1.0 | 32 × 4 |
| mmd_squared | 384 | 0.15 | separated | 0.5 | 64 × 2 |
| energy_statistic | 384 | 0.15 | separated | 0.5 | 64 × 2 |
| mmd_squared | 384 | 0.15 | separated | 1.0 | 64 × 2 |
| energy_statistic | 384 | 0.15 | separated | 1.0 | 64 × 2 |

Complete raw trials, Wilson intervals and 10000 family-adjusted tests are in JSON. Noise is per ambient coordinate.
