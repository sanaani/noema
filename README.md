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
| [Replication](results/phase-1-recognition/state-bridge-v1/README.md) | do proofs sharing a rare lemma have nearer centroids? | AUC **0.877**, margin over shuffled control **+0.164** |
| [Betweenness](results/phase-1-recognition/state-bridge-v1/README.md) | does a known bridge theorem sit *between* its two endpoints? | all **6/6** families in the top 4.3% of 1,795 objects, four in the top 1.4% |
| [Forward test](results/phase-1-recognition/mathlib-forward-v1/README.md) | does the 2024 map point at links Mathlib only made by 2026? | angle **AUC 0.973** against proof size's 0.509 and vocabulary overlap's 0.691 |
| [α-rename control](results/phase-1-recognition/rename-control-v1/README.md) | does any of it survive deleting every variable name? | all three: forward **0.974**, betweenness **6/6 in the top 3.3%**, replication margin **+0.162** |
| [Exact label](results/phase-2-dependency-labels/link-graph-2026-v1/README.md) | does the forward test survive asking Lean, not grep, who cites whom? | 53 positives instead of 17; angle **AUC 0.898** |
| [Unseeded corpus](results/phase-2-dependency-labels/unseeded-corpus-v1/README.md) | does it survive a corpus drawn by seed instead of by hand? | 5,200 positives; angle **AUC 0.709**, cluster null 0.500 ± 0.017 |
| [Doubled corpus](results/phase-3-doubled-corpus/README.md) | on pairs sharing no area and under 5% vocabulary, is the angle above chance? | pre-registered: AUC **0.561**, **3.9 σ**; fresh pairs alone 3.6 σ |
| [Trained encoder](results/phase-4-trained-encoder/README.md) | is ReProver the bottleneck? a proof-state encoder trained on Mathlib, same pairs | pre-registered: hard-subset AUC **0.692** vs 0.598, **+0.095** [+0.044, +0.145]; but ReProver's top 100k holds 3× more hits |
| [Conjecture map](results/phase-5-conjecture-map/README.md) | does the 2024 map know where a new cross-area theorem will land? | pre-registered: AUC **0.568** [0.545, 0.590], real but weak; **word overlap does better** (−0.022) |

1,797 Mathlib theorems, 99,275 captured proof states, 23,874 unique state texts,
encoded with the pinned ReProver ByT5 retriever. The corpus was built by
expanding outward from six known bridge families, so it is a positive control by
construction.

The fourth row is the one that decides how to read the first three. The encoder
consumes pretty-printed text, so every result above could have been stylometry —
the map recognising an author's naming habits rather than any mathematics. It is
not: renaming every binder and hypothesis in all 1,797 theorems, certified in
Lean on the `Expr`, leaves each measurement where it was or slightly better,
while the purely lexical baseline it is scored against drops from 0.691 to
0.547. The ablation demonstrably removed information and the geometry did not
depend on it.

**Phase 2 changed how the first four rows should be read.** The 1,797-theorem
corpus was chosen by hand, and phase 2 replaced it with 11,489 theorems from
350 Mathlib files drawn once by a fixed seed, with the 2026 label taken from
Lean's own dependency graph rather than a text search. The forward AUC went
from 0.973 (grep label) to 0.898 (exact label, same corpus) to **0.709**
(exact label, unseeded corpus). The effect is real — 5,200 positives, predicted
to the pair before the first proof was replayed, against a degree-preserving
null of 0.500 ± 0.017 — and phase 1's number was mostly selection. On the
unseeded corpus two predictors that need no encoder, shared state vocabulary
(0.736) and same Mathlib area (0.712), match or beat the angle on the full pair
set. Where those two give nothing — cross-area pairs sharing under 5% of their
vocabulary, the pairs the project exists to find — the angle still scores
0.549 on 401 positives, 3.4 null standard deviations above chance, with
vocabulary at 0.370 as the control, and the top of that ranking is enriched
but thin. And the theorem's *statement*, encoded the same way, predicts the
label at least as well as its proof states (0.773 against 0.726), so the
premise that a proof's trajectory knows something its statement does not is
not supported. The phase 2 READMEs carry the tables; the paragraphs below are
phase 1's reading of phase 1's corpus and are kept as written.

