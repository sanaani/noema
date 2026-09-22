# Phase 1 — Recognition

**Closed 2026-09-22.** Numbers here do not move. Later phases read these
artifacts; they do not rewrite them.

## The question this phase asked

> Does the geometry of a theorem's proof states know which theorems are
> related — for links a human has *already* made?

Recognition is a precondition, not the goal. The project exists to ask whether
the map can point at a link nobody has made yet, and phase 1 does not answer
that. It answers whether the map is measuring anything real at all.

## What it found

| | result |
|---|---|
| Replication: do proofs sharing a rare lemma sit nearer? | AUC 0.877, margin over shuffled control +0.164 |
| Betweenness: does a known bridge sit between its endpoints? | 6/6 families inside the top 4.3% of 1,795, four inside 1.4% |
| Forward test: does the 2024 map point at links Mathlib made by 2026? | angle AUC 0.973, against proof size 0.509 and vocabulary 0.691 |
| α-rename control: does any of it survive losing every variable name? | forward 0.974, betweenness 6/6 inside 3.3%, replication margin +0.162 |

The corpus is 1,797 Mathlib theorems, 99,275 captured proof states, 23,874
unique state texts, encoded with the pinned ReProver ByT5 retriever. Nothing is
fitted: every number is a distance between frozen vectors.

The repository README carries the full reading of these, including what each
does not show. The short version: the geometry is measuring something, it is
not measuring naming style, and it is not a subfield detector.

## What this phase does **not** establish

- **No connection was discovered.** Every link measured was one a human already made.
- **The corpus is a positive control by construction.** It was grown outward
  from the six bridge families by a rarity-weighted shared-landmark score, and
  that criterion is the replication test's own label. The replication is
  therefore scored on a corpus enriched for its positives.
- **The forward label is a grep heuristic.** It reads names out of the 2026
  Mathlib source rather than asking Lean what a proof used. Its first version
  was wrong in three ways and was rebuilt on 2026-09-22; see
  [`mathlib-forward-v1/README.md`](mathlib-forward-v1/README.md).
- **Seventeen positives is a thin base.** The AUC is stable across every
  subset and a degree-preserving cluster null, but the 45–55° band lift rests
  on four pairs and does not survive dropping one hub theorem.
- **Betweenness has no prespecified pass mark**, and its percentile is an
  observed rank among the corpus, not a fitted null.

## What is here

| directory | what it holds |
|---|---|
| `link-graph-v1/` | 206,889 theorem → dependency edges from Mathlib `f0957a7`, the bridge-triple scan, and the Lean elaborators that produced them |
| `state-bridge-v1/` | the replication and betweenness tests; the 99,275 captured states |
| `mathlib-forward-v1/` | the 2024 → 2026 forward test, its centroids, and the independence, vocabulary and area checks |
| `rename-control-v1/` | all three measurements rerun with every binder and hypothesis renamed in Lean under a structural certificate |
| `bridge-expansion-v1/` | the six (A, B, bridge) families, and what "machine-checked" does and does not certify |
| `bridge-conjecture-v1/` | a machine-proposed, machine-checked bridge, proposed by the earlier statement ranker rather than the state geometry |
| `state-object-v1/` | the 128-object archive the first AUC 0.786 came from |
| `historical-connections-v1/` | the initial-State pilot that seeded four of the six families |
| `encoder-invariance-v1/`, `encoder-comparison-v1/`, `semantic-encoder-evaluation-v1/`, `state-consistency-v1/` | what the encoder does and does not do |

## Handoff to phase 2

Phase 2 ([`../phase-2-dependency-labels/`](../phase-2-dependency-labels/README.md))
inherits four things and must not re-derive them:

1. **The captured states.** `state-bridge-v1/states-augmented.jsonl.gz` holds
   all 99,275, so the Lean capture against Mathlib `f0957a7` never has to be
   repeated. This was the expensive step.
2. **The centroids.** `mathlib-forward-v1/centroids.npz` is 1,797 unit
   centroids, the 9.9 MB collapse of a 272 MB encode. Any new label can be
   scored against these without touching a GPU.
3. **The 2024 dependency graph.** `link-graph-v1/edges.jsonl.gz` and the
   `Deps.lean` elaborator that built it. Phase 2's whole job is to run that
   same elaborator against the 2026 Mathlib.
4. **The analysis scripts**, unchanged and shared, in `scripts/`. A new label
   is a new `new-connectors.json`; every script that consumes it already
   exists and is already tested.

What phase 2 must **not** inherit: the grep label itself, and the assumption
that the seeded corpus is a fair test ground. Both are named above as
weaknesses, and closing them is the point of the next phase.
