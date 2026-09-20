# Demonstrating usefulness of Theorem Density Objects

September 16, 2026. Research proposal, not a report of new measurements.

**Priority correction, later September 16:** the user requires encoder invariance
to be addressed first. The [Lean-certified presentation audit](../results/encoder-invariance-v1/README.md)
is the immediate work. The case studies proposed below are conditional on a
defensible measurement: α-renaming, pretty-printing and definitionally equal
restatements must not manufacture the signal attributed to mathematics. Neither
corpus expansion nor a selected connection example repairs a failed encoder.
The [alternative-encoder comparison](../results/encoder-comparison-v1/README.md)
separates raw model behavior from Lean-derived canonicalization and tests for
lost proposition distinctions. Passing these finite controls does not establish
the mathematical usefulness proposed below.
The [subsequent implementation](../results/state-consistency-v1/README.md) enforces
identical encoding for certified equivalent States in a frozen inventory, using
typed capture and rejecting unknown States. This resolves the accepted-input
consistency contract within its declared scope; useful mathematical distance
still needs independent evidence.

## Handoff: recommended path to value for the math community

Read this document first for the current direction, then the
[current specification](current-state-object-spec.md) for collection and admission
rules, and the [historical pilot](../results/historical-connections-v1/README.md)
for completed evidence. Earlier boundary and synthetic prediction studies are
historical; do not silently restart them as the current objective.

After the measurement gate is resolved, a possible contribution is an inspectable collection of mathematical
case studies: theorem statements, verified source proofs, initial-State centers,
State distributions, and explanations of what the observed proximity reveals.
A mathematician should be able to find a relevant connection or proof passage,
open its source, and judge the explanation. This offers a concrete route to value
in mathematical navigation, comparison of alternative arguments, and teaching.
It is a proposal to test, not an established benefit of the current encoder.

After that gate, prioritize known connections, then comparisons of existing proof routes.
For cumulative mass specifically, ask whether its features help locate meaningful
excursions or differences between arguments. Retain the full vectors and ordered
provenance so that a disappointing radial summary does not erase other evidence.
Only pursue automated proof shortening after there is evidence that the geometry
helps interpret valid existing routes.

Success should ultimately include mathematical readers finding the explanations
correct and the navigation useful; numerical proximity alone cannot establish
community value. An initial deliverable can be a carefully documented worked
example. Broader usefulness needs repetition and independent mathematical review.
Reader feedback is a future evaluation step, not authorization to contact others.

For an LLM continuing this work: preserve every collected occurrence, keep the
initial State as center, distinguish measurements from proposals, and report
unsuccessful cases. Do not introduce a shortest-proof collection filter, train a
model, demand an unknown discovery, or claim that high density means a good proof.
This note records the proposed next investigation; it does not report its execution.

## What we are trying to learn

Can the geometry of theorem initial States and their associated proof States
make meaningful mathematical relationships easier to recognize? Can it also help
us recognize direct routes in existing proofs? A known connection appearing at a
surprisingly short distance is a legitimate first success. Discovering an unknown
connection or generating a new, shorter proof is not required.

The user wants direct proofs with few unnecessary steps. Collecting all available
proofs supplies alternative routes to examine; it does not commit us to treating
long or frequently copied routes as desirable. We preserve every State occurrence
and its provenance while investigating what makes a route useful.

Three contributions deserve separate assessment:

| Contribution | Question | Useful evidence |
|---|---|---|
| Theorem placement | Do initial-State embeddings bring mathematically connected theorems close? | Several interpretable examples, with actual statements and neighboring alternatives inspected. |
| Theorem Density Object | Does the distribution of proof States reveal something useful about a theorem or its relationships? | A reproducible feature of the State distribution that corresponds to an identifiable mathematical feature. |
| Proof trajectories | Does geometry help identify direct arguments among existing proofs? | Geometric measurements that agree with inspected differences between efficient arguments and detours. |

The first contribution does not need to fail for us to study the second. Comparing
them establishes what each contributes. Neither requires encoder training or a
new proof-search system. There is no arbitrary ten-percentage-point success gate.

## Definition we have agreed on

For a proved theorem T, let c_T be the embedding of its complete initial goal and
assumptions, before proof steps. It is not a centroid or the generic `no goals`
display. Let x_1, ..., x_n be the retained nonempty proof-State occurrences across
its acquired proofs, in the same encoder coordinate system. The object retains
these vectors, their rays to c_T, and theorem/proof/State provenance.

Each occurrence contributes one unit of observed mass. Coincident vectors remain
separate occurrences. Mass is at observed endpoints; a drawn ray does not assert
that intermediate positions are valid or observed proof States. The center is a
reference point, not an extra manufactured observation. If initial States occur
in the traces, their occurrences remain, including any mass at radius zero.

