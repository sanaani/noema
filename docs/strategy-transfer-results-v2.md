# Structurally matched strategy transfer: completed result

**Subsequent user instruction:** the user rejected the 10-percentage-point
requirement as arbitrary and directed continuation after these results. The
original gate outcome below is retained as history; it no longer determines
whether work continues. A separately preregistered confirmation will test for
positive added information and estimate its size without that minimum margin.

**The harder task passes headroom and power, but fails the registered cloud
added-information stability gate: 0 of 100 draws qualify, versus 80 required.**
The initial ReProver cloud score is 65.6%, compared with its centroid at 60.9%.
Across proof resampling, its average advantage over that centroid is only
1.19 percentage points. This closes the operational candidate before confirmation.

The user authorized continuing after v1's task and budget failures. This fresh
experiment directly addresses both: source and target statement similarity are
matched separately, and the planned confirmation budget is determined by a
larger power grid. The v1 candidate remains closed and its clouds remain unscored.

The [protocol](strategy-transfer-protocol-v2.md) is a local Git preregistration,
committed before embeddings. The [assignment freeze](../results/strategy-transfer-v2/assignment-freeze.json)
retains the exact population, sampling choices and source hashes. This experiment
uses eight leaves for development and reserves nine leaves for conditional
confirmation; no seven-leaf or Horn pair is reused.

## What changed

Positive strategy-transfer pairs and zero-transfer negatives now have exactly
equal source-clade intersections and exactly equal target-clade intersections
with the anchor. Consequently each component of structural Jaccard distance
ties, as do premise overlap and token-bag distance. The matching is symbolic;
learned geometry does not select candidates. The frozen 64-triplet
population has 32 triplets in each used-premise-overlap stratum, 0 and 1.

The frozen population has 192 distinct theorem endpoint pairs and 1,640 distinct
shortest programs. No program is reused across triplets. Positive sharing within
a triplet is intentional and defines transfer; the negative shares no program
with either positive member. This prevents direct program reuse across sampling
units, while leaving the broader limits of a small synthetic family explicit.

The matching has a simple exact justification. An ordered full binary tree with
n distinct leaves has n−2 proper nontrivial clades. If two such clade sets share
k elements, their Jaccard distance is `1 − k / (2(n−2) − k)`. Matching k separately
at the source and target therefore fixes both distances exactly; it does not
depend on a fitted statistical adjustment.

The transfer oracle is also exact within its stated language. Both endpoint
pairs have shortest distance five, and each complete program bank contains all
five-step shortest programs. A program from A succeeds on B if and only if it
belongs to B's bank. Thus the directed transfer rate is `|P_A ∩ P_B| / |P_A|`.
The archive verifier additionally performs literal replay in both directions,
rather than trusting set-intersection labels alone.

Each cloud still samples four distinct proofs and intermediate positions 1 and
3 of five rotations. The new screen has 1,099 unique statement/state inputs,
all exactly 266 ByT5 tokens. The fixed 24-proof Lean fixture passes, with 120
intermediate states matching the symbolic renderer. No encoder, distance,
sampling budget, effect threshold or headroom cutoff was changed after scores.

## Power qualification

The planning alternative remains cloud accuracy .80 versus .65 for each of nine
controls, with paired discordance .35. The joint rule still requires a gain of
at least .10 and exact one-sided McNemar p≤.05 against every control. Simulated
controls are conditionally independent given the cloud outcome. These are
planning assumptions, not a fitted estimate of the actual cloud effect; they
are conservative for the three controls that tie by design.

| Independent triplets | Detection rate | Wilson 95% interval | All-null rejection | One-equal-control null rejection |
|---|---:|---:|---:|---:|
| 256 | .6134 | [.6038, .6229] | .0000 | .0027 |
| 512 | .8397 | [.8324, .8468] | .0000 | .0000 |
| 1,024 | .9803 | [.9774, .9828] | .0000 | .0000 |

**512 triplets qualifies**, because its lower power bound exceeds .80 and both
null upper bounds are below .10. The composite-null check retains one equally
accurate .65 control and makes the other eight independent fair predictors.
Each row/condition has 10,000 trials: 90,000 simulated experiments and 810,000
paired comparisons overall. All individual gains/p-values are archived.

The 64-triplet headroom screen permits at most 52 correct for an upper bound
below .90. An individual control passes with probability .9986 at true accuracy
.65, .9065 at .75, .6477 at .80, and .0236 at .90. Passing all controls depends
on their joint behavior; neither these calculations nor qualification establishes
a real cloud effect.

## Measured headroom and conditional outcome

**Headroom passes for all nine controls.** Both upstream gates therefore opened
the conditional geometry test, which has now completed.

| Control | Correct / 64 | Accuracy | Upper 95% | Overlap 0 | Overlap 1 |
|---|---:|---:|---:|---:|---:|
| token bag | 34 | 0.5312 | 0.6388 | 0.6250 | 0.4375 |
| used premise | 34 | 0.5312 | 0.6388 | 0.6250 | 0.4375 |
| statement structure | 34 | 0.5312 | 0.6388 | 0.6250 | 0.4375 |
| syntax statement | 31 | 0.4844 | 0.5938 | 0.6250 | 0.3438 |
| syntax centroid | 30 | 0.4688 | 0.5786 | 0.5000 | 0.4375 |
| minilm statement | 34 | 0.5312 | 0.6388 | 0.4375 | 0.6250 |
| minilm centroid | 30 | 0.4688 | 0.5786 | 0.4062 | 0.5312 |
| reprover statement | 38 | 0.5938 | 0.6975 | 0.5938 | 0.5938 |
| reprover centroid | 39 | 0.6094 | 0.7119 | 0.6562 | 0.5625 |

