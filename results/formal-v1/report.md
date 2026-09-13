# Controlled formal proof-cloud feasibility study

Gate: **failed**.

- cross-generator association does not survive all required controls
- cloud geometry does not add the required information beyond centroids
- a primary representation collapses

This is a generated propositional population, not a survey of mathematics. The text encoder is pretrained on general text. No cross-domain H3/H4 claim follows.

All reported clouds use 32 distinct proofs × 4 states = 128 occurrences. Inference permutes whole theorem labels, keeping proof/state blocks intact.

| Encoder | View | Split | Theorems | Cloud win | Centroid win | Single proof | Statement | q |
|---|---|---|---:|---:|---:|---:|---:|---:|
| syntax | full | cross | 24 | 0.391 | 1.000 | 0.342 | 1.000 | 1 |
| syntax | full | backward | 24 | 1.000 | 1.000 | 1.000 | 1.000 | 0.0001714 |
| syntax | goal | cross | 24 | 0.500 | 0.500 | 0.500 | 0.500 | 1 |
| syntax | goal | backward | 24 | 0.848 | 0.846 | 0.521 | 0.500 | 0.0001714 |
| truth | full | cross | 24 | 0.500 | 0.500 | 0.500 | 0.500 | 1 |
| truth | full | backward | 24 | 0.848 | 0.842 | 0.511 | 0.500 | 0.0001714 |
| truth | goal | cross | 24 | 0.500 | 0.500 | 0.500 | 0.500 | 1 |
| truth | goal | backward | 24 | 0.848 | 0.842 | 0.511 | 0.500 | 0.0001714 |
| minilm | full | cross | 24 | 0.862 | 0.877 | 0.777 | 1.000 | 0.0001714 |
| minilm | full | backward | 24 | 1.000 | 1.000 | 1.000 | 1.000 | 0.0001714 |
| minilm | goal | cross | 24 | 0.500 | 0.500 | 0.500 | 0.500 | 1 |
| minilm | goal | backward | 24 | 0.806 | 0.804 | 0.509 | 0.500 | 0.0001714 |

Win rates count tied matches as half; chance is 0.5. The initial-state baseline includes the complete premise context. Goal-only views remove that context from every state.

BH family: 12 tests. Skipped comparisons: 12; details are in JSON.

The result does not justify interpreting cross-theorem overlaps as mathematical discoveries. Full matrices, split identities, and representation collapse diagnostics are retained in the JSON report.

## Theorem-level uncertainty

Exploratory 95% paired theorem-cluster percentile intervals, conditional on the observed proof samples. Both matrix axes are resampled jointly. These intervals are not simultaneous or population-wide guarantees.

| Encoder | View | Split | Cloud win (95% CI) | Gain over centroid (95% CI) |
|---|---|---|---|---|
| syntax | full | cross | 0.391 (0.267, 0.525) | -0.609 (-0.733, -0.475) |
| syntax | full | backward | 1.000 (1.000, 1.000) | 0.000 (0.000, 0.000) |
| syntax | goal | cross | 0.500 (0.500, 0.500) | 0.000 (0.000, 0.000) |
| syntax | goal | backward | 0.848 (0.734, 0.938) | 0.002 (-0.008, 0.012) |
| truth | full | cross | 0.500 (0.500, 0.500) | 0.000 (0.000, 0.000) |
| truth | full | backward | 0.848 (0.733, 0.937) | 0.005 (-0.008, 0.023) |
| truth | goal | cross | 0.500 (0.500, 0.500) | 0.000 (0.000, 0.000) |
| truth | goal | backward | 0.848 (0.733, 0.937) | 0.005 (-0.008, 0.023) |
| minilm | full | cross | 0.862 (0.782, 0.934) | -0.014 (-0.059, 0.031) |
| minilm | full | backward | 1.000 (1.000, 1.000) | 0.000 (0.000, 0.000) |
| minilm | goal | cross | 0.500 (0.500, 0.500) | 0.000 (0.000, 0.000) |
| minilm | goal | backward | 0.806 (0.680, 0.910) | 0.002 (-0.019, 0.025) |

## Sampling and diversity sensitivity

Descriptive repeats; no additional p-values or threshold changes.

| Encoder | View | Policy | Seed | Cloud win | Centroid win |
|---|---|---|---:|---:|---:|
| syntax | full | primary | 316843 | 0.389 | 1.000 |
| syntax | full | primary | 316844 | 0.386 | 1.000 |
| syntax | full | premise_set | 316842 | 0.411 | 1.000 |
| syntax | goal | primary | 316843 | 0.500 | 0.500 |
| syntax | goal | primary | 316844 | 0.500 | 0.500 |
| syntax | goal | premise_set | 316842 | 0.500 | 0.500 |
| truth | full | primary | 316843 | 0.500 | 0.500 |
| truth | full | primary | 316844 | 0.500 | 0.500 |
| truth | full | premise_set | 316842 | 0.500 | 0.500 |
| truth | goal | primary | 316843 | 0.500 | 0.500 |
| truth | goal | primary | 316844 | 0.500 | 0.500 |
| truth | goal | premise_set | 316842 | 0.500 | 0.500 |
| minilm | full | primary | 316843 | 0.882 | 0.889 |
| minilm | full | primary | 316844 | 0.866 | 0.866 |
| minilm | full | premise_set | 316842 | 0.868 | 0.879 |
| minilm | goal | primary | 316843 | 0.500 | 0.500 |
| minilm | goal | primary | 316844 | 0.500 | 0.500 |
| minilm | goal | premise_set | 316842 | 0.500 | 0.500 |

## Operational graph fidelity

Edge-versus-nonedge distance AUC within one proof per theorem/generator; chance is 0.5. The backward tree and forward derived-fact graph differ. These are external validation targets, not encoder inputs.

| Encoder | View | Generator | Theorems | Mean AUC |
|---|---|---|---:|---:|
| syntax | full | backward | 24 | 0.526 |
| syntax | full | forward | 24 | 0.718 |
| syntax | goal | backward | 24 | 0.655 |
| syntax | goal | forward | 24 | 0.500 |
| truth | full | backward | 24 | 0.656 |
| truth | full | forward | 24 | 0.500 |
| truth | goal | backward | 24 | 0.656 |
| truth | goal | forward | 24 | 0.500 |
| minilm | full | backward | 24 | 0.505 |
| minilm | full | forward | 24 | 0.637 |
| minilm | goal | backward | 24 | 0.587 |
| minilm | goal | forward | 24 | 0.500 |
