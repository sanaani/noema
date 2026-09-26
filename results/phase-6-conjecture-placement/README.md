# Phase 6 — can the map say where a theorem goes, and can one be written there?

**Pre-registration (draft).** Everything in this file is written and committed
before any 2024 statement outside the corpus is printed, before any predictor
is trained, and before any candidate theorem is written. Results go in a
section appended below; nothing above that section changes.

## Why

Phase 5 found that the 2024 map marks where cross-area theorems will appear,
weakly (AUC 0.568), and that plain word overlap does it slightly better
(0.590). Three loose ends came out of it, and one question was queued before
it:

1. **Placement.** Nearest-neighbour mixing is a blunt score. A model trained
   to put a theorem where it belongs, given the lemmas it uses, is the sharper
   version of the same question. Queued as phase 6 in
   `docs/phase-6-jepa-plan.md`.
2. **The bridge label.** Several of phase 5's top "bridges" qualify only
   through lemmas that nearly every proof in an area uses (`Category.comp_id`,
   `Nat.cast_one`). That label may be hiding or inflating the signal.
3. **Words and geometry together.** Words won phase 5. That does not mean the
   two see the same thing.
4. **Writing theorems.** Five phases have measured the map. None has tried to
   produce a theorem with it, which is the goal behind all of them.

Phase 6 runs all four, each with its own pre-registered test.

## Shared inputs

- **Encoder B**, from phase 4, frozen throughout. Nothing in this phase
  changes its weights.
- **The 2024 graph**: `phase-1-recognition/link-graph-v1/edges.jsonl.gz`,
  206,889 theorems at Mathlib `f0957a7`, with each theorem's direct
  dependencies.
- **2024 statements for every theorem in that graph**, printed by phase 1's
  `InitialGoals.lean` at Lean 4.9 / `f0957a7`, and encoded by B exactly as
  phase 5 encoded its statements (`scripts/encode-b.py`: first 512 tokens,
  mean-pooled, normalised). Theorems that fail to print are dropped and
  counted.
- **Phase 5's connectors, labels, 2026 statements and B vectors**, unchanged.
- **Bootstrap**: 2,000 draws, resampling connectors by their 2026 source
  file, as in phase 5. Intervals are 95%.
- Seed for everything drawn or trained here: **20260928**.

## Part 1 — learned placement (the queued phase 6)

### The predictor

A permutation-invariant set model, because the order of a proof's lemmas is
not information this project uses:

| | |
|---|---|
| input | B vectors of the theorems a theorem cites, 2024 statements; at most 64, keeping the rarest by 2024 in-degree |
| model | Deep Sets: shared MLP 256→512→512 (GELU), mean-pool and max-pool concatenated, MLP 1024→512→256, L2-normalised |
| target | B vector of the theorem's own 2024 statement |
| loss | 1 − cosine |
| training | every 2024 theorem citing at least one other 2024 theorem; AdamW lr 1e-3, batch 256, 20 epochs |
| held out | 5% of 2024 source files, drawn by seed, for the loss curve and choosing the epoch only |

One architecture and one training run. Nothing is tuned against any 2026 data.

### The test

For each of phase 5's 10,368 connectors, the input is the set of theorems it
cites that exist in the 2024 graph, not only corpus theorems. The target is
its B vector from its 2026 statement.

A method is scored by where it puts the true statement among all 10,368
connector statements: its **percentile rank** (1 is top, 0.5 is chance). **P**
is the mean over connectors.

| method | how it ranks the candidates |
|---|---|
| **PRED** | cosine to the predictor's output |
| **AVG** | cosine to the normalised mean of the cited theorems' vectors |
| **WORDS** | Jaccard between the union of the cited theorems' identifier sets (2024 statements) and each candidate's identifier set, with `analyze-forward-vocabulary.py`'s tokenizer; ties take their average rank |

### H1 — does learning beat averaging?

P(PRED) − P(AVG), paired bootstrap.

| outcome | verdict |
|---|---|
| interval above 0 | **learned placement beats averaging** |
| contains 0 | **no measurable difference** |
| below 0 | **averaging does better** |

Prediction: learned placement beats averaging.

### H2 — does it beat words?

P(PRED) − P(WORDS), paired, with the same three verdict rows (with "words" in
place of "averaging"). Prediction: no measurable difference.