**Phase 3 settled the hard subset.** Doubling the corpus to 24,916 theorems
(23,583 positives, again predicted to the pair before encoding) and fixing every
test in advance, the angle scores 0.561 on the hard subset at 3.9 σ under the
more conservative cluster null, and 3.6 σ on pairs no earlier phase had seen.
It is real and small: 0.60 with kind-aware ranking, about one true connection
per thousand among the closest candidates. Proof states against statements is
still undecided.

**Phase 4 changed the instrument.** A small Transformer trained for 15 minutes,
with no label, on the same 2024 proof-state texts ReProver read lifts the
hard-subset AUC from 0.598 to 0.692 (+0.095, interval +0.044 to +0.145, fresh
pairs +0.094), at 8.3 σ on its own against ReProver's 3.9. Under it the
statement beats the proof states. But ReProver's closest hard pairs remain
three times richer in true connections: the trained encoder orders the whole
ranking better, ReProver's short list is better.

**Betweenness is the load-bearing one.** The replication shares a confound with
its own target: proof size alone predicts "these two proofs share a rare lemma"
at AUC 0.740, because long proofs cite more lemmas and their centroids drift
toward the corpus mean. Only the +0.164 margin over the shuffled control is the
encoder's, and that margin is one shuffle draw (an independent re-encode gave
+0.167). The corpus itself was grown by that same rare-lemma criterion, so the
replication is scored on a corpus enriched for its own positives. Betweenness
does not inherit the size confound — its null is the same corpus scored the
same way, though it has no prespecified pass mark and its "top 4.3%" is an
observed rank, not a fitted null — and neither does the forward test, where
proof size is a coin flip at 0.509.

The forward test's label contains no 2024 vocabulary at all: between Mathlib
`f0957a7` (2024-07-01) and `09712d48` (2026-09-21) — 812 days, 22,961 commits,
65,368 new declarations — did anyone write a theorem citing both halves of a
pair? Over 1,530,134 eligible pairs the base rate is 1 in 90,007. The corpus
sits at a median 89.3° (quartiles 87.3–90.4); the hits sit at a median 72.7°,
all 17 below 85° where only 14.9% of pairs live, and 13 below 75° where 3.0%
do.

**The label was rebuilt on 2026-09-22.** The first version credited a theorem
with citing `Foo.bar` when the line said `Foo.bar_baz`, counted hits inside
`def` bodies and docstrings, and counted a theorem's own header as a citation
of itself. [`build-forward-label.py`](scripts/build-forward-label.py) replaces
that uncommitted procedure with whole-name matching inside theorem and lemma
bodies, and CI checks the committed label against it. 22 positives became 17
and the AUC went from 0.958 to 0.973; the vocabulary baseline fell from 0.764
to 0.691. The forward-test README carries the before-and-after table.

**Read the AUC, not the band lift.** The 17 positives are not 17 independent
observations: 24 theorems carry all of them, `FiniteField.card` appears in
four.
[`analyze-forward-independence.py`](scripts/analyze-forward-independence.py)
takes the clustering apart. The AUC does not move — 0.977 on a vertex-disjoint
subset where no theorem is used twice, 0.973 after dropping every pair that
touches a seed family, 0.975 after dropping the `Complex.exp*` hub outright, and
0.971–0.980 across all 24 leave-one-endpoint-out refits. Against a cluster null
that substitutes each endpoint for a random theorem while preserving exactly
which endpoints pair with which, the null sits at 0.499 ± 0.075 and the observed
0.973 does not occur in 5,000 draws. The 160× lift in the 45–55° band is the
fragile number: it rests on four pairs, three of them sibling lemmas about the
same object, and dropping that one hub leaves one.

## What this does not show

