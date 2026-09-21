# Noema

**Does the geometry of a theorem's proof states know which theorems are related?**

A Lean proof passes through a sequence of goal states. Encode every state of
every proof, summarise a theorem by the centroid of its states, and ask whether
theorems that are mathematically connected sit closer together than theorems
that are not. If they do, the map can be asked a question no citation search
can answer: *which two theorems should be connected, but have not been yet?*

That last question is still open. What follows is the evidence collected so far
that the map is measuring something real.

## Three measurements, and the control that decides how to read them

| | what it asks | result |
|---|---|---|
| [Replication](results/state-bridge-v1/README.md) | do proofs sharing a rare lemma have nearer centroids? | AUC **0.877**, margin over shuffled control **+0.164** |
| [Betweenness](results/state-bridge-v1/README.md) | does a known bridge theorem sit *between* its two endpoints? | all **6/6** families in the top 4.3% of 1,795 objects, four in the top 1.4% |
| [Forward test](results/mathlib-forward-v1/README.md) | does the 2024 map point at links Mathlib only made by 2026? | angle **AUC 0.958** against proof size's 0.498 and vocabulary overlap's 0.764 |
| [α-rename control](results/rename-control-v1/README.md) | does any of it survive deleting every variable name? | all three: forward **0.964**, betweenness **6/6 in the top 3.3%**, replication margin **+0.162** |

1,797 Mathlib theorems, 99,275 captured proof states, 23,874 unique state texts,
encoded with the pinned ReProver ByT5 retriever. The corpus was built by
expanding outward from six known bridge families, so it is a positive control by
construction.

The fourth row is the one that decides how to read the first three. The encoder
consumes pretty-printed text, so every result above could have been stylometry —
the map recognising an author's naming habits rather than any mathematics. It is
not: renaming every binder and hypothesis in all 1,797 theorems, certified in
Lean, leaves each measurement where it was or slightly better, while the purely
lexical baseline it is scored against drops from 0.764 to 0.610. The ablation
demonstrably removed information and the geometry did not depend on it.

**Betweenness is the load-bearing one.** The replication shares a confound with
its own target: proof size alone predicts "these two proofs share a rare lemma"
at AUC 0.740, because long proofs cite more lemmas and their centroids drift
toward the corpus mean. Only the +0.164 margin over the shuffled control is the
encoder's. Betweenness does not inherit that confound — its null is the same
corpus scored the same way — and neither does the forward test, where proof size
is a coin flip at 0.498.

The forward test's label contains no 2024 vocabulary at all: between Mathlib
`f0957a7` (2024-07-01) and `09712d48` (2026-09-21) — 812 days, 22,961 commits,
65,368 new declarations — did anyone write a theorem citing both halves of a
pair? Over 1,530,134 eligible pairs the base rate is 1 in 69,551. The corpus
sits at a median 89.3° (quartiles 87.3–90.4); the hits sit at a median 74.0°,
with 20 of the 22 below 85° where only 14.9% of pairs live, and 13 below 75°
where 2.9% do.

**Read the AUC, not the band lift.** The 22 positives are not 22 independent
observations: 32 theorems carry all of them, `Complex.exp_add` appears in four.
[`analyze-forward-independence.py`](scripts/analyze-forward-independence.py)
takes the clustering apart. The AUC does not move — 0.963 on a vertex-disjoint
subset where no theorem is used twice, 0.963 after dropping every pair that
touches a seed family, 0.964 after dropping the `Complex.exp*` hub outright, and
0.955–0.966 across all 32 leave-one-endpoint-out refits. Against a cluster null
that substitutes each endpoint for a random theorem while preserving exactly
which endpoints pair with which, the null sits at 0.499 ± 0.068 and the observed
0.958 does not occur in 5,000 draws. The 124× lift in the 45–55° band is the
fragile number: it rests on four pairs, and dropping that one hub leaves one.

## What this does not show

- **No connection has been discovered.** Every link measured here is one a human
  already made. Recognising them is a precondition, not the result.
