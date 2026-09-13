# Corpus feasibility protocol v1

Commit this design before collecting proof embeddings. This study establishes corpus and inference feasibility in a bounded fragment; it cannot test cross-domain mathematical discovery.

## Population and generators

Use generated propositional Horn entailments with eight proposition atoms, two initial facts, forward implications (including conjunctive antecedents), and a conjunctive conclusion. Different acyclic premise networks define different theorem statements. All accepted scripts must be checked by a pinned Lean compiler and extracted from its actual tactic information.

Implement two independent search algorithms over the same rules: goal-directed recursive backward chaining and breadth-first forward saturation. Their outputs are ordinary Lean proof scripts, with explicitly represented intermediate goals/facts. These are substantially different search strategies within a small shared logic, not two large general-purpose learned provers. Report that limitation and do not extrapolate across mathematical domains.

Theorems and search seeds are deterministic. The collection fixes 24 premise networks, seed 91827, and up to 64 proofs from each generator. The final goal is `(p4 ∧ p5) ∧ (p6 ∧ p7)` so both searches must establish four distinct consequences. This supplies at least four forward intermediate fact states without inserting artificial padding. Include all attempted theorem IDs and report failures, budgets, proof counts, and state counts. Model inputs contain formal states only. Initial theorem-goal states and empty terminal states are excluded; any later state text exactly duplicating the initial state is also excluded.

## Diversity and splitting (fixed before geometry)

Canonical proof trees use premise identifiers, implication application, and conjunction introduction. Expand forward references into the same tree representation used by backward search. Hash that tree as the primary proof identity; this removes renaming, formatting, temporary-fact names, and differences in execution order. The proof tree is external to the learned geometry. Deduplicate across both generators, retaining the list of discovering generators in the audit record. Identical normalized state sequences are an additional duplicate criterion.

For cross-generator comparisons, shared proof identities must never occur on both sides. Shared identities are removed from the primary cross-generator analysis; retain them for explicit sensitivity analyses only. Within-generator splits group by canonical proof identity. Do not count shuffled tactic orders as independent proofs.

Primary proof clouds preserve the empirical state distribution after normalization, with a fixed per-proof sample budget. A theorem is eligible only if both sides supply the prespecified number of distinct proof identities and states without replacement. Insufficient data is an explicit failed corpus-adequacy gate, not permission to repeat states or lower a threshold after inspecting geometry.

## Verification evidence

Pin Lean 4.33.1 and REPL commit `bbeedf38e0898869fc3b7c009e1ea877b46204e4` (v4.33.0 source, built with the pinned compiler). Save full accepted proof scripts, actual extracted goals, constants used, verifier responses, and content hashes. Check every accepted declaration for errors, `sorry`/admit, and its transitive axiom set. This constructive propositional fragment requires no axioms. Search scaffolding is never accepted as a proof. Each proof is verified in a fresh environment containing only imports, so one sampled proof cannot call another.

## Next scientific decisions

Before representation evaluation, commit the exact eligible corpus, split assignments, state normalization, encoder manifests, matched controls, baselines, sample budget, and proof/theorem-level inference procedure. A corpus feasibility failure calls for better search/theorem selection before any H1 claim. A successful toy corpus is still only a feasibility population.
