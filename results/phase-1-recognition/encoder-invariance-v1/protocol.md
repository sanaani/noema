# Encoder invariance falsification screen, v1

Written before generating or inspecting this screen's vectors. The immediate
question is whether the fixed ReProver measurement survives semantics-preserving
presentation changes, before further corpus acquisition or connection case studies.

Use eight small Lean-core theorem fixtures (conjunction swap/association,
implication composition, disjunction swap, equality symmetry/transitivity,
natural-number addition associativity, and list append associativity), with two
explicit proofs each. These are an engineering falsification suite, not a random
sample or qualification of the admitted corpus. Retain every instrumented
nonempty State occurrence and all pending goals at each checkpoint. Instrument
each explicit proof step, including introductions and branch changes; automation
internals are not captured. The initial State is the center and is also retained
as an observed occurrence. Archive terminal empty checkpoints but exclude them
from density, as required by the current object definition.

Transform each structured checkpoint independently into: original, alpha-renamed
local and bound variables, narrow pretty printing, notation-disabled printing,
and a transparent `id` wrapper around each goal's proposition. Lean must check
the original and transformed closed obligations definitionally equal, with no
unresolved metavariables, and verify every proof and its axiom closure. Pretty
printing is performed directly on the checked expressions and contexts; this
does not assert arbitrary printed text is an injective serialization. Preserve
goal order and local declarations. No regex renaming or string-only equivalence
certification. Include a deliberately non-defeq negative check to exercise the
verifier. Fail closed on verification, input length, missing rows or nonfinite
vectors. Do not truncate or discard failures.

Use the existing checksummed CPU ReProver adapter, singleton quantization and
full UTF-8 byte inputs. Re-encode every arm in this run; do not mix existing
archive vectors. Retain one vector row per occurrence and arm, including repeats.
Re-encode originals to measure numerical repeatability. No model training or
serialization repair is selected using these outcomes.

Measure Euclidean paired displacement, center displacement, radial distances
and empirical F_T with multiplicities retained. Transform both center and states
together (primary), and report center-only/state-only perturbations as diagnostics.
For F_T report exact sup CDF difference, Wasserstein-1 (mean sorted-radius
difference), and maximum paired radius drift. Also report center-distance
matrix changes and nearest-center order changes with explicit tie handling.
Other fixtures are comparison objects, not certified semantically unrelated
negative examples. Report lexical/syntax sensitivity only as a control, not as
ground truth mathematical distance.

Exact invariance is falsified by changes exceeding the larger of 1e-6 and ten
times the measured duplicate-encoding drift. This is a numerical identity
tolerance, not a semantic acceptability threshold. CDF jumps can exaggerate
arbitrarily small shifts, so always report radius-scale drift as well. Passing
this finite screen is necessary evidence only: it cannot validate mathematical
relatedness. A failure blocks interpreting the current distances, curves or
rankings as mathematical relatedness; retain all failures and investigate a
separately specified representation repair before any new usefulness study.