- The band edges in the forward test were fixed with the table visible, and the
  band that got reported, 45–55°, is narrower than the 40–55° that was posted to
  issue #1 at 15:05:53Z before the analysis was committed at 15:31:00Z. 22
  positives is a thin base, and the band lift does not survive dropping a hub
  theorem. The AUC does; that is the number the claim rests on.
- **Vocabulary does some of the work.** Token overlap between two theorems'
  state texts predicts the same 2026 label at AUC 0.764 on its own
  ([`vocabulary.json`](results/mathlib-forward-v1/vocabulary.json)): connected
  pairs share 17.0% of their state vocabulary against 7.7% for an average
  eligible pair. The angle's 0.958 is well clear of that, and 3 of the 22 hits
  share under 5%, but "still separates where words give little" is the
  defensible claim, not "vocabulary-independent". The α-rename arm sharpens this
  rather than settling it: stripping names costs the lexical baseline 15 points
  (0.764 → 0.610) without costing the angle anything, so the angle is not riding
  on *naming*, but 0.610 is still well above chance and constants are untouched.
- **It is not a subfield detector, which was the most plausible deflation.**
  Same area means same people working in the same active corner of Mathlib, and
  those pairs get connected later anyway — so the angle could predict the label
  without understanding anything. Measured
  ([`area-control.json`](results/mathlib-forward-v1/area-control.json)): the
  angle predicts "same area" at only 0.656, "same area" predicts the 2026 label
  at only 0.660, and on cross-area pairs alone — where the confound cannot
  operate — the angle still scores **0.955 on 13 hits** against 0.958 overall.
  That rules out this story, and the α-rename effect — a different story, and
  the one that stayed open longest — is ruled out separately below.
- The forward label is `git grep` over full declaration names, so it misses
  citations under an `open` namespace and does not check that a citation is
  load-bearing. Both attenuate rather than inflate.
