# Canonical replay redesign, before new geometric analysis

The revised-plan pilot reveals an instrumentation mismatch: a backward tree is
replayed as `constructor/apply/exact`, whereas a forward-discovered tree is
compressed into `have` declarations, reusing subtrees and assembling conjunctions
inside terms. Native tactic lengths therefore count different mathematical units.
The native-replay v2 pilot and all its failures remain reported separately.

This is a disclosed design change prompted by **nongeometric** length/yield
evidence and the known rendering code, not a claim that the original gate passed.
The original full-text results motivate further work but do not confirm this design.

Use a fresh 24-theorem population with seed 132671, fixed in
`configs/corpus-pilot-canonical-v3.json`. Preserve both existing discovery
algorithms and their resource bounds. Replay every discovered canonical proof
tree using the same existing `backward_script` renderer. This has a well-defined
state at each rule application; no padding, no-op tactics, repeated-state
oversampling, or changes to the proved proposition are introduced. Every selected
script must still pass the pinned Lean kernel and axiom checks.

The resulting experiment compares two discovery populations **under a shared
replay convention**. It does not claim to reproduce the native search-time
trajectory of forward saturation. Discovery algorithm and replay convention must
be separate manifest fields. The encoder still receives only individual state
content. Native replay results cannot be relabeled canonical replay results.

The fresh population is evaluation data: no geometric representation or score
may be computed before its corpus, length/depth matching, diversity rules and
analysis are frozen. The pilot may inspect only proof identities, rule trees,
lengths, candidate counts and verification yield.

Apply the same exhaustive common-length matching and fixed normalized-depth
positions as the v2 continuation protocol, with at least 12 eligible theorems.
Derive m and n from the independently replicated clustered power envelope.
Prefer MMD when it qualifies for both a location shift and at least one
equal-centroid structural alternative in 384 dimensions at noise .02; choose
the smallest tested m*n that qualifies for those alternatives, breaking ties
by smaller m. Energy is a fallback under the same rule. Report ring/disk,
weak-effect and high-noise failures without extending qualification to them.
Neither metric is qualified for arbitrary intrinsic dimensions or correlation.

Primary comparisons use full state content and the chosen metric, with syntax,
truth-table and frozen pretrained text encoders. Run cross-discovery and
disjoint within-discovery splits wherever the selected envelope is met, and
report coverage. Include unmatched secondary comparisons with equal cloud sizes.
Goal-only is diagnostic, not a primary gate. The primary family includes all
eligible matched encoder/direction tests and uses whole-theorem permutations
and BH correction. Retain paired theorem-bootstrap intervals and the existing
statement, premise, hypothesis, centroid, one-proof and trajectory baselines.

A positive primary text result requires q<=.05 and pairwise win rate >=.65.
Advancement to confirmatory intersections additionally requires cloud-minus-
centroid gain >=.05 with paired 95% lower bound >0, noncollapsed representations,
survival of syntax/premise controls and independent cross-training replication.
Preserve these thresholds before embeddings; do not adjust them to force success.
If acquisition cannot meet the qualified envelope, or these tests fail, report
the bounded negative/inconclusive result and close the conditional discovery
phase under the supplied plan's stopping criteria. This is the only replay
redesign in this continuation; no sequence of post-result representation searches.

## Acquisition freeze

The completed power grid and independent replication select **energy distance,
m=32, n=4**, under the stated fallback rule. MMD's promising structural power
does not override its failed first-stage null precision guard. The qualified
structural alternative is full-strength Gaussian versus symmetric mixture;
ring/disk is unqualified. Control encoders remain diagnostics of representation
sensitivity; this envelope is not a claim of sufficient power for every actual
state distribution.

The canonical pilot has capacity 134 proofs per generator on a common
12-theorem subset, or 63 proofs per side with disjoint within-prover splits.
Choose the subset maximizing the latter capacity; ties remain lexicographic.
Allocate 32 proofs per side by round-robin over available lengths, respecting
each length's capacity. Within each length use proof-hash order, with the first
quota assigned to side A and the next quota to side B. All theorem/prover/side
groups have exactly the same length allocation and four raw-depth positions.

The unmatched secondary sample is the first 32 distinct proof identities per
generator in hash order from the unrestricted candidate bank, on the same
selected 12 theorems. It uses the same four relative-depth positions without
length matching. Verify the union of matched and unmatched selections: **1,864
scripts**, with every exact identity frozen in
`results/canonical-v3/acquisition-plan.json.gz`. The theorem seed is fresh; this
is still a restricted Horn population, not a cross-domain mathematical library.

After Lean validation, freeze every actual retained state and sample. Reject
shared proof identities, duplicate normalized state sequences, mismatched depth
histograms or missing required state positions before any embedding. No failed
verification is counted as an accepted proof. Per-batch checkpoints allow recovery.
