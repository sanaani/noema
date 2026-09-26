# Phase 7 — can a model trained on 2024 choose which lemmas to combine?

**Pre-registration.** Everything in this file is written and committed before
any picker is trained, before any Phase 7 score is computed on a test pair,
and before any candidate theorem is written. Results go in a section appended
below; nothing above that section changes.

## Why

Phase 6 solved half of a conjecture tool. Told which 2024 lemmas a new theorem
will use, a small model trained on 2024 Mathlib puts the theorem's statement in
the top 6% of 10,368 on average. The other half was left open: *choosing which
lemmas to combine*. Part 4 of Phase 6 suggested the map's nearest pairs are the
wrong choice. They are look-alikes (`Nat.bot_eq_zero` with
`Ordinal.bot_eq_zero`), which combine easily and say nothing new.

The project exists to ask which two theorems should be connected but have not
been yet. Phase 7 asks it directly, three ways:

1. **Part 1.** Several pair-pickers, trained on 2024 only, race to predict the
   hard-subset pairs Mathlib joined by 2026. They are compared against baselines
   that need no learning.
2. **Part 2.** Phase 6's placement predictor is used as a judge of novelty.
3. **Part 3.** Theorems are written from the winner's pairs, from Claude's
   picks, from the nearest pairs and from random pairs. A stricter hit rule is
   used, and the pre-registered headline is the quality of the results.

Part 3 is the headline test because better theorems are the goal. Part 1 is
the larger and better-powered test, and it decides which picker Part 3 uses.

## Shared inputs

- **Encoder B**, from Phase 4, frozen throughout.
- **2024 statement vectors**: B's vectors of every 2024 statement, from Phase 6
  (`b-statements-2024.npz`, 206,845 of 206,889 theorems).
- **The 2024 graph**: `phase-1-recognition/link-graph-v1/edges.jsonl.gz`, Mathlib
  `f0957a7`. **The 2026 graph**: `link-graph-2026-v1/edges-2026.jsonl.gz`,
  Mathlib `09712d48`.
- **The corpus**: Phase 3's union of 24,916 theorems, with Phase 3's pair
  definitions unchanged. A pair is **eligible** if its endpoints share no rare
  2024 lemma. It is **hard** if it is cross-area and its state-vocabulary
  Jaccard is under 5%. It is a **positive** if a 2026 connector cites both
  endpoints.
- A theorem is **generic** if more than 200 theorems cite it in 2024 (Phase 6).
- **Co-cited in 2024** means some 2024 theorem cites both.
- **The 2024 citation graph** used by the pickers and baselines has one node per
  2024 theorem holding a vector. Its edges are "theorem cites theorem" between
  such nodes, taken as undirected where a method says so.
