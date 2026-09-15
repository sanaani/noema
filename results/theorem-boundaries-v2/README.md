# Boundaries through the observed dots

Open the [revised explorer](explore.html). It starts with `lean_workbook_34313`
and `lean_workbook_13957` overlaid in one shared coordinate frame.

The user rejected the convex enclosure's empty area and the generic red “no goals”
point, requested an inward-bending boundary minimizing area, and asked for shared
orientation, x–y axes, visible zero and scale. This view implements those changes.
The [earlier convex explorer](../theorem-forms-v1/explore.html) is preserved as an
archive, along with every source record and original vector.

## Selecting and navigating objects

Use **Visible objects** to search theorem names and check or uncheck them
individually. **Show all 102**, **Clear**, and **Show only inspected theorem**
are shortcuts. Clicking a visible name or state changes the inspector without
removing other objects or resetting the camera. Selecting an absent theorem adds
it to the view. Membership changes fit the visible set and zero; **Fit / reset
view** restores that framing after navigation. Local axes show just the inspected
theorem, preserving the shared-view selection for your return.

Drag the drawing to pan. Scroll, pinch, or use **+ / −** to zoom. Wheel and pinch
zoom preserve the coordinate beneath the pointer or gesture center. Axes keep
coordinate units as you move; when zero leaves the view, ticks move to the plot
edge and the status reports that the origin is off screen. SVG export includes
the current camera, clipping, and visibility settings.

Colors are fixed per theorem: `lean_workbook_13957` is teal and
`lean_workbook_34313` is purple. Names in the legend and state/boundary hover text
identify objects, including when many colors look similar. The outlined ring
marks the inspected state, not a centroid. Toggle **Show state dots** to see
thin shaded regions without dot overlap. Hiding dots only changes their display;
all records remain available. Showing all objects draws 102 boundaries and
10,748 separate plotted state records, with no sampling or aggregation.

To regenerate only the interface from the saved payload, without recomputing
geometry or re-encoding states:

```bash
.venv/bin/python scripts/render-boundary-explorer.py
```

Browser navigation and selection checks are recorded in `navigation-validation.json`.
The original geometry validation remains in `validation.json`.

## What changed

- **10,748 nonempty state displays are plotted.** The 5,844 `no goals` records stay
  in the 16,592-record archive and are accessible through the inspector's archive
  checkbox. They participate in neither the new boundaries nor the fitted axes.
  No other state is omitted. There is no text normalization, re-encoding, state
  deduplication, or added neighborhood radius.
- Each projected boundary **visits every observed location**, including interior
  locations of the old convex enclosure. Coincident records share a geometric
  location but keep separate rows and inspector entries. Boundary location indices
  do not replace the original vectors or records.
- The polygon must have no crossing, overlapping or nonadjacent touching edges.
  Its vertex set is exactly the observed projected locations; no invented bend
  points are allowed. Minimize enclosed area over orders satisfying those rules.
- Small cases use exhaustive search over every cyclic order (up to nine different
  projected locations). Larger cases use multiple starting orders and strict area
  descent via vertex relocation and edge reconnection. The latter are explicitly
  labeled **global minimum unproven**. This is a computational method choice,
  not a cap on the data: every point participates in every case.
- Degenerate point/collinear cases have zero area; no thickness is invented.
  All other areas and non-crossing predicates use exact integer arithmetic on the
  supplied binary floating-point coordinates. This certifies the geometry of the
  stored projections, not the encoder's mathematical meaning.
- The optional dashed convex outline is only a comparison. The filled area is the
  new candidate polygon, not a convex hull with an altered visual style.

