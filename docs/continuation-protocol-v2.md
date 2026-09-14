# Revised-plan continuation protocol

The user supplied `research-plan-v2.md` from Downloads after the first bounded
study. Preserve both source plans and all earlier outcomes. The 0.862 full-text
cross-generator win rate and stable sampling sensitivities are encouragement for
a controlled continuation, not evidence that the previous failed gate passed.
The new plan supersedes the earlier declaration that this implementation was
complete. No claim about the revised primary experiment follows from unmatched
v1 comparisons.

## Clustered power envelope

`configs/cluster-power-v1.json` fixes a new synthetic study before execution.
Sample independent proof centers from the existing Gaussian/ring/disk/mixture
families. A proof's states share its center and have independent latent jitter
of standard deviation 0.10 plus ambient Gaussian noise. Embed through a common
orthonormal map. This deliberate correlation model tests why m proofs cannot
be replaced by m*n iid states; it does not model all Lean state populations.

Sweep m={8,16,32,64}, n={2,4}, d={256,384}, ambient noise={0.02,0.15}.
Nulls are Gaussian/Gaussian and ring/ring. Alternatives are separated Gaussians,
ring/disk and Gaussian/mixture. For effect 0.5, half the comparison proof centers
come from the alternative and half from the anchor distribution; effect 1 uses
only the alternative. All draws are independent at proof level.

The inferential candidates are the existing Gaussian MMD squared and energy
V-statistic, with exactly their frozen formulas. Compute pairwise state kernels
and aggregate into proof-block means. Permute whole proof blocks (999 draws),
never individual states; use corrected conservative Monte Carlo p-values.
Each of 100 trials per stratum receives raw primary p-values and a single
study-wide BH correction for both candidates. Raw rejection rates estimate
power/calibration; report Wilson intervals separately. Sliced transport and
coverage remain descriptive diagnostics, and persistent homology is excluded
because no demonstrated gap justifies its added cost. They receive no power claim.

Report the minimal tested m*n regime separately per candidate, dimension, noise,
effect and structure. A provisional regime requires >=80% raw power, a power
Wilson lower bound >=0.80, and both null Wilson upper bounds <=0.10 at alpha .05.
A selected regime needs an independently seeded replication (seed 928195,
400 null trials and 200 alternative trials); failed calibration strata remain
visible. These are grid minima, not universal sample-complexity bounds.
Do not pool away correlation, increase trials selectively after seeing outcomes,
or silently drop weak alternatives. If none passes in a setting, label it
unqualified. Measurement power is necessary, not sufficient, for formal inference.

## Corpus pilot and matching

Use the existing verified corpus only as a disclosed development population.
Record total tactic length L, raw step i, and normalized depth i/(L-1) for every
retained state in external audit records. These must never reach an encoder.
An initial nongeometric pilot found median L=31 backward and L=13 forward;
19 of 24 theorems have no exact-length overlap in their current accepted proofs.
This rules out treating the previous unmatched run as the revised primary test.

Before more Lean verification, assess candidate yields from the two existing
search algorithms under a bounded enlarged search budget. No candidate is accepted
without Lean. Choose corpus budgets only after the independent power envelope.
Primary matching requires a common proof-length distribution across theorems and
provers, and the same normalized-depth bins. Exact lengths shared across all
included theorem/prover groups are preferred; never extrapolate outside common
support or create repeated proofs/states. At least 12 theorems must meet the
selected power envelope. Report excluded theorems and balance diagnostics.
Within-prover proof splits stay disjoint, and unmatched comparisons are secondary.
A lack of feasible common support is a failed revised corpus-adequacy gate.

The enlarged nongeometric pilot is fixed in `configs/corpus-pilot-v2.json`:
8,192 backward attempts and forward width 512 on all 24 development theorems.
Before geometric analysis, enumerate every 12-theorem subset and maximize the
common count summed over exact proof lengths; this permits a mixture of lengths,
not just one length. Equal optima choose lexicographic theorem order. This
optimistic capacity excludes shared proof identities and predicted forward
state-sequence duplicates, but still requires actual Lean acceptance and state
deduplication. Within-prover comparisons require twice the per-side count.
At each length choose the same n raw positions ceil(j*(L-1)/n), j=1,...,n;
missing required states make a proof ineligible. Neither length nor position is
an encoder feature. These selection rules use only nongeometric data.

The exact new corpus/splits/matching specification must be committed before its
geometric analysis. Tests permute complete theorem labels within the matched
population. Full individual state content is the primary representation; v1's
goal-only view is a disclosed degenerate diagnostic, not evidence that all
contextual representations fail. All previous baseline and replication failures
remain relevant. A new positive result must demonstrate added information beyond
centroids and statement/premise controls before confirmatory overlap discovery.

## Conditional downstream execution

If matched reproducibility and added-information gates pass, continue the full
revised plan using a held-out, adequately sampled mathematical population and
cross-training encoder replication. Freeze the complete unordered pair universe
from nongeometric eligibility rules before overlap scoring, test every eligible
pair, and correct the entire universe. Do not reinterpret a single-domain
feasibility population as cross-domain discovery. Graph fidelity is optional and
non-gating under the revised plan. A failed power or feasible-corpus gate closes
this continuation with the revised plan's explicit stop/redesign outcome.

## Subsequent disposition

The native-replay pilot failed its common-support gate. The separately frozen
[canonical-replay protocol](canonical-replay-protocol-v3.md) records the one
allowed redesign on a fresh theorem seed before geometric analysis. It preserves
the native failure, qualifies energy at 32 proofs × 4 states, and completes the
matched study. The [final result](revised-plan-results.md) reports reproducibility
without demonstrated added information; conditional discovery is closed.
