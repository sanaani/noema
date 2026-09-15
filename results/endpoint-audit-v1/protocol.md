# Endpoint audit protocol

Question: do distinct proofs of one theorem produce identical or consistently close
terminal embeddings, while different theorems remain distinguishable?

Written before computing the following distance summaries. All admitted theorem
records remain unchanged. No encoder is trained or replaced. No paid compute.

Primary target is the final step vector of the Dartmouth Delta representation
(ACL 2026, sections 4.5 and 4.7). This requires the released tokenizer, preprocessing,
vocabulary, weights and pooling configuration, or supplied endpoint vectors with
provenance. The current ReProver state encoder is not that representation. A
state-vector difference must not be presented as a Dartmouth Delta embedding.

Available-data controls:

1. Check every archived `no goals` vector, including equality across theorems.
   This tests the literal completion-display endpoint only.
2. Extract matched before/after pairs from each complete local tactic trace using
   trace ID and tactic index. Find the latest source end position among the original
   tactic nodes; among transitions ending there, select the latest start position
   with nonempty before and empty after. This avoids treating the outer `by` block
   as the final local tactic. Keep trace-level provenance and all extraction failures.
   An unresolved tie with different before-state texts is ineligible. The selected
   record is a source-position closing-step candidate, not a certified complete
   mathematical State; focused goals and nested tactics remain limitations.
3. Compare stored BEFORE-state embeddings of these candidates as an explicitly
   separate diagnostic. Keep environments separate. Distinguish exact source-body
   copies from different bodies; different bodies do not prove independent arguments.
4. Report all eligible within-theorem pairs from different source bodies and all
   between-theorem pairs in the same environment. Also report both distributions
   restricted to identical closing-tactic text. Report raw distances, exact equality,
   and quantiles, without selecting a favorable threshold for 'close'. Pair-weighted
   descriptive summaries are not independent-sample significance tests.
5. Save concrete min/max-distance within-theorem examples and their source proofs,
   including the theorem names the user has inspected. These selected examples
   illustrate measured extremes, not generalization evidence.

The true Dartmouth endpoint question remains unresolved if its model artifacts
cannot be obtained. Do not infer its result from the available-data controls.
