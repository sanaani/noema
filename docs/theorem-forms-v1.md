# First exploration of theorem-object forms

The proof-admission and separate-row fixes hold. We have constructed and measured
**102 filled theorem hulls using all 16,592 admitted state vectors**. Their forms
can now be inspected in the [interactive atlas](../results/theorem-forms-v1/explore.html),
[complete PDF atlas](../results/theorem-forms-v1/atlas.pdf), and
[summary figure](../results/theorem-forms-v1/overview.png).

The strongest finding is a measurement problem: the common empty-goal display and
text formatting account for much of the apparent structure. These objects are
useful for investigating the representation, but their shapes are not yet reliable
evidence of the geometry of mathematical ideas. This does not test or refute the
broader theorem-object hypothesis.

All recorded states remain separate physical rows. The object is their filled
convex enclosure. The mean used to fit display axes is only an arithmetic step;
it never replaces the object. No proof or state was sampled, merged, removed,
re-encoded or moved. Six excluded and 148 held theorem groups remain outside this
active analysis, with their original data preserved. The admitted groups contain
813 source proof records, including 727 distinct scripts; script differences are
not a count of independent mathematical arguments.

## What the objects look like

Local two-dimensional pictures often resemble elongated triangles or fans with
one distant tip. Some spread sideways substantially; the simplest is a line
segment. That visual description concerns projections, not their complete form.

| Measurement across 102 objects | Minimum | Median | Maximum |
|---|---:|---:|---:|
| Recorded states per object | 6 | 96 | 813 |
| Numerical affine dimension | 1 | 12 | 145 |
| Diameter in the original coordinates | 1.377 | 1.409 | 1.497 |
| Greatest distance from the diameter line / diameter | approximately 0 | 0.679 | 0.838 |
| Recorded spread captured by the best single axis | 47.2% | 78.6% | 100% |
| Recorded spread captured by the best two axes | 71.4% | 92.6% | 100% |
| Axes needed for 95% of recorded spread | 1 | 3 | 8 |

Diameter and sideways extent describe the hull. Spread percentages describe the
recorded-row distribution and depend on repetitions; they are not fractions of
hull volume. Local pictures use different fitted axes and scales, so they cannot
establish relative placement or intersection. The atlas also offers common axes
and a common scale. Those common axes retain a median 57.4% of each object's
within-object spread, making the lost information explicit.

Every object has the maximum numerical affine dimension permitted by its observed
coordinate locations: one less than their count. Every different location passes
a supporting-direction check as a vertex. These are numerical simplices in their
own affine spans—higher-dimensional analogues of triangles and tetrahedra, usually
very uneven in extent. Repeated observations remain separate rows at their
original locations; counting coordinate locations for this diagnostic does not
compress the objects.

This is largely a property of the measurement setup. Vector norms differ from 1
by at most 8.9e-16. Distinct points on an exact unit sphere are exposed vertices:
the direction of a point has a strictly larger dot product with itself than with
any other sphere point. We checked the corresponding gaps on all actual rows;
the smallest is 0.000784, well above the roundoff guard. The numerical ranks also
remain unchanged under relative singular-value cutoffs of 1e-8 and 1e-6. The
objects occupy lower-dimensional affine spans, so their 1,472-dimensional ambient
volume is zero. This is not evidence that the theorems lack mathematical content.

## The shared tip dominates

All 102 objects contain exactly the same encoded `no goals` display. There are
5,844 such records, 35.2% of the active dataset. A longest span of **every object**
runs from this point to a nonempty display. Diameters vary by only about 0.12 across
the entire set, despite large differences in state counts and numerical dimension.

A variance decomposition using every record finds that the difference between
empty and nonempty display groups accounts for a median **78.4% of recorded
spread**. This is a descriptive decomposition, not a claim of causation or a
replacement object. Empty rows remain in both the analysis and every projection.
The shape's dominant direction often measures the change from a displayed
obligation to a generic completion marker.

No theorem's diameter exceeds the largest diameter of one of its individual source
proof records. This does **not** mean alternative proofs add nothing: 101 objects
have coordinates belonging to a source proof record and absent from that theorem's
other source proof records. Those coordinates can add lateral extent and vertices.
Their novelty can also reflect printing or replay differences, so it does not by
itself establish new mathematical arguments. Diameter alone misses this structure.

## Contact and connectivity

All **5,151 theorem pairs** were checked in the original coordinate space:

- **5,150 pairs intersect only at the shared empty-goal point.**
- **One pair intersects along a segment**, from that point to a shared displayed
  intermediate obligation:
  ```lean
  a b c : ℝ
  ⊢ 0 ≤ (a - b) ^ 2 + (b - c) ^ 2 + (c - a) ^ 2
  ```

The pair is `lean_workbook_plus_9114` and `lean_workbook_5091`. Their enclosing
obligations differ; this is a shared local subgoal. Earlier evidence established
at least a segment. The new separating-plane certificate checks all 450 and 349
rows, puts all other rows strictly on opposite sides, and leaves both endpoints
on the plane. Its checked margin is approximately 0.0480 and endpoint residual
6.94e-18. Thus the intersection is exactly this segment within numerical precision.
The [certificate](../results/theorem-forms-v1/segment-certificate.json) is retained.

