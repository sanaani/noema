# State-object investigation specification

The goal is to investigate whether states encountered across proofs of many
theorems form meaningful geometric objects, and whether their shape, extent,
intersection, separation and connectivity correspond to recognizable mathematical
relationships. This is exploratory investigation. Training an encoder or LLM,
predicting missing regions, and optimizing prediction accuracy are not current
objectives. Existing fixed encoders are measurement tools.

## Theorem selection and proof coverage

Sample theorems. For each selected theorem, include every known proof and every
intermediate proof state that can be extracted. Do not sample proofs within a
theorem or impose a fixed number of states. If acquisition must be staged, retain
the full inclusion target and mark the acquired object as incomplete.

Establish a documented theorem and proof inventory before choosing a new theorem
sample. Record sources, theorem identities and equivalent formulations, proof
identities, formalization status and missing material. Search for alternative
proofs rather than treating one library's default proof as all known proofs.
Completeness can be audited against an explicit source inventory; it cannot be
asserted for all mathematical literature without evidence. Record known missing
proofs explicitly rather than silently redefining "all known" as the subset that
was convenient to extract. A prose or diagrammatic proof may require formalization
before comparable formal states are available.

Do not use proof length, a shortest-proof restriction, or ease of encoding as an
unreported exclusion rule. Computational staging is not scientific subsampling.
The first corrected draw is 256 theorem identities across Mathlib and Lean
Workbook; its pinned source inventory and acquisition status are recorded in
[state-object-implementation-v1.md](state-object-implementation-v1.md).

## Candidate object algorithm

1. Preserve the full proof source and extraction provenance for every acquired
   proof. Capture all intermediate states at the documented extraction granularity,
   including local contexts and outstanding goals. Preserve initial and terminal
   records and any extraction failures explicitly. Tactic-level extraction does
   not expose every internal operation of an automated tactic; report that limit.
2. Preserve separate provenance-based identities for every recorded state. A hash
   of printed text identifies an encoder input, not a mathematical state. The
   [input-identity audit](state-input-identity-audit-v1.md) demonstrated this
   distinction in Lean4.9. Capture structured goal/context/environment information
   and distinguish local focused obligations from complete proof states before
   asserting semantic identity from a new acquisition.
   Encode each state with the same fixed encoder and serialization. Preserve the
   original state text and its theorem/proof associations. Cache repeated identical
   inputs without losing their occurrence records. Do not mix coordinate spaces
   from different encoders or silently substitute truncated states.
3. For theorem T, let Z_T contain every acquired state vector from all its acquired
   proofs. Define the candidate State object X_T = conv(Z_T), the convex hull.
   The hull includes its interior and boundary, not merely an ordered perimeter.
   No centroid, neighborhood radius, or proof-order edges define this object.
4. Represent the hull implicitly by its generating vectors. Exact duplicate
   vectors may share geometric storage because they do not change the hull;
   retain all provenance. Do not require enumerating every high-dimensional face.
5. Test two hulls for intersection by solving A alpha = B beta with nonnegative
   weights summing to one separately on each side. Save verified intersection
   witnesses or separating hyperplanes. Numerical ambiguity is unresolved, not
   a scientific overlap threshold. Inspect the formal states contributing to
   intersections and identify shared initial/terminal or other common states.
6. Record affine dimensions, geometric extent and between-object intersections.
   Distinguish contact from overlap of positive volume. A hull is connected and
   has no holes by construction; investigate connectivity across objects without
   claiming to discover these imposed within-object properties.
7. Use common projections for illustrations only. Keep original-space results
   alongside pictures. Label incomplete acquisition explicitly and retain all
   state vectors so other object definitions can later be investigated.

The convex hull is the current candidate to investigate, not an established best
definition. Normalized embeddings and sparse sampling impose important limits
on containment and rank; see the literature review. Do not change normalization,
project away dimensions, or omit inconvenient states solely to induce overlap.

## Existing work and remaining work

Read-only audit on September 14, 2026 of the archived confirmation plan found:

- 1,536 synthetic theorem entries.
- 21,243 theorem-specific programs in their stored proof banks, counted with
  theorem associations; this is not the number of globally unique templates.
- 6,144 selected proofs, four per theorem.
- Two retained encoded states per selected proof, eight per theorem.

These banks are from a restricted associativity family and enumerate shortest
programs at the configured distance. Expanding from four proofs to the stored
banks would still not establish coverage of every known proof, nor supply the
broad mathematical population sought for this investigation.

Archived proof extraction, verification, encoder adapters, vectors and recovery
infrastructure can be reused where compatible. The present corpus must not be
represented as meeting this specification. The next preparation is the theorem
and proof-source inventory, followed by theorem sampling and complete acquisition
against that inventory. The corrected implementation and first acquisition are complete, with explicit
proof and identity gaps; see the implementation record above. No model was trained.

References: [literature review](state-object-convex-hull-literature-review.md),
[durable recovery checkpoint](convex-hull-investigation-status.md).
