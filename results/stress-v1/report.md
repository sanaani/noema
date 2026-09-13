# Supplementary measurement stress audit

exploratory_only; frozen qualification scope unchanged

| Scenario | Kind | Rejection rate (95% Wilson CI) | BH rate |
|---|---|---|---:|
| anisotropic_null | null | 0.05 (0.022, 0.112) | 0.04 |
| narrow_axis_shift | alternative | 1.00 (0.963, 1.000) | 1.00 |
| rotated_isotropic_null | null | 0.04 (0.016, 0.098) | 0.01 |
| sampler_weights | alternative | 1.00 (0.963, 1.000) | 1.00 |

BH family: 400 tests. Raw metrics and transformation deltas are in JSON.

The sampler-weight alternative changes the empirical distribution even though its possible component support is unchanged. This is a sampler-bias diagnostic, not evidence of a change in mathematical content.
