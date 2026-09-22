# Phase 2 — Dependency labels

**Open.** Started 2026-09-22.

## The question this phase asks

> Does the phase 1 forward result survive a label that is *exact* rather than
> a text search, and does it still hold once there are enough positives for
> the number to mean anything?

Phase 1 answered "did anyone later write a theorem citing both halves of this
pair?" by searching the 2026 Mathlib source for theorem names. That is a
heuristic standing in for a fact Lean already knows with certainty.

## Why it has to change

Two reasons, and the second is the one that matters.

**The grep label is fragile.** Its first version credited a theorem with
citing `Foo.bar` when the source said `Foo.bar_baz`, counted hits inside `def`
bodies and docstrings, and counted a theorem's own header as a citation of
itself. That was found and fixed in
[`../phase-1-recognition/mathlib-forward-v1/`](../phase-1-recognition/mathlib-forward-v1/README.md),
but the class of error remains: a text search cannot see a citation made under
an `open` namespace, or one whose target was renamed after 2024.

**Seventeen positives is too few.** The AUC survives every subset test and a
degree-preserving cluster null, but the effect rests on seventeen pairs
carried by twenty-four theorems. That is the single weakest thing about the
result, and no amount of careful statistics fixes a thin base.

A kernel-level dependency label should fix both at once. Lean knows exactly
what every proof used. Phase 1 already extracted that for the 2024 library:
206,889 edges, via `link-graph-v1/Deps.lean`. The same elaborator against the
2026 library gives an exact answer key and should turn seventeen positives
into hundreds.

## Plan

1. Build the 2026 dependency graph with the phase 1 elaborator, pinned at
   Mathlib `09712d48`, the same commit the grep label already used.
2. Derive the label from real dependencies: a pair is positive when some
   declaration new since `f0957a7` depends on both halves.
3. Rerun the published forward, independence, vocabulary and area analyses
   against the phase 1 centroids, unchanged. Only the label moves.
4. Report the comparison honestly, including what happens if the effect
   shrinks. A larger, exact label making the result weaker is a finding, not a
   failure.

## What this phase inherits from phase 1

The captured states, the 1,797 centroids, the 2024 dependency graph and its
elaborator, and every analysis script. None of it is re-derived. See the
handoff section of
[`../phase-1-recognition/README.md`](../phase-1-recognition/README.md).

## Status

Nothing measured yet. This directory holds no findings.
