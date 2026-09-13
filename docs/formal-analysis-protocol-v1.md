# Formal feasibility analysis v1

This protocol is fixed before corpus embeddings or cross-theorem distances are computed. It is a feasibility study in generated Horn logic, not a confirmatory test over mathematics at large.

## Eligibility and sampling

Use the 24-theorem corpus population and 64-proof-per-generator search budget specified in the corpus protocol. Remove shared proof identities and duplicate normalized state sequences before splitting. A proof needs at least four retained intermediate states. Primary cross-generator clouds use 32 distinct proofs per generator and four sampled state occurrences per proof, yielding 128 points on each side. Sampling is without replacement at both levels; identical content observed at different occurrences may remain. Fixed seed 316842 controls splitting and state sampling. At least 12 eligible theorems are required for a report to evaluate the feasibility gate; fewer means inadequate corpus coverage.

Within-generator replication uses two disjoint sets of 32 proofs where 64 eligible proofs exist. These results are secondary and can have a different eligible theorem set. Never fabricate missing states or count repeated proof identities as independent.

## Encoders and leakage controls

Each encoder receives only one state's formal content. Remove case labels, binder names, and declaration order, retaining formula content and multiplicities. The restricted parser rejects unsupported expressions. Primary views are full content and current goal only. The goal-only view removes the shared-premise fingerprint. All theorems share the same file, propositional vocabulary, mathematical domain, atom count, rule count, and final conclusion; this intentionally makes goal-only statement similarity uninformative.

1. Pretrained text representation: `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, quantized AVX2 ONNX export. It is a general-text encoder, not established as a Lean semantic encoder. Use fixed nonoverlapping windows of 254 content tokens with special boundary tokens, content-token-weighted pooling, and L2 normalization. Retain every token. Record model and tokenizer checksums. No fine-tuning on this corpus. Output dimension 384; this is an explicit extrapolation beyond the three exact Phase 0 ambient dimensions, so formal results remain exploratory.
2. Syntax baseline: fixed signed SHA-256 token 1–3-gram counts in 256 dimensions, L2 normalized. No training.
3. Exact semantic control: 256 truth-table coordinates over eight atoms, each encoding `2 * context_satisfied + goal_satisfied`, scaled by 48. This is a denotational control, not a learned latent representation. It deliberately collapses equivalent formula content and may lose proof-operational distinctions.

Before any H1 claim, record identical-vector rates, dimensionality, finite-value checks, and comparison to goal-only and initial-state baselines. This population can have semantically equivalent contexts despite different premise networks; any collapse is a limitation to report, not noise to hide.

## Comparisons and inference

Compute frozen MMD² between each anchor theorem cloud and every gallery theorem cloud. The primary direction is backward-to-forward; secondary directions compare disjoint proofs within each generator. Record matching rank, tie-aware top-1 accuracy, pairwise ranking win rate, and the gap between matched and mismatched distances.

Use 9,999 permutations of **whole theorem labels** in the gallery for the mean matched-distance statistic. The proof/state blocks stay intact; never use iid point permutations. The null assumes theorem-label exchangeability within this bounded population. One BH family covers all encoder/view/direction tests actually reported; record skipped comparisons and family size. Ties are conservative.

Compare cloud ranking against centroid distance, a single sampled proof, and initial-state embeddings (the complete theorem statement/premises). These baselines share the same eligible theorems. Keep premise-network overlap and tactic/definition/domain controls descriptive because this is one tightly controlled logical fragment. Report raw distance matrices so null choices can be audited.

## Decision gates

The feasibility gate requires all of: >=12 eligible cross-generator theorems; primary cross-generator association at adjusted p<=0.05 for both full and goal-only text views; a pairwise-ranking improvement of at least 0.05 over the centroid baseline in the goal-only view; and no complete representation collapse. These are engineering/research-feasibility thresholds, not a global test of H1–H4. A successful generic text encoder does not count as replication with a second validated mathematical encoder.

If shared-premise controls or centroids account for the observed association, report the corresponding kill-criterion outcome for this population and **do not proceed to mining mathematical intersections**. The correct follow-up is a better corpus/encoder design, not interpreting chance overlaps. Cross-domain H3/H4 are untestable in this corpus by design. Keep this limitation explicit in the final research status.