- **No connection has been discovered.** Every link measured here is one a human
  already made. Recognising them is a precondition, not the result.
- The band edges in the forward test were fixed with the table visible, and the
  band that got reported, 45–55°, is narrower than the 40–55° that was posted to
  issue #1 at 15:05:53Z before the analysis was committed at 15:31:00Z. 17
  positives is a thin base, and the band lift does not survive dropping a hub
  theorem. The AUC does; that is the number the claim rests on.
- **Vocabulary does some of the work.** Token overlap between two theorems'
  state texts predicts the same 2026 label at AUC 0.691 on its own
  ([`vocabulary.json`](results/phase-1-recognition/mathlib-forward-v1/vocabulary.json)): connected
  pairs share 14.1% of their state vocabulary against 7.7% for an average
  eligible pair. The angle's 0.973 is well clear of that, and 4 of the 17 hits
  share under 5%, but "still separates where words give little" is the
  defensible claim, not "vocabulary-independent". The α-rename arm sharpens this
  rather than settling it: stripping names costs the lexical baseline 14 points
  (0.691 → 0.547) without costing the angle anything, so the angle is not riding
  on *naming*, but 0.547 is still above chance and constants are untouched.
- **It is not a subfield detector, which was the most plausible deflation.**
  Same area means same people working in the same active corner of Mathlib, and
  those pairs get connected later anyway — so the angle could predict the label
  without understanding anything. Measured
  ([`area-control.json`](results/phase-1-recognition/mathlib-forward-v1/area-control.json)): the
  angle predicts "same area" at only 0.656, "same area" predicts the 2026 label
  at only 0.632, and on cross-area pairs alone — where the confound cannot
  operate — the angle still scores **0.972 on 11 hits** against 0.973 overall.
  That rules out this story, and the α-rename effect — a different story, and
  the one that stayed open longest — is ruled out separately below.
- **Superseded by phase 2**, which rebuilt the label from Lean's dependency
  graph and found 53 positives where grep found 17. As written in phase 1: the
  forward label is `git grep` over full declaration names, so it misses
  citations under an `open` namespace, misses a target renamed since 2024, and
  does not check that a citation is load-bearing. Misses attenuate; but the
  first version of this label showed that a loose matcher inflates, so a grep
  label is not conservative by default. Real dependency data would replace
  the heuristic.
