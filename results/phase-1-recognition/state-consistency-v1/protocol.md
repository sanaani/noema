# State consistency contract and independent extensions

Freeze this protocol before running the new suite. Preserve both earlier archives.
The acceptance requirement is identical encoder inputs/vectors for certified
equivalent ordered obligation States, with no collapsed tested distinctions.
This is a consistency contract, not validation of mathematical distance.

Implement typed expression serialization independently of Lean pretty printing.
Erase bound/local display names and metadata, retain de Bruijn references,
constants, types, universe levels, local-definition values, context boundaries,
and every pending goal in order. Reject unresolved expression/universe metavariables,
loose variables and resource failures. Preserve terminal records separately.
Use reducible WHNF recursively plus eta contraction as a limited normalization;
check original versus normalized fields by Lean definitional equality.

Extend beyond the old id wrapper: dependent binders, nested shadowing, local lets,
beta/zeta/iota/projection/eta, reducible aliases, ordinary definitions, explicit
instances, universe polymorphism, multiple pending goals, literal strings and
unused assumptions. Include deliberately distinct types, targets, values, goal
counts/orders and repeated contexts. Include expected unresolved-variable failures.
Keep universe parameters named in this version: changing their names is an explicit
out-of-contract case, not an unreported success. Declaration/goal reordering is
likewise not quotiented away. This defines ordered obligation States, not complete
Lean tactic execution snapshots or proof-search operational equivalence.

For the finite acquired inventory, compare every pair with Lean using the same
ordered context/goal shape and definitionally equal closed typed fields. Build a
frozen, deterministic representative registry; every member must have direct
evidence against its representative, and every certified pair must share a class.
Distinct raw syntax can map to one representative only with that evidence. Record
the environment, Lean version, source and policy hashes. Registry extension creates
a new version: never silently move old vectors. Unknown keys must fail, not fall
back to printed text. The full equality matrix exposes missed expected positives
and accidental equivalences among supposed negatives.

Run the structural baseline and at least LeanStateSearch on representative inputs,
checking token limits, token collisions and vector collisions across distinct
classes. Never truncate. Compute each occurrence's vector, retaining multiplicity;
repeat inference independently and compare all certified equivalent pairs. Test
the original 16 proofs through the same capture path. A finite-inventory contract
can be checked exhaustively; it is not a proof of universal canonicalization or
injectivity of a fixed-width real embedding. Persist any out-of-contract or failed
case with an explicit reason. Document precisely which guarantees are structural,
Lean-certified, finite numerical checks, or still unresolved.
