# Exploratory theorem-object forms, v1

Written before computing the new shape summaries. This is a descriptive follow-up,
not a preregistered hypothesis test. Existing admission and pair-contact results
are already known. No prediction task, encoder training, new sample, or success
threshold is introduced.

Use all 102 admitted theorem groups and all 16,592 physical rows in
`results/state-objects-admitted-v1`. Verify admission and source checksums first.
Construct each filled convex hull implicitly from its entire generating matrix;
retain every proof/state record, including identical coordinates. Counting equal
coordinates is a diagnostic only; no deduplicated matrix replaces the object.

Compute for every object:

- Original-space diameter and the two witnessing state records; maximum distance
  from the shared empty-goal vector; greatest perpendicular distance from the
  diameter line, divided by diameter (a measure of lateral extent).
- Numerical affine rank from the entire centered matrix, with the standard
  floating-point cutoff and a reported relative-cutoff sensitivity check.
- A supporting-direction check for every generating row: is its own vector a
  strict separator from every different coordinate in this object's matrix?
  This checks exposed vertices numerically; it does not identify distinct
  mathematical states.
- Singular spectrum, number of axes explaining 90%, 95%, and 99% of recorded-row
  squared spread, and first-/first-two-axis fractions. These measure the recorded
  distribution and depend on multiplicities; they do not define the hull, its
  volume, or the theorem's meaning. A mean is used only to center this diagnostic.
- Empty-goal record fraction, source proof counts, distinct source scripts,
  trace types, source environment counts, printed-text lengths and elisions.
  Measure single-source-proof diameters and source coordinate sharing to distinguish
  recorded proof coverage from demonstrated independent argument diversity.
- Whether each diameter uses the empty-goal endpoint. Also compute distances
  among nonempty displays as a labelled diagnostic; all empty-goal rows stay in
  the object and every saved projection.

Display every object, in a common projection for comparisons and in separately
fitted local projections for inspecting each form. Label local axes as incomparable
across objects. Export an all-object atlas and descriptive summary figures. Show
all distributions; choose textual examples by fixed rules: minimum diameter,
median diameter (lower middle), maximum diameter, largest lateral-extent ratio,
and the previously certified nonterminal-contact pair. Report ties by theorem ID.
No examples are presented as representative of mathematical areas.

Check the nonterminal-contact pair's intersection extent with a separating plane
through the shared segment if numerically possible. Previously saved witnesses
establish at least a segment, not that no additional overlap exists. If the new
certificate fails, keep that upper bound unresolved.

Interpretation limits remain active: 99 Workbook groups and 3 Mathlib groups are
not a broad sample of mathematics; source admission does not establish consistent
assumptions in every case, all-known-proof coverage, complete internal-state
capture, or semantic fidelity of printed goals/encoder coordinates. Convexity and
absence of holes are imposed. The common empty-goal encoding mechanically joins
all objects. No state will be removed to manufacture separation or overlap.

## Recorded exploratory extension

After the first summaries showed every diameter using the empty-goal endpoint,
add a variance decomposition across all rows into empty versus nonempty displays.
The between-group share measures how much recorded spread distinguishes these two
printed display types. It does not remove rows, redefine the hull, or validate a
semantic distinction. This extension was motivated by observed results.

Inspection of the fixed median-diameter example revealed line-break-only variants
with widely separated coordinates. Extend the exploration with a complete
within-theorem literal whitespace-split-token comparison across all admitted rows.
Record all matching groups, original-vector distance witnesses and their fraction
of full-object diameter. This is a text sensitivity diagnostic, not semantic
canonicalization: it neither proves state equivalence nor changes any encoding.
