# Preregistered strategy-transfer headroom and added-information test

Frozen before any candidate-task embeddings or performance measurements.
This follows the user's task-design correction. It is not Phase 5 and does not
select pairs from either Horn corpus. Structural feasibility alone was examined:
six leaves yield no eligible positive pairs; seven leaves yield 1,632 eligible
endpoint pairs, 504 with positive partners; eight leaves yield 23,148 endpoint
pairs, 10,164 with positive partners. No geometry informed these counts.

## Population and independent relationship

Use ordered full binary trees with seven leaves for development, eight for a
held-out confirmation. An endpoint pair denotes an equation between two
parenthesizations under an abstract associative operation. Require shortest
rotation distance exactly five and at least eight distinct shortest programs.
Enumerate all shortest programs exactly. A step is a subtree address and rotation
direction; a strategy transfers when replaying all five steps is applicable and
reaches the other theorem's endpoint. Positive pairs have at least 75% successful
transfer in BOTH directions; negative pairs have zero. Exclude self-pairs and
intermediate cases. This operational relation is narrower than general deep
mathematical relatedness. Its labels come from symbolic replay, never embeddings.

Every triplet has an anchor, a positive and a negative. No endpoint pair recurs
within a split. All three have identical available premises: two abstract
operations f/g and both associativity laws. Randomly choose the anchor's operation.
Half the triplets use that operation for both candidates; half use the other.
Thus used-premise Jaccard is exactly 1 or exactly 0 for BOTH candidate comparisons,
and available-premise overlap is always 1. Both relationship labels occur in both
overlap strata. Transfer permits uniform operation/variable substitution.
Independently permute the common variable names in each theorem. Leaf count,
vocabulary, token bag and proof length are matched within each triplet. Structural
statement features may still predict transfer; the headroom gate tests that risk.

Select triplets by seeded random order, using only the symbolic eligibility rule
and excluding used endpoint pairs. Development seed 914202601, held-out seed
914202602; 32 development triplets. Confirmation uses a different leaf count and
the first qualified sample size below. Archive assignments before encoding.

## Representations and cheap gate

Three fixed encoders: existing signed syntax n-grams; pinned general-text MiniLM;
and the Lean-trained ReProver ByT5 retriever. Use its author's CTranslate2 export,
revision 8612469b496b72bdb2f0d6ccd5316c100200581e, CPU int8_float32, 1,472 dimensions.
Use UTF-8 byte IDs +3, EOS 1, masked mean including EOS, L2 normalization. Reject
empty inputs, special-token spellings and inputs exceeding 1,024 tokens; do not
truncate. Hash the weights/config/vocabulary and record software and preprocessing.
The export is an operational quantized arm, not a claim of exact original-weight
numerical equivalence. See the primary [ReProver implementation](https://github.com/lean-dojo/ReProver/blob/main/retrieval/model.py)
and [model table](https://github.com/lean-dojo/ReProver#retrieval).

Use four distinct shortest proofs selected uniformly without replacement, and
two intermediate positions (1 and 3 of five rotations) from each: eight points
per theorem. Initial and terminal goals are excluded from clouds. This is a
small task-specific sampling budget, NOT imported qualification at m=32,n=4
from the old Gaussian study. Headroom uses symbolic state renderings; verify a
small fixed fixture in Lean before encoding. A passing headroom gate additionally
requires a sampling-power check before confirmation acquisition (below).

Baselines, all fixed: full initial statement embedding in each encoder; cloud
centroid in each encoder; token-multiset Jaccard; used-premise Jaccard; and an
alpha-invariant structural statement baseline. The latter averages source and
target tree-clade Jaccard distances, where clades are proper nontrivial contiguous
leaf spans. This deliberately strong cheap structural control can close the gate.
Closer candidate wins. Use absolute tolerance 1e-10; resolve ties by one seeded
fair bit per triplet shared across methods, also report tie-adjusted accuracy.

Before any cloud-distance scoring, evaluate all nine baselines on development.
Headroom passes only if EVERY baseline has one-sided exact 95% binomial upper
confidence limit below 0.90. Report both premise-overlap strata, all scores and
all failures. If any fails, stop this candidate as a task-design/headroom failure;
do not acquire confirmation, score cloud distances, mine replacement pairs, or
interpret it as a cloud-hypothesis failure. No full mathlib acquisition.

## Power and conditional confirmation

Before the headroom result, simulate 10,000 trials at N=64,128,256 independent
triplets. The prespecified meaningful alternative has cloud accuracy .80 and
each of nine baselines .65; paired cloud-only success .25, baseline-only .10.
Baseline outcomes are conditionally independent given the common cloud outcome.
The primary inference is an intersection-union test: require a gain >=.10 AND
one-sided exact McNemar p<=.05 against every baseline. This tests one primary
claim (Lean-trained energy beats all controls); no selection of the easiest
baseline. Repeat the null with equal .65 accuracies and discordance .35. Select
the smallest N whose power Wilson lower 95% bound exceeds .80 and null upper
bound is below .10. Publish simulation assumptions and sensitivity; power under
this model is not a promise about real cloud effects.

If headroom passes, additionally check the actual m=4,n=2 budget's stability on
the development task: 100 independently seeded proof samples, without changing
triplets or representations. The primary energy metric must beat every baseline
by .10 in at least 80% of these conditional resamples. This is an empirical
feasibility check, not an independent significance test or a universal geometry
power envelope. A failure closes this small sampling budget without interpreting
the hypothesis. Do not increase m/n or choose another metric after observing it.

Only if all gates pass, freeze the held-out assignments, verify all selected
proofs in Lean, audit actual states against symbolic renderings, and encode.
Primary unordered-cloud distance is the existing energy V-statistic. ReProver
energy must meet the joint criterion above on held-out triplets. MiniLM/syntax
energy and overlap-stratum results are descriptive secondary outcomes. Report
all paired outcomes, exact p-values, and 10,000 triplet-bootstrap gain intervals.
Proofs/states are not independent trials. Archive source, assignments, states,
vectors, oracle checks and reproducible scoring. Any positive conclusion is
restricted to this synthetic strategy-transfer relation and sampling budget.
Phase 5 and full mathlib acquisition remain outside this continuation.