- **Exact invariance is false; discriminative invariance holds.** The encoder
  is not name-blind, and never was: under α-renaming the centroids move a median
  **20.0°** (quartiles 15.2–26.3, max 69.5°), with only 31 of 1,797 theorems
  left under 1°. The 8/8 falsification in
  [encoder-invariance-v1](results/encoder-invariance-v1/README.md) and the 48.1°
  single-state probe in [issue #2](https://github.com/sanaani/noema/issues/2)
  are both confirmed. What they do not imply is what was feared: everything
  moves *together*, so the arrangement the three tests read is preserved and all
  three survive ([rename-control-v1](results/rename-control-v1/README.md)).
  Distances here still must not be read as absolute relatedness — only as rank.
- **The statement-embedding null is not a like-for-like comparison.** Five
  encoders on theorem statements put the four prespecified targets nearer than 98.8–99.2% of
  background controls — they pass the bar the tests above are scored against.
  What they fail is a *lexical* control: against four word-matched decoys the
  target was nearer only 12.5–18.8% of the time, so the proximity tracks
  wording
  ([semantic-encoder-evaluation-v1](results/semantic-encoder-evaluation-v1/README.md)).
  Betweenness and the forward test have never been put through *that* control,
  so "statements fail, states succeed" is not established — the two were held to
  different bars. The α-rename arm closes part of the gap and not all of it: it
  ablates names and measures what the ablation cost the lexical baseline, which
  is a real lexical screen, but it is not the word-matched-decoy construction
  the statement encoders failed. Building those decoys for proof states remains
  the obvious next screen, and it has not been run.
- Nothing was fitted to the three measurements above: they are distances
  between frozen ReProver vectors, with no learned component anywhere. A
  trained linear head existed in an earlier line of work, over Qwen vectors of
  theorem *statements*; it predates the proof-state capture, contributes to
  none of the numbers here, and now lives in
  [`docs/history.md`](docs/history.md) with the other detours.

Each result directory states its own caveats; they travel with the numbers.

## The tree

```
docs/
  theorem-link-discovery-plan.md   the hypothesis, as predicted; superseded stages flagged
  state-bridge-run-plan.md         how the 1,797-theorem run was designed and costed
  muse-brief-lemma-hygiene.md      spin-off: anonymous-lemma detection for Mathlib
  latent_geometry_...plan.md       the original proposal, preserved byte for byte
  history.md                       every earlier line of work, and where to read it
results/
  link-graph-v1/        206,889 theorem->dependency edges from pinned Mathlib; the
                        bridge-triple scan; the Lean elaborators that produced them
  state-bridge-v1/      the replication and betweenness tests
  mathlib-forward-v1/   the 2024 -> 2026 forward test, its centroids, and the
                        independence and vocabulary checks on it
  rename-control-v1/    all three measurements rerun with every binder and
                        hypothesis renamed in Lean under a structural
                        certificate; the arms, the prespecification, the verdict
  bridge-expansion-v1/  the six machine-checked (A, B, bridge) families
  bridge-conjecture-v1/ a machine-proposed, machine-checked bridge — proposed by
                        the earlier statement ranker, not by the state geometry
  state-object-v1/      the 128-object archive the first AUC 0.786 came from
  historical-connections-v1/  the initial-State pilot that seeded the six families
  encoder-*/, semantic-*/, state-consistency-v1/
                        what the encoder does and does not do: α-rename
                        invariance, a five-encoder comparison, certified
                        structural capture, and the statement-embedding null
scripts/   the pipeline, in order: scan -> filter -> select -> capture -> encode -> analyse
           bootstrap-*/setup-* provision a pinned host or encoder for a rerun;
           audit-/evaluate-/verify-* regenerate one archived result each
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
.venv/bin/python scripts/analyze-state-geometry.py          # the first AUC 0.786
.venv/bin/python scripts/analyze-mathlib-forward.py         # the forward test
.venv/bin/python scripts/analyze-forward-independence.py    # does the clustering break it?
.venv/bin/python scripts/analyze-forward-vocabulary.py      # how much is word overlap?
.venv/bin/python scripts/analyze-forward-area.py            # is it just a subfield detector?
.venv/bin/python scripts/analyze-size-confound.py           # proof size on both labels
.venv/bin/python scripts/analyze-state-bridge.py            # needs the vectors, see below
```

The α-rename control compares two arms of one encode, so it needs that encode's
vectors (517 MB, not committed) rather than the centroids:

```bash
.venv/bin/python scripts/analyze-rename-control.py \
    --arms outputs/rename-control-v1/arms \
    --vectors outputs/rename-control-v1/vectors/reprover-embeddings.npz
```

Its two exported centroid files *are* committed
([`centroids-original.npz`](results/rename-control-v1/centroids-original.npz),
[`centroids-alpha.npz`](results/rename-control-v1/centroids-alpha.npz)), so the
forward, vocabulary and independence scripts can be pointed at either arm with
`--centroids` without rebuilding anything.

The first six need nothing but the repository, and CI runs all six. The five
that read `results/mathlib-forward-v1/centroids.npz` use it as 1,797 unit
centroids, 9.9 MB, the only input they need from the encode, exported by
`scripts/export-forward-centroids.py` and checked against the full vectors by
`tests/test_forward_centroids.py` wherever those vectors are present.

`analyze-state-bridge.py` is the one that cannot: its shuffled control permutes
the vector/text assignment, so it needs every state vector, and
`outputs/state-bridge-v1/vectors/reprover-embeddings.npz` is 272 MB and
therefore not committed. Everything upstream of it is:
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
git checkout full-research-trail   # tag on 2e56503, the commit before the prune
```

2,128 files against the 418 here. `a44f244` is the prune itself: 1,743 files,
1,663,285 deletions, no new work.

## License

[Apache-2.0](LICENSE), matching Lean and Mathlib, so the pinned Mathlib, the
vendored `REPL` fork and this work all sit under one license.

Imported material keeps its own terms and is not relicensed here: the Lean REPL
carries its original Apache-2.0 headers, the ReProver export is the authors',
and `results/state-object-v1/source-manifests/` retains the publisher notices
for everything it archived.