The agreed cumulative quantities are:

```text
r_i = ||x_i - c_T||
N_T(r) = number of retained State occurrences with r_i <= r
F_T(r) = N_T(r) / n
```

N_T reports counts; F_T reports the fraction of this acquired object's States
within radius r. F_T is defined only when n > 0. The name Theorem Density Object
does not require estimating mass per unit of ambient volume. These functions are
cumulative mass, not a smooth probability density.

The existing geometry excludes generic empty `no goals` displays, with all those
records preserved in the archive and inspector. Their common embedding carries
no theorem-specific content. Retain that explicit convention; do not silently
delete any other State or overwrite the full archive. Counts must identify the
included records and distinguish nonempty observations from all archived records.

## How cumulative mass could actually help

### 1. Describe how proof States spread relative to the theorem

F_T answers a concrete question: what fraction of the acquired States lies within
a given distance of the theorem's initial State? Its quantile radii describe the
extent of the distribution without defining a polygon, fitting a neighborhood
radius, or inventing interior points.

An illustrative observation could be: most States of one theorem stay relatively
near its center, while another has a substantial distant portion. That becomes
mathematically useful if inspection shows that the distant portion corresponds
to a meaningful change of representation, auxiliary construction, or reduction.
For example, a proof may move from integer arithmetic to an argument in Gaussian
integers. This is a hypothesis to inspect, not a measured result or a promise that
the embedding detects such a move.

The next action is to open the States at the relevant radii and follow their
source proofs. A curve with a long tail alone is a description. A tail that
repeatedly identifies an understandable mathematical excursion is evidence of
interpretive value. We should also inspect cases with similar curves but different
mathematics, so that resemblance is not mistaken for meaning.

### 2. Compare existing routes to the same theorem

Retain the aggregate curve and also display each proof's cumulative curve around
the same theorem center, alongside its ordered States and proof text. This does
not remove long proofs or change their contribution to the aggregate.

This could reveal that one argument spends many recorded steps on an excursion
that another argument avoids. If inspection confirms unnecessary work, density
has helped identify an existing route worth studying. No new proof must be
generated. Conversely, a distant excursion might be the clever substitution
that makes a proof shorter. Small radii are not inherently good.

Since a forward proof begins at the center, distance to that center is not a
measure of remaining work. We must not reward monotonically approaching the
initial State or interpret radius as progress toward completion.

The aggregate alone cannot identify the best proof: it discards temporal order,
and a long proof contributes more occurrences than a short one. Provenance and
ordered transitions are essential for this use. Supplementary per-proof curves
explain the aggregate; they do not replace it with silently reweighted data.

### 3. Offer a coarse descriptor of proof organization

Two theorems could have similar radial profiles despite distant centers. This
would suggest similar *patterns of spread*, worth investigating through their
States. It would not yet demonstrate a shared mathematical idea.

A simple optional comparison is the area between their normalized curves:

```text
D_radial(A, B) = integral |F_A(r) - F_B(r)| dr
```

For the current unit-vector encoder, all center-to-State distances are in [0, 2],
so that is the integration interval. Use a common distance scale; do not rescale
each object's radius independently. This comparison concerns radial distributions,
not physical proximity of the theorem objects. It is a proposed descriptive
measurement, not a chosen semantic score.

Its value would be demonstrated by a repeatable correspondence between the
profiles and inspected proof organization. If similar profiles occur everywhere,
or primarily reflect serialization and proof-record counts, this descriptor may
have little mathematical value even if the full object remains useful.

### 4. Ask where one theorem's States lie relative to another theorem

For the user's interest in surprising proximity, an additional cumulative view
can retain the reference to a particular other theorem:

```text
C_A_to_B(r) = number of States of A within r of c_B / n_A
```

This asks whether an appreciable part of A's proof-State collection reaches near
B's initial State, even when the two initial States are distant. Inspect the
contributing States and their proof locations to determine whether a recognizable
relationship explains the proximity. Report the reverse direction separately;
the two quantities need not agree.

This is a proposed extension using the complete vectors in their shared space.
It cannot be recovered from A's own-center cumulative curve alone. It does not
prove that B can discharge any of A's goals, establish a valid transition, or
detect every relationship between two distributions. A useful connection may
involve a single rare State, so low cumulative mass must not hide it. The inspector
must retain those individual States and their actual distances.

## What cumulative mass cannot establish

Consider two illustrative planar objects centered at the origin. One has State
vectors (1, 0) and (2, 0); another has (-1, 0) and (-2, 0). Their N(r) and F(r)
are identical at every radius, although their States point in opposite directions.
These are schematic coordinates, not measurements from our unit-vector encoder.
The general loss of directional information also applies in the actual embedding.

