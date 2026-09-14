# Prospective supplemental baseline audit

This supplement completes baseline comparisons named in Phase 4 of the original
research plan. It is committed during Lean acquisition, before any nine-leaf
embeddings or prediction scores. It does not revise the amended primary claim:
the nine registered controls, exact paired tests, fixed 512-triplet sample and
absence of a minimum gain requirement remain as preregistered.

Report these additional comparisons descriptively on the same frozen triplets:

1. **Single-proof mean, for each encoder.** Use the first of the four uniformly
   sampled proofs already frozen in each theorem record. Average its two state
   vectors at positions 1 and 3 and apply nearest-candidate Euclidean distance.
2. **Position-specific means, for each encoder.** Reshape the existing eight
   vectors as four proofs by two positions. Average across proofs at each
   position, concatenate those two means, divide by sqrt(2), and apply Euclidean
   distance. This retains positional alignment without additional embeddings.
   It is a partial trajectory summary, not an encoding of all five proof steps.
3. **Sampled complete program trajectories.** Compare the sets of four complete
   sampled address/direction programs using Jaccard distance. These are exactly
   the sampled proof trajectories verified in Lean. This comparator has access
   to all five steps and their order; the cloud uses only two intermediate
   states per proof. It is a structural proof-evidence control, not a statement
   baseline or an information-matched claim of cloud inferiority.
4. **Tactic-component histogram.** Across the four generated proof scripts,
   count the fixed components `refine`, `Eq.trans`, `Eq.symm`, `congrArg`, `hf`,
   `hg`, `rfl`. Extract only the proof body (between `:= by` and `#print axioms`),
   normalize the seven counts to unit Euclidean norm, then compare by Euclidean
   distance. This excludes binders, theorem text and parameter declarations.

All comparisons use the existing fixed tie bits and 1e-10 tie tolerance. Report
accuracy, tie-adjusted accuracy, overlap strata, and ReProver energy minus each
control. Use 10,000 paired triplet-bootstrap marginal 95% intervals with the
primary bootstrap seed 914202617 and its same sampling algorithm. Do not make
new significance claims or choose a replacement primary comparator from these
results. Interpret the main nine-control result together with this fuller audit.

Domain labels are constant (associativity), available definitions/premises are
identical, and used-premise overlap is exactly matched within each triplet.
Those controls therefore reduce to already registered ties. None of these
supplemental analyses mines the closed seven-leaf population or the Horn corpus.