- **Bootstrap**: 2,000 draws, pigeonhole endpoint bootstrap (Phase 3's H3,
  Phase 4's H1): endpoints resampled, a positive weighted by the product of
  its endpoints' multiplicities. Intervals are 95%.
- Seed for everything drawn or trained here: **20260930**.

## Part 1 — the picker race

### The test population

Every hard pair of the corpus with neither endpoint co-cited with the other
in 2024 and both endpoints holding a 2024 statement vector. Pairs already
co-cited in 2024 are connections that were already made, so they are removed
from positives and negatives alike. Counts are fixed by
`scripts/build-phase7-pairs.py` before any picker is trained, and reported
with the results.

Each method gives every pair a score. A method's **AUC** is the mean, over
positives, of the share of negatives in the population it scores below that
positive. Ties count half. Every negative in the population is scored; nothing
is sampled.

### Training data common to every picker

Every picker learns from the 2024 graph only. No 2026 data is read before the
analysis.

- A **training theorem** is a 2024 theorem citing at least two theorems that
  hold a vector. Its **cited set** is those theorems, capped at 64, keeping the
  rarest by 2024 in-degree (Phase 6's rule).
- **Held out**: 5% of 2024 source files, drawn by seed, used for the loss curve
  and to choose the epoch only.
- One architecture per picker and one training run each. Nothing is tuned.
  Optimiser AdamW, learning rate 1e-3, 20 epochs, keeping the epoch with the
  lowest held-out loss, unless stated otherwise below.

### The pickers

| picker | model | trained to | pair score |
|---|---|---|---|
| **GNN** | 2-layer GraphSAGE (mean aggregation, hidden 256, GELU, output 256) over the undirected 2024 citation graph. Input: B vectors. | predict pairs a theorem newly co-cites (below) | dot product of the two output vectors |
| **GNN-noB** | the same, with input the log in-degree, log out-degree and a learned 32-d embedding of the Mathlib area in place of B | the same | the same |
| **JEPA** | Phase 6's Deep Sets architecture, predicting a *hidden* cited lemma's B vector from a random subset of the others (context size uniform over 1 to n−1); loss 1 − cosine | fill in a hidden lemma | mean of cos(f({a}), b) and cos(f({b}), a) |
| **JEPA-multi** | the same, with 5 output heads; loss 0.95 × the best head's loss + 0.05 × the mean over heads | the same | the same, taking the best head |
| **CLASSIFIER** | MLP on [a + b, a ⊙ b, \|a − b\|] of the B vectors, 768 → 512 → 256 → 1, GELU | yes/no, binary cross-entropy | the logit |
| **ENSEMBLE** | mean percentile rank of GNN, JEPA, JEPA-multi and CLASSIFIER over the test population. Nothing is fitted. | — | — |

**GNN training without leaks.** The test asks for pairs *not* co-cited in
2024. If a GNN is trained on co-cited pairs while it can see the theorem that
co-cites them, it learns to spot that shared citer, and that signal is absent
from every test pair. So the 2024 training theorems are split by source file:

- 90% are **message-passing** theorems, whose citation edges form the graph the
  GNN aggregates over;
- 10% are **supervision** theorems. Their co-cited pairs that are *not* also
  co-cited by any message-passing theorem are the positives.

The negative for each positive keeps its first endpoint and takes a second
drawn uniformly from all theorems cited in 2024. At test time the GNN
aggregates over the whole 2024 graph. The held-out 5% of files is drawn from
the supervision files.

**CLASSIFIER's negatives.** Each step samples a training theorem uniformly,
then a pair (a, b) from its cited set uniformly, so a theorem citing 60
lemmas does not outweigh one citing 3. Each positive gets three negatives,
each keeping a:

1. **random**: b′ uniform over all theorems cited in 2024;
2. **look-alike**: b′ uniform among a's 50 nearest theorems by B cosine;
3. **popularity-matched**: b′ uniform among theorems in the same 2024
   in-degree decile as b.

A negative that happens to be co-cited with a in 2024 is redrawn. An epoch is
one pass over the training theorems.

### Baselines

| baseline | score |
|---|---|
| **NEAREST** | cosine between the two 2024 statement vectors (Phase 6's TOP rule) |
| **POPULAR** | log(1 + in-degree) summed over the two endpoints, 2024 |
| **GRAPH** | Adamic–Adar on the undirected 2024 citation graph: the sum over common neighbours z of 1 / log(degree of z) |
| **WORDS** | Jaccard of the identifier sets of the two 2024 statements, with `analyze-forward-vocabulary.py`'s tokenizer |

### H1 — does any picker beat the best baseline?

For each of the five primary pickers (GNN, JEPA, JEPA-multi, CLASSIFIER,
ENSEMBLE), the statistic is its AUC minus the highest baseline AUC, positive by
positive, with the pigeonhole bootstrap. The one-sided p is the share of
draws at or below 0. Holm's correction at 0.05 is applied across the five.

| outcome | verdict |
|---|---|
| at least one picker passes Holm | **a 2024 picker beats every baseline** (each passing picker named) |
| none passes, the best picker's interval contains 0 | **no picker beats the baselines** |
| every picker's interval is below 0 | **the baselines do better** |

**The winner**, which Part 2 and Part 3 use, is the passing picker with the
highest AUC. If none passes, it is the picker with the highest AUC, and Part 3
is reported with that caveat.

Prediction: GNN passes. JEPA-multi is the best picker that uses no graph.
GRAPH or POPULAR is the strongest baseline.

### H2 — does the geometry add anything to the network?

AUC(GNN) − AUC(GNN-noB), paired bootstrap. This is the one number in Phase 7
that answers the project's founding question.

| outcome | verdict |
|---|---|
| interval above 0 | **the geometry adds to the citation network** |
| contains 0 | **no measurable difference** |
| below 0 | **the geometry hurts** |

Prediction: the geometry adds.

### Reported, not tested

- Hits in the top 1,000, 10,000 and 100,000 of every method, with the counts
  expected by chance.
- Every method's AUC within bands of the pair's summed 2024 in-degree
  (quintiles of the population), so a picker that only learned popularity shows
  itself.
- Every method's AUC on the non-generic part of the population.
- **RERANK.** A cross-encoder is initialised from B's weights, with B's
  tokenizer and 6-layer Transformer. Its input is the two 2024 statements,
  each truncated to 255 tokens, joined by a separator. It is trained for one
  pass over 2,000,000 examples from CLASSIFIER's sampler (one positive and its
  three negatives count as four examples), with learning rate 3e-4 and batch
  64. It is scored in both orders and averaged. It is applied to each primary
  picker's top 10,000 test pairs, and the hits in the top 1,000 after
  reranking are reported against before. It cannot score the whole population,
  so it is not in H1.
- **Lean fit check.** For each primary picker's top 1,000 test pairs, Lean at
  Mathlib `f0957a7` asks whether A's conclusion unifies with one of B's
  explicit hypotheses, or B's with one of A's (universe levels and
  implicit arguments become metavariables; 5 s per direction). Hits among the
  pairs that pass are reported against hits among all 1,000.

## Part 2 — novelty from the placement predictor

Phase 6's placement predictor (`predictor.pt`, epoch 11) is fed the pair
{a, b}. It outputs p, a predicted statement vector.

- **Novelty** = 1 − the highest cosine between p and any 2024 statement other
  than a and b.
- **Reach** = 1 − max(cos(p, a), cos(p, b)).
- **NOVEL** = the mean of the winner's percentile rank, novelty's and reach's,
  within the winner's top 100,000 test pairs.

### H3 — does novelty help the winner find 2026's pairs?

Positives among NOVEL's top 10,000 minus positives among the winner's top
10,000, both within the winner's top 100,000. The interval comes from the
pigeonhole bootstrap over the positives in that 100,000. Verdict rows as H2,
with "novelty helps / no measurable difference / novelty hurts".

Prediction: no measurable difference. A theorem that is new and real is rarely
in the 2026 label, so novelty's payoff, if any, should show in Part 3.

## Part 3 — writing theorems

### The pool

As in Phase 6: hard corpus pairs with neither endpoint generic, not co-cited
by any 2026 theorem, and with both endpoints present by name in the 2026 graph.
Also not co-cited by any 2024 theorem, and not one of Phase 6's 80 pilot pairs.

### The arms (40 pairs each)

| arm | pairs |
|---|---|
| **WINNER+NOVEL** | pool pairs taken in order of NOVEL (computed over the winner's top 100,000 *pool* pairs), each kept only if it passes the Lean fit check at `09712d48` |
| **CLAUDE** | a fresh Claude subagent is shown 400 pool pairs drawn by seed (names and 2026 statements only) and picks the 40 most likely to yield a new, non-trivial theorem |
| **NEAREST** | pool pairs in order of B cosine (Phase 6's TOP, as a replication) |
| **RANDOM** | pool pairs drawn by seed |

Every arm takes pairs in its own order, skipping any pair that would put a
lemma in more than two of that arm's pairs, or that another arm has already
taken. Arms are filled in the order RANDOM, CLAUDE, NEAREST, WINNER+NOVEL, so
the arm most likely to overlap with others is filled last. The 160 pairs are
shuffled together. The arm key is hashed before writing and published only
after rating.

CLAUDE may pick pairs from the other arms, because the 2026 answers are
not involved in Part 3. It cannot take part in Part 1, because it has probably
read 2026 Mathlib.

### The writer and the checker

Phase 6's writer prompt, budget (three candidates, three repairs each) and
checker (Lean at `09712d48`), with the hit rule extended. A candidate is a
**hit** only if:

1. it compiles with no `sorry` and no axioms beyond `propext`,
   `Classical.choice` and `Quot.sound` (`choice` accepted under `open
   Classical`, Phase 6's fix);
2. its proof term cites both endpoints;
3. `exact?` does not close its statement in 60 s;
4. **new:** its conclusion, after all binders are introduced, is not a
   conjunction or an iff at the head (`And`, `Iff`);
5. **new:** `aesop` does not close its statement in 60 s.

The writer prompt states all five rules. The Phase 6 plan also proposed checking
that neither lemma is decorative, by removing it from scope. It is dropped:
Lean cannot remove a Mathlib lemma from scope for one check without rebuilding
the library. Rules 4 and 5 catch the glue that Phase 6 found.

### The rater

Phase 6's rater prompt and rubric (0 restates or glues, 1 routine combination,
2 worth merging), one fresh subagent, every hit shuffled, without the arm label.

A **human check**: 40 hits drawn by seed across all arms are rated blind by the
project owner on the same rubric. Agreement is reported as Cohen's weighted
κ. If κ < 0.4, the model ratings are reported but called unreliable.

### H4 (headline) — does the winner's selection produce better theorems?

The share of pairs whose best hit is rated at least 1, WINNER+NOVEL against
RANDOM, one-sided Fisher exact test.

| outcome | verdict |
|---|---|
| p < 0.05 | **the picker points at better theorems** |
| otherwise | **no measurable difference at this size** |

Prediction: the picker points at better theorems.

Reported alongside, not tested: the same comparison for CLAUDE, NEAREST and
WINNER+NOVEL against CLAUDE; hits, compiles and ratings per arm; every hit
rated 2, in full.

## What is out of scope

- Training or fine-tuning B (RERANK fine-tunes a *copy* of B for Part 1's
  reported rows only).
- Any second architecture, setting or combination rule for any picker.
  Anything suggested by the results is reported as exploratory in its own
  section.
- Triples of lemmas.
- Submitting anything to Mathlib.
- Learning from the writing results (Phase 8).

## Budget

- One GPU worker (g6e.xlarge): train the six models, score the test
  population, Part 2. About an hour. $3–6.
- One CPU worker with Lean 4.9 at `f0957a7`: Part 1's fit check. $2–4.
- One CPU worker with Lean at `09712d48`: Part 3's fit check and the checker.
  $5–8.
- Writers, Claude's picker and the rater run as Claude Code subagents: no
  API key and no AWS.
- AWS ceiling: $30. Every role, security group, instance and task object is
  torn down and the teardown verified.

---

## Results

*Appended after the runs. Nothing above this line changes.*

### Verdicts, parts 1 and 2

| test | pre-registered prediction | result | verdict |
|---|---|---|---|
| **H1** best picker − best baseline (AUC) | GNN passes | best picker ENSEMBLE 0.884 against POPULAR 0.959: **−0.076** [−0.099, −0.051]; every picker's interval is below 0 | **the baselines do better** |
| **H2** GNN − GNN-noB | the geometry adds | **+0.273** [+0.232, +0.317] | **the geometry adds to the citation network** (see the caveat below) |
| **H3** NOVEL − winner, positives in the top 10,000 | no measurable difference | 31 against 23: **+8** [−17, +34] | **no measurable difference** |

H1 went against the prediction: no picker passes, and every picker's
interval sits below zero. The strongest baseline was popularity, as
predicted, and it was far stronger than expected. The winner that Part 3 uses
is therefore the highest-AUC picker, ENSEMBLE, with the caveat the
pre-registration requires: it does not beat the baselines.

### Part 1 — the picker race

Numbers from `results/phase7.json` (`scripts/run-phase7.py`).

**The population.** 57,589,891 hard pairs are placeable and not already co-cited in 2024.
1,661 of them are positives, spread over 794 distinct endpoints. The rule removed
4,367 hard pairs that some 2024 theorem already cites together. 623 of those
were positives: 14% of them, against a base rate of 1 in 35,000 in the
population. A pair already joined in 2024 is very likely to be joined again,
and phase 4's 2,284 hard positives included them.

| method | AUC | AUC, non-generic | positives in top 1,000 | top 10,000 | top 100,000 |
|---|---:|---:|---:|---:|---:|
| **POPULAR** (baseline) | **0.959** | **0.949** | **12** | **93** | **690** |
| ENSEMBLE | 0.884 | 0.880 | 0 | 23 | 195 |
| JEPA-multi | 0.866 | 0.857 | 4 | 22 | 107 |
| CLASSIFIER | 0.852 | 0.837 | 0 | 8 | 66 |
| JEPA | 0.839 | 0.833 | 0 | 7 | 85 |
| GNN | 0.753 | 0.768 | 0 | 0 | 4 |
| NEAREST (baseline) | 0.732 | 0.736 | 0 | 1 | 18 |
| GRAPH (baseline) | 0.511 | 0.504 | 0 | 10 | 36 |
| GNN-noB | 0.480 | 0.497 | 0 | 0 | 0 |
| WORDS (baseline) | 0.417 | 0.418 | 0 | 1 | 2 |
| *chance* | 0.5 | | 0.03 | 0.29 | 2.9 |

In words: the single best predictor of which two lemmas a 2026 theorem will
combine is how popular both lemmas already are. Summing their log citation
counts ranks the true pair above 96% of the others. Every learned picker beats
the map's plain nearest-neighbour rule (0.732), and the best geometry-only
model, JEPA-multi, reaches 0.866. None comes close to popularity.

**Where the pickers do beat popularity** (reported, not tested): within
bands of equal popularity. Split the population into quintiles of summed 2024
in-degree, and popularity has little left to rank with inside a band:

| AUC within quintile of summed in-degree | 1 (least cited) | 2 | 3 | 4 | 5 (most cited) |
|---|---:|---:|---:|---:|---:|
| POPULAR | 0.541 | 0.643 | 0.586 | 0.595 | 0.918 |
| ENSEMBLE | 0.788 | 0.851 | 0.879 | 0.847 | 0.868 |
| CLASSIFIER | 0.820 | 0.867 | 0.902 | 0.820 | 0.833 |
| JEPA-multi | 0.781 | 0.865 | 0.858 | 0.834 | 0.841 |
| NEAREST | 0.531 | 0.559 | 0.615 | 0.709 | 0.722 |

Among pairs of equally popular lemmas, the learned pickers rank the true pair
above 79–90% of the others, where popularity manages 54–64% in four of the
five bands. So the pickers carry real information that popularity does not.
Across bands, most of the ranking comes from popularity itself. This was
chosen as a reported row in advance, but no test was fixed on it. It is the
lead phase 8 should test.

**The H2 caveat.** GNN-noB, with no map positions, scores 0.480, below chance.
Its input is popularity and Mathlib area, and every test pair is cross-area by
construction, so the area input actively misleads it. "The geometry adds" is
true as registered. It mostly measures the GNN-noB failure, not a strong GNN.
The GNN with map positions (0.753) is the weakest learned picker. JEPA and
CLASSIFIER, which never see the graph, both do better. In this design the
citation network did not help the geometry; popularity used directly did.

**RERANK** (reported): re-ranking each picker's top 10,000 by the
cross-encoder raises positives in the top 1,000 for every picker that had any
to find: ENSEMBLE 0 → 8, CLASSIFIER 0 → 6, JEPA 0 → 3, JEPA-multi 4 → 7 (GNN
had none in its top 10,000). Reading the two statements adds something the
frozen vectors lose. It still leaves every picker far below POPULAR's 12.

**Lean fit check, Part 1** (reported): of each picker's top 1,000, the share
where one lemma's conclusion unifies with an explicit hypothesis of the other
at Mathlib `f0957a7` is JEPA 38, JEPA-multi 51, CLASSIFIER 41, ENSEMBLE 29,
GNN 0. None of the pairs that fit is a positive. The fit filter selects pairs
that plug together, not the pairs 2026 Mathlib combined.

**Training** (`training` in `phase7.json`). Every model's held-out loss fell
and flattened. The chosen epochs were GNN 5, GNN-noB 12, JEPA 19, JEPA-multi
19 and CLASSIFIER 19 of 20. The GNN overfits after epoch 5, and its held-out
loss (0.59 against 0.69 for a coin flip) says it learned little from 81,373
supervision pairs. RERANK finished one pass of 2,000,000 examples at a running
loss of 0.377.

### Part 2 — novelty

**H3: no measurable difference**, as predicted. Within ENSEMBLE's top 100,000
test pairs (195 positives), re-ranking by NOVEL puts 31 positives in the top
10,000 against the winner's own 23, with interval −17 to +34.

### Checks

- **Reproduction.** The scoring and analysis ran twice on separate GPU
  workers from the same trained models (see Deviations). Every AUC agrees to
  within 3 × 10⁻⁹, every interval within 10⁻⁹, and every top-k count, H3 and
  the RERANK rows match exactly.
- **The smoke stage.** The worker first ran the whole pipeline on a slice
  (20,000 graph records, 2 million pairs, one epoch) and only then started the
  real run. The smoke numbers are not results.

### Part 3 — writing theorems

Numbers from `results/pilot.json` (`scripts/score-phase7-pilot.py`). Every
check is in `pilot/checks.jsonl` and the blind ratings are in `pilot/ratings.json`.
The arm key was hashed before any writing (`pilot/arm-key.sha256`) and published
after the model rating. It matches its hash.

**H4: the picker points at better theorems.** WINNER+NOVEL had 25 of 40 pairs
whose best hit was rated at least 1, against RANDOM's 6 of 40 (one-sided Fisher
p = 1.2 × 10⁻⁵). The prediction was right.

| | WINNER+NOVEL | CLAUDE | NEAREST | RANDOM |
|---|---:|---:|---:|---:|
| pairs | 40 | 40 | 40 | 40 |
| **pairs whose best hit is rated ≥ 1** | **25** | **27** | **20** | **6** |
| pairs with at least one hit | 40 | 40 | 40 | 40 |
| checks run | 92 | 55 | 63 | 64 |
| checks that compiled | 73 | 46 | 57 | 47 |
| hits | 48 | 43 | 52 | 42 |
| hits rated 1 (routine combination) | 31 | 28 | 27 | 7 |
| hits rated 0 (restates or glues) | 17 | 15 | 25 | 35 |
| hits rated 2 (worth merging) | 0 | 0 | 0 | 0 |

Reported alongside, not tested: CLAUDE against RANDOM, 27 against 6
(p = 1.6 × 10⁻⁶). NEAREST against RANDOM, 20 against 6 (p = 0.0008). WINNER+NOVEL
against CLAUDE, 25 against 27 (p = 0.76), no difference.

In words: all three ways of choosing pairs produce real combinations far more
often than chance. Random pairs from different areas share nothing, so a
writer can only glue them together, and 35 of their 42 hits were rated 0. The
learned picker is as good as Claude reading the statements, and neither is
clearly better than picking look-alike pairs. **No hit in any arm was rated 2**,
so none of the 185 theorems is a candidate for Mathlib.

**The stricter hit rule did its job only partly.** Rules 4 and 5 rejected many
candidates (`aesop` closed statements in every arm), and the writers adapted.
Some wrapped glue in forms the rules do not catch: an equality of pairs
`(x, y) = (x', y')` instead of a conjunction, an `if` whose condition uses one
lemma, or a hypothesis `aesop` cannot use. All 160 pairs still produced a hit,
so hits alone again separate nothing. The rating separates the arms.

**Human check: pending.** 40 hits drawn by seed (`score-phase7-pilot.py human`)
are waiting for the project owner's blind ratings. Until they are in, the
model ratings behind H4 are unchecked.

### What this establishes

- A picker trained on 2024 Mathlib, filtered by a Lean fit check, chooses
  lemma pairs that yield genuine combinations about four times as often as
  random pairs (H4).
- On predicting which pairs 2026 Mathlib joined, nothing learned beats
  popularity (H1). Within equal popularity, the learned pickers carry real
  information popularity lacks (reported).

### What it does not establish

- **That the map beats simpler choices.** Claude reading the statements does
  as well, and nearest pairs nearly as well. The comparison that shows skill
  is against RANDOM, and RANDOM is a weak control: pairs from different areas
  that share nothing.
- **Which part of WINNER+NOVEL does the work.** Its pairs passed three
  filters: the ENSEMBLE ranking, the novelty re-ranking and the Lean fit check.
  The fit check alone plausibly accounts for much of the effect, and no arm
  isolates it.
- **A new theorem.** Nothing reached a 2.

### Deviations

- **The part 3 candidate list was cut at 3,000 by the code, not the rules.**
  Only 35 of the top 3,000 WINNER+NOVEL pool pairs passed the fit check, too
  few to fill the arm. The pre-registration says to walk down the NOVEL order
  until the arm is full. The first GPU run had saved only 3,000 rows, so
  scoring and analysis were rerun on a second GPU worker from the same trained
  models, saving the whole order. The rerun reproduces every part 1 and part 2
  number (see Checks). The fit check then ran on the first 15,000 pairs, and
  the arm filled at pair 6,442.
- **Subagents read their prompts from a file.** The CLAUDE picker and the
  rater were each given one instruction: read one file holding the fixed
  prompt, filled in, and use no other tool. The writers were told the same,
  plus to run the checker. The prompts are unchanged; only the way they were
  delivered differs from Phase 6's inline text.
- **The rater's summary miscounted.** Its prose said 94 zeros and 91 ones. Its
  JSON, which is what is scored, has 92 and 93.
- **The checker gained `--smoke --endpoints`** to test it against real Mathlib
  before any pair existed. It does not log.
- **Fit check interpretation.** "Explicit hypotheses" was read as explicit
  binders whose type is a proposition, and conclusions were not unfolded
  (`forallMetaTelescope`, default transparency, as `apply` uses). The reasons
  are given in `scripts/phase7-fit.py`.

### Cost and teardown

Five AWS workers:

- a g6e.xlarge for training and scoring (about 20 minutes);
- a g6e.xlarge for the rescore (about 6 minutes);
- two m6i.4xlarge Lean workers, one at `f0957a7` for part 1's fit check (about
  15 minutes) and one at `09712d48` for part 3's fit check and all 274 checks
  (about 4 hours);
- none for encoding, which Phase 6 had already done.

Every instance, IAM role, instance profile, security group, and S3 task and
result object was deleted, and the deletion was verified. The writers, the
picker and the rater ran as Claude Code subagents.