The three symbolic controls tie in every triplet; their half-credit accuracy
is .5000. Their .5313 binary score comes solely from the frozen fair tie bits.
The strongest measured control is the ReProver centroid at 39/64=.6094, with
upper bound .7119. All baseline bounds are below the unchanged .90 threshold.

![Headroom on exactly matched source and target structure](../results/strategy-transfer-v2/figures/headroom.png)

## Cloud added information and proof resampling

All 342 additional state embeddings completed, yielding 1,441 unique inputs per
encoder. The original 1,099 cached vectors are preserved exactly. The energy
comparison uses eight state points per theorem: four distinct proofs, each
contributing positions 1 and 3. All three encoders use the same sampled proofs.

| Encoder | Frozen energy accuracy | Statement accuracy | Centroid accuracy | Resampled energy mean | Resampled energy range |
|---|---:|---:|---:|---:|---:|
| syntax | 0.4219 | 0.4844 | 0.4688 | 0.4194 | [0.3281, 0.4844] |
| minilm | 0.4844 | 0.5312 | 0.4688 | 0.5372 | [0.4531, 0.6250] |
| reprover | 0.6562 | 0.5938 | 0.6094 | 0.6386 | [0.5938, 0.7344] |

On the initial frozen sample, ReProver energy is correct on 42/64 triplets,
versus 38/64 for its statement and 39/64 for its centroid. The gains are 6.25
and 4.69 percentage points respectively, below the registered 10-point target.
The ReProver energy scores in premise-overlap strata 0 and 1 are .7188 and .5938.
These are descriptive results from development, not independent significance tests.

Each of the 100 registered draws resamples four distinct proofs from every
frozen theorem and recomputes all centroids on that same sample. The table
below reports ReProver energy minus each control; ranges describe these fixed
draws and are not confidence intervals.

| Control | Mean gain | Gain range | Draws with gain ≥ .10 |
|---|---:|---:|---:|
| token bag | 0.1073 | [0.0625, 0.2031] | 54/100 |
| used premise | 0.1073 | [0.0625, 0.2031] | 54/100 |
| statement structure | 0.1073 | [0.0625, 0.2031] | 54/100 |
| syntax statement | 0.1542 | [0.1094, 0.2500] | 100/100 |
| syntax centroid | 0.1717 | [0.0938, 0.2656] | 99/100 |
| minilm statement | 0.1073 | [0.0625, 0.2031] | 54/100 |
| minilm centroid | 0.1089 | [0.0156, 0.2656] | 56/100 |
| reprover statement | 0.0448 | [0.0000, 0.1406] | 1/100 |
| reprover centroid | 0.0119 | [-0.0312, 0.0781] | 0/100 |

**Zero draws beat all nine controls by at least .10; at least 80 were required.**
The ReProver centroid alone prevents qualification in every draw: the cloud
advantage ranges from −3.13 to +7.81 percentage points and averages +1.19.
The centroid is recomputed each time, so this comparison does not give clouds
new proof samples while leaving their main control fixed.

![Minimum cloud gain over the nine controls across proof samples](../results/strategy-transfer-v2/figures/stability.png)

This result provides a direct conditional test of added information after
establishing headroom. It is evidence against a stable 10-point advantage for
unordered energy with this encoder and four-proof/two-state budget on this
population. It does not establish that the true effect is zero, exclude smaller
gains, or refute proof-state geometry across mathematics. The slight initial
advantage does not satisfy the continuation rule.

The registered stopping rule therefore closes this candidate. The power-qualified
512-triplet nine-leaf confirmation is not acquired, and no metric substitution,
replacement-pair search, Phase 5, or full mathlib acquisition follows. The earlier
v1 clouds remain unscored. Any further redesign would be a separately disclosed
experiment, not a continuation selected from these outcomes.


## Reproduction and scope

All analyses consume state content without theorem IDs, proof-program addresses,
transfer labels or sequence metadata. The classifiers are the prespecified
nearest-candidate rules, with no task training. ReProver is the same pinned
Lean-trained retriever used in v1; syntax and MiniLM are representation controls.
The [reproduction guide](reproduction-strategy-transfer-v2.md) documents dependencies,
source/encoder hashes, restart-safe vector checkpoints and archive-only checks.

The independent symbolic replay audit and Lean fixture check operational
correctness. They do not turn the small synthetic family into a representative
sample of mathematics. Triplets have no direct program reuse, but hidden shared
structural features can still induce dependence. Any resampling stability
result is conditional on this fixed development population, not a replication.
Phase 5 and full mathlib acquisition are outside this continuation.

An ancillary portability check found that a different BLAS CPU kernel shifts
old archived distances by at most 1.11e-16 without changing any predictions or
decisions. Archive verification now reports float drift with tight 1e-12
absolute/relative bounds; discrete outcomes remain exact. This changes neither
the experiment's tie threshold nor its decision rules.

All 93 local tests pass. The archive verifier reconstructs the assignments,
3,204 explicit transfer replays, 120 recorded Lean states, nine headroom scores,
all 100 proof-resampling comparisons, and both gate decisions. Source hashes,
encoder manifests, raw scores, vectors and SHA256 checksums accompany the result.