Recall at 10 (the share of connectors whose true statement ranks in the top
10 of 10,368) is reported for all three methods.

## Part 2 — a cleaner bridge label

A corpus theorem is **generic** if more than 200 theorems cite it in the
2024 graph. The threshold is the upper bound of phase 3's rare-lemma rule, not
a new choice.

A **clean pair** is an eligible pair (phase 3's definition) with neither
endpoint generic. Connectors are re-classed from clean pairs only: **clean
bridge** joins at least one clean cross-area pair; **clean within** joins clean
pairs, all same-area; the rest are excluded. The counts are fixed before any
score is computed and reported with the results.

### H3 — does mixing mark clean bridge spots?

AUC of phase 5's M, clean bridges against clean within, with phase 5's H1
verdict rows (≥ 0.60 with interval above 0.5 → locates bridge spots; interval
above 0.5 → real but weak; contains 0.5 → not supported; below 0.5 →
contradicted). Prediction: real but weak.

Reported alongside: AUC(M) − AUC(M_V) on clean labels (paired), and citation
count's AUC on clean labels.

## Part 3 — words and geometry together

A combined score is the mean of the two scores' percentile ranks within the
test set. There is no weighting and nothing is fitted.

### H4 — does combining beat words alone in placement?

P(PRED+WORDS) − P(WORDS), paired, with the same three verdict rows as H1.
Prediction: combining beats words.

Reported alongside: AUC(M+M_V) − AUC(M_V) on phase 5's labels and on the
clean labels.

## Part 4 — writing theorems (pilot)

### The pairs

The pool is hard-subset corpus pairs (cross-area, vocabulary under 5%,
eligible) with neither endpoint generic, that **no 2026 theorem cites
together**. These are connections Mathlib has not made.

| arm | pairs |
|---|---|
| **TOP** | the 40 pairs with the highest cosine between their B statement vectors |
| **RANDOM** | 40 pairs drawn by seed from the same pool, excluding TOP |

The 80 pairs are shuffled together. The writer never sees which arm a pair
came from.

### The writer

Claude, run as a fresh subagent per pair with one fixed prompt, archived with
every output. It gets the two lemmas' names and their 2026 statements and is
asked for up to three Lean 4 theorems that genuinely need both, each with a
proof. After each attempt it gets Lean's error messages back, up to three
repair rounds. It is not told the pair's score, arm or area.

### The checker

Lean at Mathlib `09712d48`, the 2026 version. A candidate is a **hit** only
if all of these hold:

1. it compiles with no `sorry` and no new axioms;
2. its proof term cites both endpoints, by `Deps2026.lean`'s rule;
3. it is not already in Mathlib: `exact?` does not close the statement in 60
   seconds.

### H5 — does ranking help writing?

The share of pairs with at least one hit, TOP against RANDOM, one-sided
Fisher exact test.

| outcome | verdict |
|---|---|
| p < 0.05 | **the ranking points at writable theorems** |
| otherwise | **no measurable difference at this size** |

With 40 pairs an arm this is a pilot. Only a large difference can register.
Prediction: TOP has more hits, but not significantly.

Reported: every hit in full, the number of candidates written and compiled per
arm, and a blind 0–2 interest rating of each hit, given by a separate Claude
subagent with a fixed rubric (0 = restates a lemma, 1 = routine combination,
2 = something a Mathlib reviewer might merge) and without the arm label. Steve
may rate them too, also blind.

## What is out of scope

- Training or fine-tuning B or any writer.
- Any second predictor architecture, threshold, k or combination rule.
  Anything suggested by the results is reported as exploratory in its own
  section.
- Submitting anything to Mathlib.

## Budget

- One CPU worker (m6i.4xlarge), self-terminating, to print about 207,000
  2024 statements with Lean 4.9. Estimated $3–6.
- Encoding with B and training the predictor run locally on CPU.
- The Lean checks for part 4 run locally if Mathlib `09712d48` installs from
  its cache, otherwise on one CPU worker (about $5).
- The writer runs as Claude Code subagents: no API key and no AWS.
- AWS ceiling: $25. Every role, security group, instance and task object is
  torn down and the teardown verified.

---

## Results

*Appended after the runs. Nothing above this line changed.* Parts 1–3 are
added below when the 2024 statement encode finishes. Part 4 is complete.

### Part 4 — writing theorems (pilot)

Numbers from `results/pilot.json`, written by `scripts/score-phase6-pilot.py`.
Every check is in `pilot/checks.jsonl`, the blind ratings in
`pilot/ratings.json`. The arm key was hashed before writing
(`pilot/arm-key.sha256`) and published only after the ratings were in; it
matches its hash.

| | TOP | RANDOM |
|---|---:|---:|
| pairs | 40 | 40 |
| pairs with at least one hit | **40** | **40** |
| checks run | 81 | 81 |
| checks that compiled | 68 | 60 |
| hits (candidates passing all three rules) | 67 | 51 |
| hits rated 2 (worth merging) | 0 | 0 |
| hits rated 1 (routine combination) | 42 | 10 |
| hits rated 0 (restates or glues) | 25 | 41 |

**H5: no measurable difference at this size** (40/40 against 40/40, one-sided
Fisher p = 1). The prediction was "TOP has more hits, but not
significantly". The outcome is weaker than that: the hit rule does not
separate the arms at all, because every pair in both arms produced one. The
rule was too easy. A conjunction of the two lemmas, or a rewrite chain that
names both, compiles, cites both endpoints and defeats `exact?`. That is a flaw
in the test's design, fixed in advance and not changed here, not a finding
about the map.

**No hit is worth merging.** The blind rater gave 0 of 118 hits a 2.

### Deviations

- **Pool.** Before any writing, the pool gained one condition the
  pre-registration does not list: both endpoints must exist by name in the
  2026 graph. The first draw had 17 of 80 pairs with an endpoint renamed or
  removed by 2026. Those pairs could not be written against Mathlib
  `09712d48`, and a hit must cite both endpoints there. The condition is in
  `scripts/select-phase6-pairs.py` and was committed with the pairs, before
  the first writer ran.
- **Checker axiom rule.** With `open Classical`, Lean prints the choice axiom
  as `choice`, not `Classical.choice`. The checker read that as a forbidden
  axiom. Three RANDOM checks (pairs 36 and 49) failed on this alone, and both
  writers repaired it within budget, so every pair still ended with a hit and
  H5 is unaffected.
- **Checker environment.** Lean ran on one m6i.4xlarge worker, not locally:
  `import Mathlib` at `09712d48` does not fit in the laptop's memory. This is
  one of the two options the budget allowed.
- **Encode.** The first 2024 encode was killed for lack of memory while
  saving: a fixed-width array of 206,845 texts, the longest 30,692 characters,
  needs about 25 GB. `encode-b.py --texts-json` now writes the texts to a
  separate file. The vectors are computed exactly as before.

### Exploratory, not pre-registered

- **Quality differs by arm.** Pairs whose best hit was rated at least 1: TOP
  25 of 40, RANDOM 9 of 40 (one-sided Fisher p = 0.0003). This was chosen
  after seeing the ratings. TOP pairs also share endpoints heavily
  (`FreeRing.coe_surjective` is in nine of them; `Real.arctan_one` and Stirling's limit are in four each),
  so the 40 TOP pairs are far fewer than 40 independent draws. It is a lead,
  not a result.
- **What TOP's closest pairs look like.** The highest-cosine unjoined hard
  pairs are near-duplicates in different areas: `Nat.bot_eq_zero` with
  `Ordinal.bot_eq_zero`, `Int.csInf_empty` with `Ordinal.sInf_empty`,
  surjectivity lemmas with surjectivity lemmas. B finds statements with the
  same *shape*. Two such lemmas combine easily, which explains more
  compilations and more rated-1 hits. It is also why nothing reaches a 2:
  combining two same-shaped facts rarely says anything new.
- **The best TOP hits** (rated 1) are small real results. Examples: e < π from
  `Real.exp_one_lt_d9` and `Real.arctan_one`; n!/(n/e)^n → ∞ from Stirling's
  limit; |z|² sublevel sets in ℂ are bounded; a finite sum of
  `smoothTransition` values is positive iff some input is. Nothing here is a
  new theorem in the mathematical sense.

### Cost and teardown

Two m6i.4xlarge workers: the 2024 statement print (about 10 minutes) and the
Lean checker (about 30 minutes). Both instances, their IAM roles and instance
profiles, their security groups and their S3 task and result objects were
deleted, and the deletion was verified. The writers and the rater ran as
Claude Code subagents.