The collection is connected through the generic shared point. Because every hull
contains it, their union is also star-shaped about that point: moving any point
straight toward it stays inside the union. This follows from the construction,
not from discovered mathematical relationships. Within each object, convexity
already rules out separate components and holes. The current construction therefore
cannot reveal disjoint theorem objects while this common coordinate is included.
No state was dropped to change that answer.

## Formatting can manufacture apparent extent

Inspecting the median-diameter example exposed an additional problem. The same
printed context and goal, with line breaks replaced by spaces, map to vectors
**0.642 apart—45.5% of that object's diameter**. No mathematical change is needed
to produce this geometric separation in that pair of displays.

We extended the exploratory analysis to every admitted record, grouping strings
only for a literal whitespace-split-token diagnostic. This found **246 variant
groups in 79 theorems**, involving 4,774 records. Among affected theorems, the
maximum within-group separation ranges from **7.3% to 69.7% of object diameter**,
with a median of **34.7%**. Every pair of original vectors remains unchanged.
This is not semantic canonicalization: whitespace inside a string literal, for
example, is not assumed mathematically irrelevant. The concrete median example
contains ordinary binders and an arithmetic goal, without string literals.

The [full diagnostic](../results/theorem-forms-v1/formatting-sensitivity.json)
retains all group memberships and distance witnesses. The interactive atlas
shows each object's formatting result and lets the reader inspect both witness
records. We have replaced an unsupported interpretation of geometric extent with
an explicit, inspectable measurement of this confound. We have **not** repaired
the encoder's formatting sensitivity or the missing structured-state capture;
normalizing text or dropping records here would hide the problem and alter the
user's object definition.

## Examples selected by stated rules

The selection rules were written before the new summaries: minimum diameter,
lower-median diameter, maximum diameter, and maximum sideways/diameter ratio.
They are illustrative extrema and an order statistic, not representative examples
of mathematics. All 102 objects are shown in the atlas.

| Selection | Theorem | Observed form and source interpretation |
|---|---|---|
| Smallest diameter | `lean_workbook_plus_39161` | 33 states; numerical dimension 2. The three coordinate locations are the empty display and two binder-printing versions of an initial arithmetic obligation. Its very thin triangle is not evidence of a three-stage mathematical argument. |
| Lower-median diameter | `lean_workbook_34729` | 21 states; numerical dimension 3. A real polynomial inequality solved by automation. The visible wedge includes substantial line-break sensitivity; 89.2% of recorded spread is the empty/nonempty contrast. |
| Largest diameter | `lean_workbook_plus_77403` | 108 states; numerical dimension 31. The proof moves from divisibility hypotheses to a remainder calculation and a fourth-power congruence. The larger recorded form plausibly reflects multiple displayed obligations, but no general correspondence with mathematical difficulty is established. |
| Greatest sideways/diameter ratio | `lean_workbook_plus_23187` | 170 states; numerical dimension 30. The recorded proof introduces quantified variables and assumptions, derives positivity facts, and transforms a rational inequality. Sideways extent is 83.8% of diameter. It warrants examining which formal state changes cause this extent. |

The exact source proofs and diameter witness states are saved in
[examples.json](../results/theorem-forms-v1/examples.json). Source comments are not
used as proof evidence. `PadicInt.modPart_nonneg`, the sole dimension-1 object,
contains only recorded outer proof-term boundaries; its line shape illustrates
extraction granularity, not intrinsic mathematical simplicity.

## What this resolves, and what it leaves open

The implementation now constructs the requested extended objects, retains all
admitted rows, measures their original-space extent, and makes every recorded
form inspectable. It distinguishes hull properties from multiplicity-sensitive
display statistics, and strengthens the segment witness to an extent certificate.
Formatting sensitivity is now measured throughout the set and visible beside
each object's shape, rather than silently assumed negligible.

The evidence is insufficient to assign mathematical meanings to these forms.
Full structured contexts and pending obligations are still missing; complete
all-known-proof coverage is not established; and the admission process leaves
**99 Workbook groups and only three Mathlib groups**. No broad cross-area pattern
can be inferred from that composition. Admission also does not prove every
remaining theorem's assumptions satisfiable.

A subsequent semantic investigation needs structured state capture and a stable,
validated serialization, with original records preserved. It should explicitly
check that meaning-preserving display changes do not produce the alleged signal.
Those are measurement repairs, not grounds to train a new model, remove the shared
endpoint, or switch to a prediction contest. The current results support the
intuition of extended, varying forms, while showing that these particular forms
are strongly influenced by how proof states were recorded and encoded.

Reproduction instructions and artifact hashes are in the
[results README](../results/theorem-forms-v1/README.md). The
[exploratory protocol](../results/theorem-forms-v1/protocol.md) records which
measurements were planned and which checks were added after seeing results.
