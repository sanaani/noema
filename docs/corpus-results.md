# Verified corpus results

The recovered collection completed all 24 predetermined Horn entailments and
verified **3,072 proofs**, 1,536 from each generator. Every selected script passed
Lean 4.33.1 with an empty transitive axiom set; there were no failed verifications,
`sorry` admissions, or proofs with fewer than four retained states.

The original interruption left no complete theorem checkpoint. The recovered
run used eight-proof verifier processes branching independently from an
import-only environment. Collection provenance records clean revision `baff1fb`.
The full corpus and exact sampling assignments were committed at `6211c0a`
before the first corpus embedding was computed.

| Census | Backward search | Forward saturation |
|---|---:|---:|
| Lean-verified scripts | 1,536 | 1,536 |
| Retained intermediate state occurrences, before proof deduplication | 47,479 | 18,843 |
| Eligible distinct proofs after normalized sequence deduplication | 1,536 | 1,428 |
| Eligible proofs per theorem | 64 | 39–64 |

The corpus contains **66,322 intermediate state occurrences** in total. These are
observations of focused formal goal states before recorded tactics; they are
neither unique states nor all possible states of a theorem. Initial states,
empty terminal states, and later full states exactly matching the initial state
are excluded. The full goal-only view intentionally reveals whether a prover
keeps a fixed goal while adding derived facts.

Search uses deterministic seed 91827: backward search makes 512 attempts per
theorem; forward search has width 128 over at most eight saturation rounds.
Generator seeds are `91827 + theorem_index` and `191827 + theorem_index`.
Shared canonical proof identities are excluded before verification selection;
the first 64 remaining identities in hash order are checked per generator.
These are substantially different search strategies in a common small fragment,
not independent large learned prover products. Lean's pinned standard library
is sufficient; no Mathlib revision is involved.

There are 108 duplicate normalized state sequences, all in the forward group.
They are retained in the evidence archive but excluded from analysis. Proof
identity is interpreted within its theorem: local premise names refer to
potentially different formulas in different declarations. Content-only encoders
remove case labels, binder names, and declaration order while retaining formal
formulas and multiplicities.

| Preregistered selection | Eligible theorems | Disposition |
|---|---:|---|
| Cross-generator, 32 proofs per side | 24 | Analyze |
| Within-backward, two disjoint sets of 32 proofs | 24 | Analyze |
| Within-forward, two disjoint sets of 32 proofs | 1 | Below the 12-theorem gate; skip |
| Cross-generator, stricter used-premise-set deduplication | 24 | Descriptive sensitivity |
| Cross-generator, stricter tactic-histogram deduplication | 0 | Below coverage gate; skip |

Every analyzed cloud has 32 distinct proofs and four sampled state occurrences
per proof, without replacement. Identical formal content at different occurrences
remains part of the empirical distribution. Splits precede sampling and embedding.
The two additional sampling seeds keep the same budgets and eligibility.

The [machine-readable audit](../results/corpus-v1/audit.json) checks deterministic
theorem generation, regenerated proof source and tree hashes, verifier evidence,
state extraction, sequence deduplication, disjoint splits and balanced sampling.
The [checksummed archive](../results/corpus-v1/SHA256SUMS) contains all proof sources,
Lean responses, external proof trees/tactics, raw states and the exact split freeze.
See [reproduction instructions](reproduction.md) for extraction and rerunning the audit.
