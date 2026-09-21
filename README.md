# Noema

**Does the geometry of a theorem's proof states know which theorems are related?**

A Lean proof passes through a sequence of goal states. Encode every state of
every proof, summarise a theorem by the centroid of its states, and ask whether
theorems that are mathematically connected sit closer together than theorems
that are not. If they do, the map can be asked a question no citation search
can answer: *which two theorems should be connected, but have not been yet?*

That last question is still open. What follows is the evidence collected so far
that the map is measuring something real.

## Three measurements

| | what it asks | result |
|---|---|---|
| [Replication](results/state-bridge-v1/README.md) | do proofs sharing a rare lemma have nearer centroids? | AUC **0.877**, margin over shuffled control **+0.164** |
| [Betweenness](results/state-bridge-v1/README.md) | does a known bridge theorem sit *between* its two endpoints? | all **6/6** families in the top 4.3% of 1,795 objects, five in the top 1.4% |
| [Forward test](results/mathlib-forward-v1/README.md) | does the 2024 map point at links Mathlib only made by 2026? | angle **AUC 0.958** against proof size's 0.515; 124× lift in the 45–55° band |

1,797 Mathlib theorems, 99,275 captured proof states, 23,874 unique state texts,
encoded with the pinned ReProver ByT5 retriever. The corpus was built by
expanding outward from six known bridge families, so it is a positive control by
construction.

**Betweenness is the load-bearing one.** The replication shares a confound with
its own target: proof size alone predicts "these two proofs share a rare lemma"
at AUC 0.740, because long proofs cite more lemmas and their centroids drift
toward the corpus mean. Only the +0.164 margin over the shuffled control is the
encoder's. Betweenness does not inherit that confound — its null is the same
corpus scored the same way — and neither does the forward test, where proof size
is a coin flip at 0.515.

The forward test's label contains no 2024 vocabulary at all: between Mathlib
`f0957a7` (2024-07-01) and `09712d48` (2026-09-21) — 812 days, 22,961 commits,
65,368 new declarations — did anyone write a theorem citing both halves of a
pair? Over 1,530,134 eligible pairs the base rate is 1 in 69,551. The band that
concentrates the hits, 45–55°, is where the six historical bridges already sat.
That reading came off the bridges first, before this label existed.

## What this does not show

- **No connection has been discovered.** Every link measured here is one a human
  already made. Recognising them is a precondition, not the result.
- The band edges in the forward test were fixed with the table visible. The
  preregistration is a timestamp: "40–55°" was posted to issue #1 at 15:05:53Z,
  the analysis committed at 15:31:00Z. 22 positives is a thin base.
- The forward label is `git grep` over full declaration names, so it misses
  citations under an `open` namespace and does not check that a citation is
  load-bearing. Both attenuate rather than inflate.
- **Rename robustness is unresolved.** A cosmetic α-rename moves a state 48.1°
  against 56.4° for a genuine mathematical change
  ([encoder-invariance-v1](results/encoder-invariance-v1/README.md)). If the
  bridges do not survive renaming, much of this is stylometry.
- Statement embeddings never showed this. Five encoders on theorem statements
  found no evidence for four prespecified cross-area connections
  ([semantic-encoder-evaluation-v1](results/semantic-encoder-evaluation-v1/README.md));
  the signal appears only in proof states.
- No model was trained on this corpus. The
  [link ranker](results/link-ranker-v1/) is a linear head over frozen vectors.

Each result directory states its own caveats; they travel with the numbers.

## The tree

```
docs/
  theorem-link-discovery-plan.md   the hypothesis and why the project pivoted to it
  state-bridge-run-plan.md         how the 1,797-theorem run was designed and costed
  muse-brief-lemma-hygiene.md      spin-off: anonymous-lemma detection for Mathlib
  latent_geometry_...plan.md       the original proposal, preserved byte for byte
  history.md                       every earlier line of work, and where to read it
results/
  link-graph-v1/        206,889 theorem->dependency edges from pinned Mathlib; the
                        bridge-triple scan; the Lean elaborators that produced them
  state-bridge-v1/      the replication and betweenness tests
  mathlib-forward-v1/   the 2024 -> 2026 forward test
  bridge-expansion-v1/  the six machine-checked (A, B, bridge) families
  bridge-conjecture-v1/ Lean-checked conjectures raised by the bridge scan
  link-ranker-v1/       linear ranking head and its held-out referee
  state-object-v1/      the 128-object archive the first AUC 0.786 came from
  historical-connections-v1/  the initial-State pilot that seeded the six families
  encoder-*/, semantic-*/, state-consistency-v1/, structural-semantic-*/
                        what the encoder does and does not do: α-rename
                        invariance, a five-encoder comparison, certified
                        structural capture, and the statement-embedding null
scripts/   the pipeline, in order: scan -> filter -> select -> capture -> encode -> analyse
src/noema/ encoders, typed state capture, replay
```

## Reproduce

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
ruff check . && python -m pytest
```

The analyses read committed artifacts:

```bash
.venv/bin/python scripts/analyze-state-geometry.py    # the first AUC 0.786
.venv/bin/python scripts/analyze-mathlib-forward.py   # the forward test
.venv/bin/python scripts/analyze-state-bridge.py      # needs the vectors, see below
```

The first two need nothing but the repository, and CI runs both.
`analyze-state-bridge.py` needs `outputs/state-bridge-v1/vectors/reprover-embeddings.npz`,
272 MB and therefore not committed. Everything upstream of it is:
`results/state-bridge-v1/states-augmented.jsonl.gz` holds the 99,275 captured
states, so the Lean capture — the long pole, a CPU host against Lean 4.9.0 and
Mathlib `f0957a7` — does not have to be repeated. Rebuild the vectors with

```bash
python scripts/build-encode-inputs.py --states results/state-bridge-v1/states-augmented.jsonl.gz ...
python scripts/encode-reprover-gpu.py ...        # L40S, 23,874 texts, 366s, ~$0.31
```

Model weights, transient run outputs and the uncompressed copies of the large
`.jsonl` artifacts stay out of git; the committed `.gz` files are byte-identical.

## History

This repository is a research trail, and the tree above is only its current
head. Four earlier lines of work — a synthetic distribution benchmark, two
matched formal studies, a strategy-transfer experiment and the convex-hull
"State object" investigation — ran before this one and are not in the tree.
They are intact in the commit history, with what was known at each point.

[`docs/history.md`](docs/history.md) maps each of them to its commits and says
what it found. The whole pre-prune tree is one command away:

```bash
git checkout full-research-trail
```
