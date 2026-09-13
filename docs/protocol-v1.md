# Phase 0 protocol v1: held-out qualification

This protocol is committed before executing `configs/qualification-v1.json`. The smoke seed and pilot seed have been examined; qualification seed 608193427 has not. Candidate selection used only development data. No metric formula or threshold has been altered since the pilot.

## Calibration findings and scope restriction

The original pilot completed all 2,520 comparisons. At n=128, ring-versus-disk rejection was 1.00 in dimensions 2, 64, and 256 at per-coordinate noise 0.02. At noise 0.15, rejection fell to 0.57 in d=64 and 0.07 in d=256. Branch and mixture detection also deteriorated in the high-noise d=256 setting. The proposed pipeline is therefore **not qualified for arbitrary noisy embeddings**. These failures remain part of the result.

The held-out target regime is n=128 iid points, ambient dimensions {2,64,256}, and per-coordinate noise 0.02, for the already implemented two-dimensional latent shape families and a common isometric map. This restriction follows the observed calibration data and is explicit, not a claim of broad robustness. It does not establish a realistic operating regime for a learned proof encoder; the encoder will require a separate sensitivity and sample-size audit before confirmatory theorem experiments.

## Frozen measurement and inference

- Primary statistic: biased Gaussian MMD squared, as implemented in `src/noema/metrics.py`.
- Kernel width: square root of the median positive pairwise squared distance in the pooled samples; all-identical samples use width 1. The choice is independent of labels and held fixed in permutations.
- Null: exchangeable iid pooled labels, tested with 999 Monte Carlo permutations. P-value `(b+1)/(B+1)`, counting ties conservatively.
- Diagnostics: energy V-statistic, 128-direction sliced Wasserstein-1, radius coverage at half kernel width, and centroid distance. No diagnostic inherits primary significance.
- Multiplicity: one Benjamini–Hochberg family containing every primary comparison in this run. Raw rejection rates assess calibration/power; family-adjusted discoveries are reported separately.
- Sampling: three independent streams per trial for anchor, same-shape replicate, and comparison, with stable seeds and common latent-to-ambient coordinates. Equal sample sizes, no per-cloud centering, no resampling with replacement.
- Replication: 200 independent trials per scenario/stratum. All seven scenarios run; partial overlap is exploratory. No optional stopping and no removal of failed strata.
- Gates: the two null scenarios each require pointwise 95% Wilson upper rejection bound <= 0.10; each of the four alternative scenarios requires lower bound >= 0.80 in all three dimensions. Every target stratum must be present. A missing or failed stratum fails the protocol. The existing code reports a candidate pass, followed by a documented completeness/provenance review.

## Consequences

A pass freezes this measurement implementation for the bounded regime and allows a small formal-corpus feasibility study. It does not establish H1–H4 or justify iid point permutation tests on correlated proof states. A failure will be recorded and diagnosed before a separately versioned redesign. The broad high-noise regime remains failed regardless of this run's outcome.

For formal experiments, split/deduplicate at proof level, preserve state multiplicities, balance proof contributions, and use theorem/proof-level resampling and matched theorem nulls. Initial and terminal states are excluded from primary clouds. Corpus adequacy and encoder fidelity are independent gates.