This is the established **minimum-area simple polygonization** problem. Exact
optimization is difficult in general. The CG Challenge overview and exact-methods
paper distinguish heuristic results from proven optima:
[overview](https://arxiv.org/abs/2111.07304),
[exact methods](https://arxiv.org/abs/2111.05386).
Our search implementation is a small deterministic implementation of the stated
moves, not a claim to reproduce the strongest published solver.

Restricting vertices to observed locations is an explicit assumption that makes
the problem finite. If arbitrary bend locations and arbitrarily thin connecting
strips were permitted instead, “minimize area around the points” would not identify
this particular boundary. A single simple polygon also imposes connectivity within
each drawn object; it cannot establish that the observations naturally form one
connected region.

## Rotation, axes, zero and unit vectors

The old default fitted two axes separately to each theorem. Shapes in those
panels had no common orientation or location reference. Their apparent relative
rotation therefore could not be interpreted as a rotation in one shared space.

The new default uses **the same two orthonormal axes for every theorem**. The two
requested examples are overlaid so their relative positions and directions can be
compared in that projection. Each gallery tile uses the same axes and scale.
The main display can fit the selected objects plus zero, or use the full shared
scale. Local axes remain available for inspecting individual forms; comparison
is disabled in that mode and its separate coordinate frame is labeled.

All original 1,472-dimensional vectors have unit length within floating-point
precision. Their orthogonal 2D projections generally have length less than one.
The projection coordinates are `x = vector · axis_x` and `y = vector · axis_y`.
We center observations to **fit** the axes but do not subtract that center when
plotting coordinates. Therefore the original zero vector projects to `(0, 0)`.
The gray cross is this coordinate reference, not a state and not the `no goals`
embedding; it is never added to a boundary. The old centered PCA coordinates had
used a different origin convention, so old coordinate numbers should not be
compared directly with the new ones.

A projection can map separated locations to overlapping ones. These 2D candidate
polygons are not asserted to be projections of an already-defined nonconvex
1,472-dimensional theorem region. Optimizing a polygon separately in each plane
does not define such a region. This version supports the requested visual boundary
investigation while leaving that higher-dimensional construction open. The previous
claim that every object touches depended on the now-excluded generic display and
does not describe these revised boundaries.

Formatting sensitivity and incomplete structured-state capture remain unresolved.
The inspector retains formatting witnesses, original state text and provenance.

## Reproduce, verify and recover

From the repository root, with the existing pinned Python environment:

```bash
# Optional acceleration: requires a C++17 compiler and Boost headers.
g++ -O3 -std=c++17 scripts/area-boundary-opt.cpp -o outputs/area-boundary-opt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/build-boundary-explorer.py \
  --optimizer outputs/area-boundary-opt
python scripts/verify-boundary-explorer.py
```

Omit `--optimizer` to use the equivalent pure-Python search. The C++ backend caches
exact geometric conflict tests; it does not change the objective or drop states.
The saved validation includes agreement checks against the Python implementation.
A local Boost 1.83 header package was extracted under
`outputs/theorem-boundary-review/boost/`; no system package installation was needed.
Its compiler include flag is
`-I outputs/theorem-boundary-review/boost/usr/include`.

`boundaries/` checkpoints each theorem/frame independently. A checkpoint is reused
only when its projected row bytes and implementation fingerprint match. The full
search used all 102 theorems in both frames. `boundaries.json` aggregates results;
`construction.json` maps every plotted and archived record to original row indices;
`projections.npz` stores the two frames and their axes; `forms.json` records
measurements on nonempty-state vectors. `summary.json` records source/code hashes,
unit-norm checks, optimization statuses and the requested rotation comparison.
`viewer-data.json` and `explore.html` retain all original record metadata.

Verification checks all original vector hashes and record memberships, both
coordinate transforms, zero, every boundary's exact area and non-crossing property,
and exhaustive minima where claimed. The browser self-test checks every dot against
an actual boundary vertex, both frames, x–y axes, zero and archive accessibility.
Use `explore.html#self-test` to run it. SVG export saves the current drawing.

The complete admitted source and prior results remain unchanged. No encoder or GPU
run was performed. These are projected boundary studies, not a new proof sample,
prediction task, model training run or claim of semantic topology.

## The requested pair in the shared view

After excluding the generic completion displays, `lean_workbook_34313` has 26
plotted records and `lean_workbook_13957` has 196. Their shared-frame x-ranges are
approximately `[-0.676, -0.556]` and `[-0.106, 0.160]`, respectively. Thus these
particular projected boundaries are separated by a horizontal gap of about 0.450.
Their dominant recorded-spread directions make angles of 91.8° and 47.7° to the
shared x-axis (directions are defined modulo 180°). The approximately 44.1°
difference is a comparison within this projection, not a claim that one complete
object is a rigid rotation of the other or that the angle has mathematical meaning.

The computed shared-frame areas are about 20.1% and 1.8% of their respective convex
enclosures. Both are best-found results with unproven global minima. The thin
branches in the larger example are an actual consequence of this area objective;
no thickness or smoothing radius was added. The common plane retains 24.9% of the
whole nonempty recorded distribution's squared spread. Its limitations remain
relevant even though positions and scales now match across objects.
