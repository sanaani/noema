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