Reordering a proof's States likewise leaves cumulative mass unchanged while
changing its trajectory. Therefore own-center cumulative mass alone cannot tell
us which mathematical ideas occur, whether two objects intersect, which direction
connects them, or which proof is shortest. A curve does not validate its encoder.

Additional limits need explicit treatment:

- **Record frequency:** N grows when more proofs or copies are acquired. F removes
  total-count scale but remains weighted by State occurrences. Copying only one
  proof can change F; copying the whole corpus equally leaves F unchanged.
  Frequency is not independent mathematical support or desirability.
- **Proof length:** long proofs contribute more mass. A short, elegant argument
  may be rare and nearly invisible in the aggregate. Show it through provenance.
- **Order and validity:** radial distances and straight rays are not verified
  proof transitions. Geometrically short routes may be mathematically invalid.
- **Recording granularity:** one tactic can perform substantial reasoning;
  fewer recorded steps do not automatically mean less mathematical work.
- **Representation:** pretty-printing, omitted types, repeated context and model
  behavior can create apparent structure. Formally faithful inputs and
  presentation sensitivity checks are needed before semantic interpretation.
- **Coverage:** observed mass describes the acquired proofs. It is not the
  distribution over all possible proofs, and current acquisition does not include
  all known proofs of each theorem.

We should not divide by a 1,472-dimensional ball volume and call the result
mathematical density. That would introduce a volume interpretation unsupported
by the observed discrete States. Cumulative mass avoids that choice without
solving the limitations above.

## A manageable first investigation

1. **Prepare trustworthy inputs.** Verify each initial center against the proved
   theorem type. Establish that center and proof States use a documented compatible
   serialization and encoder runtime. Do not mix the new type-aware center inputs
   with old raw State vectors and assume they are directly comparable. Preserve
   record-level admission, completeness and serialization limitations.
2. **Start with interpretable examples.** Use several known mathematical
   connections and several theorems with contrasting available proof routes.
   Inspect all the acquired States for those theorems; do not cap or compress
   them. Select examples for mathematical interest, not only because a baseline
   fails. Record why each was selected and what we expected before measurement.
3. **Show the evidence together.** Present center distances, N and F, per-proof
   curves, ordered routes, and clickable contributing States. Add cross-center
   cumulative views for known connections. Measure in the original space, with
   shared projections as aids to inspection.
4. **Write a mathematical account of each case.** Explain what a geometric feature
   corresponds to in the proof, including failures to find an interpretation.
   For directness, compare recorded transition count and geometric path length
   with the actual argument and tactic granularity. Neither metric defines the
   best proof by itself; a shortest observed proof is not a globally minimal proof.
5. **Check whether the account survives obvious alternatives.** Show basic
   vocabulary similarity, proof lengths and copy counts alongside the finding.
   Inspect equivalent presentation changes and additional proofs when available.
   Preserve original results. Optional proof-block reassignment can diagnose
   whether theorem ownership matters, but destroys meaningful structure and
   must be labelled a control, not the proposed architecture.
6. **Repeat before generalizing.** Follow up promising interpretations on further
   examples chosen before their geometry is inspected. Exploratory discoveries
   remain welcome; report how they were found rather than presenting selected
   striking cases as an unbiased success rate.

No single ranking must defeat every ordinary mathematical neighbor. A known
cross-field connection can be useful even when same-topic theorems are closer.
Likewise, a curve that is visually interesting but has no stable mathematical
interpretation has not yet demonstrated mathematical usefulness.

The immediate deliverable should be a small set of inspectable case studies,
each stating the observation, mathematical interpretation, competing explanation
and remaining uncertainty. Automated proof shortening is a later possibility.

## What the repository has established so far

The [historical-connections pilot](../results/historical-connections-v1/README.md)
found all four selected historical partners within the top six of 65 candidates
in both directions under each of three presentations. Vocabulary similarity also
gave strong rankings. This supports exploring theorem placement; it did not
measure proof-State cumulative mass or establish an added contribution from it.

The [boundary explorer](../results/theorem-boundaries-v2/README.md) and
[admitted State archive](../results/state-objects-admitted-v1/README.md) preserve
valuable observations and provenance. They are not completed density-object
experiments. The prior min/max boundary questions are historical alternatives,
not prerequisites for the present mass-based investigation.

The clearest near-term demonstration of cumulative mass's value would be a
repeatable case where its curve directs attention to a mathematically meaningful
part of the proof collection, and the underlying States explain why. If that
does not happen, we should say the radial summary has not helped; this does not
by itself settle the usefulness of theorem placement or the full State geometry.