- **Exact invariance is false; discriminative invariance holds.** The encoder
  is not name-blind, and never was: under α-renaming the centroids move a median
  **20.0°** (quartiles 15.2–26.3, max 69.5°), with only 31 of 1,797 theorems
  left under 1°. The 8/8 falsification in
  [encoder-invariance-v1](results/phase-1-recognition/encoder-invariance-v1/README.md) and the 48.1°
  single-state probe in [issue #2](https://github.com/sanaani/noema/issues/2)
  are both confirmed. What they do not imply is what was feared: everything
  moves *together*, so the arrangement the three tests read is preserved and all
  three survive ([rename-control-v1](results/phase-1-recognition/rename-control-v1/README.md)).
  Distances here still must not be read as absolute relatedness — only as rank.
- **The statement-embedding null is not a like-for-like comparison.** Five
  encoders on theorem statements put the four prespecified targets nearer than 98.8–99.2% of
  background controls — they pass the bar the tests above are scored against.
  What they fail is a *lexical* control: against four word-matched decoys the
  target was nearer only 12.5–18.8% of the time, so the proximity tracks
  wording
  ([semantic-encoder-evaluation-v1](results/phase-1-recognition/semantic-encoder-evaluation-v1/README.md)).
  Betweenness and the forward test have never been put through *that* control,
  so "statements fail, states succeed" is not established — the two were held to
  different bars. The α-rename arm closes part of the gap and not all of it: it
  ablates names and measures what the ablation cost the lexical baseline, which
  is a real lexical screen, but it is not the word-matched-decoy construction
  the statement encoders failed. Building those decoys for proof states remains
  the obvious next screen, and it has not been run. The decoys the statement
  encoders faced were also sibling lemmas (`Real.cos_add` for `Real.sin_add`),
  which are mathematically as well as lexically near, so "proximity tracks
  wording" is the stronger of two readings of that result.
- **The Lean certificate is on the expression, not the text.** The α-rename
  arm proves that each renamed goal differs from the original only in binder
  names as an `Expr`. The encoder reads pretty-printed text, and the
  protocol records that instance markers (`inst✝`) are lost in the renamed
  printing. Nothing certifies the two texts differ only in names; the
  structural certificate is one level below the input.
- **Betweenness and the replication have no prespecified pass mark, and the
  rename arm's versions of them were not prespecified either.** The run plan
  named betweenness the decision point without saying what would count as
  passing; `rename-control-v1/protocol.md` fixes a rule for the forward AUC
  only. The bridge and replication results on the renamed arm were produced
  by running `analyze-state-bridge.py` against each arm's vectors, not by
  `analyze-rename-control.py`, and were committed ten minutes after the
  verdict.
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
results/                 findings and precompiled data, grouped by research phase
  phase-1-recognition/   CLOSED. Can the geometry recognise links humans already made?
    link-graph-v1/       206,889 theorem->dependency edges from pinned Mathlib; the
                         bridge-triple scan; the Lean elaborators that produced them
    state-bridge-v1/     the replication and betweenness tests
    mathlib-forward-v1/  the 2024 -> 2026 forward test, its centroids, and the
                         independence and vocabulary checks on it
    rename-control-v1/   all three measurements rerun with every binder and
                         hypothesis renamed in Lean under a structural
                         certificate; the arms, the prespecification, the verdict
    bridge-expansion-v1/ the six (A, B, bridge) families: Lean checks that each
                         theorem exists and is sorry-free; the bridge relation
                         itself is a human judgement, not a certified one
    bridge-conjecture-v1/ a machine-proposed, machine-checked bridge — proposed by
                         the earlier statement ranker, not by the state geometry
    state-object-v1/     the 128-object archive the first AUC 0.786 came from
    historical-connections-v1/  the initial-State pilot that seeded four of the
                         six families; bridge-expansion-v1 added the other two
    encoder-*/, semantic-*/, state-consistency-v1/
                         what the encoder does and does not do: α-rename
                         invariance, a five-encoder comparison, certified
                         structural capture, and the statement-embedding null
  phase-2-dependency-labels/  CLOSED. An exact label, then a corpus nobody chose.
    link-graph-2026-v1/  the 2026 dependency graph (281,359 theorems) and the
                         exact label scored on phase 1's corpus: 53 positives, 0.898
    unseeded-corpus-v1/  350 files by seed, 11,489 theorems, 5,200 positives, 0.709;
                         the residual and state-source tests; every capture artifact
  phase-3-doubled-corpus/  CLOSED. 24,916 theorems, 23,583 positives; settles the
                         hard subset at 3.9 sigma, pre-registered before capture
  phase-4-trained-encoder/  a self-supervised encoder trained on the corpus's own
                         2024 texts beats ReProver's AUC by 0.09 on the hard subset
  phase-5-conjecture-map/  can the 2024 map place future bridging theorems? weakly
                         (0.568), and word overlap places them better
viewer/    the centroid cloud flattened onto a globe two ways, with the figures that
           say how much each flattening lies; built by scripts/project-centroids-sphere.py
scripts/   the pipeline, in order: scan -> filter -> select -> capture -> encode -> analyse
           shared across phases and phase-agnostic: a script asks for
           result_path("link-graph-v1/edges.jsonl.gz") and never names a phase.
           bootstrap-*/setup-* provision a pinned host or encoder for a rerun;
           audit-/evaluate-/verify-* regenerate one archived result each
src/noema/ encoders, typed state capture, replay; paths.py owns the phase layout
```

Each phase directory carries its own README: the question it asked, what it
found, what it does not establish, and what it hands to the next phase.
Phase 1 is closed, so its numbers do not move. Code is deliberately not
organised by phase, so a phase 2 script reading phase 1's centroids needs no
phase awareness.

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
.venv/bin/python scripts/build-forward-label.py --check     # the 2026 label's citations are whole names
.venv/bin/python scripts/analyze-state-bridge.py            # needs the vectors, see below
```

Phase 2's analyses take the unseeded corpus's committed centroids (62.8 MB) and
label as arguments; the residual, state-source and independence runs need about
4 GB of memory, which is why `scripts/run-analysis-aws.sh` exists:

```bash
U=results/phase-2-dependency-labels/unseeded-corpus-v1
.venv/bin/python scripts/analyze-forward-residual.py --centroids $U/centroids.npz \
    --connectors $U/new-connectors.json --states $U/states-augmented.jsonl.gz \
    --selection $U/selection-modules.json.gz --edges results/phase-1-recognition/link-graph-v1/edges.jsonl.gz
.venv/bin/python scripts/project-centroids-sphere.py        # rebuilds viewer/data.js, ~90 s
```

The α-rename control compares two arms of one encode, so it needs that encode's
vectors (517 MB, not committed) rather than the centroids:

```bash
.venv/bin/python scripts/analyze-rename-control.py \
    --arms outputs/rename-control-v1/arms \
    --vectors outputs/rename-control-v1/vectors/reprover-embeddings.npz
```

Its two exported centroid files *are* committed
([`centroids-original.npz`](results/phase-1-recognition/rename-control-v1/centroids-original.npz),
[`centroids-alpha.npz`](results/phase-1-recognition/rename-control-v1/centroids-alpha.npz)), so the
forward, vocabulary and independence scripts can be pointed at either arm with
`--centroids` without rebuilding anything.

The first six need nothing but the repository, and CI runs all six. The five
that read `results/phase-1-recognition/mathlib-forward-v1/centroids.npz` use it as 1,797 unit
centroids, 9.9 MB, the only input they need from the encode, exported by
`scripts/export-forward-centroids.py` and checked against the full vectors by
`tests/test_forward_centroids.py` wherever those vectors are present.

`analyze-state-bridge.py` is the one that cannot: its shuffled control permutes
the vector/text assignment, so it needs every state vector, and
`outputs/state-bridge-v1/vectors/reprover-embeddings.npz` is 272 MB and
therefore not committed. Everything upstream of it is:
`results/phase-1-recognition/state-bridge-v1/states-augmented.jsonl.gz` holds the 99,275 captured
states, so the Lean capture — the long pole, a CPU host against Lean 4.9.0 and
Mathlib `f0957a7` — does not have to be repeated. Rebuild the vectors with

```bash
python scripts/build-encode-inputs.py --states results/phase-1-recognition/state-bridge-v1/states-augmented.jsonl.gz ...
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

2,128 files against the 414 here (`git ls-files | wc -l`). `a44f244` is the
prune itself: 1,743 files, 1,663,285 deletions, no new work.

Two things were never committed and cannot be recovered from the history: the
script that expanded the 82 seed names into the 2,000-theorem target list
(its output was committed, and the rule is recorded in
`docs/state-bridge-run-plan.md`), and the first procedure that turned the
2026 grep hits into a label (replaced by `scripts/build-forward-label.py` on
2026-09-22, which found and fixed its matching errors). The Lean sweep that
produced `results/phase-1-recognition/link-graph-v1/edges.jsonl.gz` names its Mathlib pin only in
`scripts/setup-state-object-host.sh` and the READMEs; `Deps.lean` itself just
says `import Mathlib`.

## License

[Apache-2.0](LICENSE), matching Lean and Mathlib, so the pinned Mathlib, the
vendored `REPL` fork and this work all sit under one license.

Imported material keeps its own terms and is not relicensed here: the Lean REPL
carries its original Apache-2.0 headers, the ReProver export is the authors',
and `results/phase-1-recognition/state-object-v1/source-manifests/` retains the publisher notices
for everything it archived.
