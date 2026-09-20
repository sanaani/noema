# Several fixed encoders: invariance and distinction controls

Specified before running the new encoders or inspecting their vectors. Reuse the
eight-theorem, 16-proof, 44-nonempty-occurrence Lean fixture inventory from the
failed ReProver screen. Preserve its original five presentations, their order,
all pending goals, centers and repeated occurrences. Reverify the fixture in
Lean. Do not alter the archived ReProver experiment.

Test the existing quantized MiniLM adapter, LeanStateSearch2025.3 (mean pooling),
Qwen3-Embedding-0.6B (last-token pooling, no task instruction), e5-small-v2 (mean
pooling, `query: ` for all symmetric inputs) and bge-small-en-v1.5 (CLS pooling,
no retrieval instruction). Add Qwen's symmetric fixed instruction as a separately
reported arm: `Represent this Lean proof state for mathematical similarity.`
No prompt tuning or choosing the best prompt after seeing results. Pin downloaded
revisions and hash weights/tokenizers; use CPU float32 and singleton batches,
evaluation mode, no truncation. If resources prevent a run, report the failure.
Retain token IDs, unknown-token counts and identical-token collisions: apparent
invariance must not conceal loss of mathematical distinctions. Run models serially.

Run each model on raw displays and on independently computed Lean canonical
displays. The latter is a representation intervention, not evidence that the
model itself learned an invariant representation. Fix local and bound names,
printer settings and width; recursively erase metadata and reduce beta, zeta and
the explicit `id` application. Preserve constants, universes, ordered local
context and the boundary between context and target. Verify every normalized
obligation definitionally equal in Lean. This is a limited policy, not a general
defeq decision procedure or a claim of complete structured-state capture.
Retain a structural signature (normalized closed expression plus local-context
length) per pending goal and use signed token n-grams of this signature as a
structural control. Also use the original syntax encoder and a constant-vector
negative control. No learned weights, theorem names, proof IDs or labels enter
any encoder input.

Add 12 explicit contrasting pairs with matching contexts: conjunction/disjunction,
implication direction, negation, dropping a conjunct/disjunct, implication versus
conjunction, iff versus or, De Morgan distinction, equalities to different natural
numbers, strict versus nonstrict order, empty versus nonempty lists, and a valid
addition identity versus an invalid one. Certify non-defeq in Lean and a concrete
truth-value disagreement under an explicit valuation for every pair. Generate
the same five presentation arms for each side. These pairs are distinctions to
retain, not a complete mathematical-relatedness ground truth. Test whether an
equivalent presentation stays closer than its paired changed proposition, for
both anchors, without selecting examples after embedding. Report all ties and
collapses. A constant encoder must fail these distinction controls.

For every model and representation, re-encode originals to measure numerical
drift. Reuse exact F_T sup distance, radial W1, paired radius drift, center-distance
changes and tie-aware rankings from the frozen screen. Numerical invariance uses
max(1e-6, 10 times duplicate drift). Also report W1 relative to the original mean
radius and displacement relative to contrast distances; raw distance scales
alone cannot rank models. Test F_T change with W1, separately from changes in
paired radial positions. Point invariance alone is not necessary for an isometry
to preserve internal geometry. No practical semantic qualification threshold is
invented after the results. A finite screen pass with retained distinctions
supports further measurement testing, not mathematical case studies yet.

Retain all physical vector rows, input associations, formal evidence, numerical
outputs, execution receipts and failures. Canonicalized equality is by construction;
never present it as an independently discovered semantic ability. All new model
results and controls are descriptive, with no population estimates or p-values.
