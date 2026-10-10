# Phase 27 — train the embedding on past surprising jumps

**Pre-registration.** Everything in this file is written and committed before
any Phase 27 number is computed. Results go in a section appended below;
nothing above that section changes.

**Approval.** Shaun approved a phase applying Dianoia's recipe (training the
encoder on far jumps) to Noema, with an AWS budget of $10, on 10/10/2026.
He approved H1 and H2 as written on 10/10/2026, before the data rebuild
finished and before any Phase 27 number existed.

## Why

Phase 26 found that an off-the-shelf sentence embedding
(`sentence-t5-base`) makes **worse** matchmaker lists than TF-IDF: 69 met
against 90, −21 [−42, −2]. It also forecast worse at 2011: within-route AUC
gain +0.095 against TF-IDF's +0.193.

The embedding was never told what a surprising jump looks like. The sister
project Dianoia (patents and papers) found that training an embedding on far
pairs only moved far-source retrieval from 52.6% to 77.7% top-10 on patents,
and from 20.0% to 36.5% on management papers. A few hundred pairs gave most
of the gain: Dianoia phase 15 reached 75.6% with 419 pairs and 77.7% with
1,676.

Phase 27 trains Phase 26's embedding on surprising jumps that happened
**before** the lists' training labels begin. It then asks two questions:
does training make better lists than the untrained embedding, and better
lists than TF-IDF?

Already seen before this file was written: all results of phases 11–26.

## Data (rebuilt)

Phase 11's data files are not on the machine that runs this phase, and the
run bucket holds no copies. They are rebuilt with Phase 11's code,
unchanged:

- **Papers:** arXiv OAI-PMH `set=math` (`run-phase11.py harvest`, run
  10/10/2026).
- **References:** joined from the OpenAlex parquet snapshot of 2026-09-23
  (`run-phase11.py snapshot`). This is the release Phase 11 used, still the
  newest on 10/10/2026.
- `W4285719527` is dropped, as in Phases 20–26.

arXiv adds and revises records, so counts may differ slightly from Phase 11's
597,860.

**Reproduction (reported, not tested):** `run-phase26.py`, unchanged, on the
rebuilt data, against Phase 26's published 90 met (TF-IDF, filter on) and 69
met (embedding, filter on). Every comparison below is made on the rebuilt
data, so drift changes no test.

## The trained embedding

**Base model:** `sentence-transformers/sentence-t5-base`, Phase 26's model.
It is kept because it was not trained on citation links (Phase 26's leakage
rule); a model that learned citing-to-cited closeness could already know
later jumps.

**Training pairs** come from Phase 25's surprising population at cutoff
**2000**: works with at least 5 citers, a target area with no citer, no
secondary-category citer and no citer in its 3 nearest areas, span ≥ 4.65
bits, and textbooks filtered out. A pair is a **jump** if at least one
target-area paper cites the work in 2001–2005.

For each jump:

- **Anchor:** an arriving paper, meaning a target-area paper of 2001–2005
  citing the work. At most 3 per jump, drawn at random.
- **Positive:** one of the work's citers up to 2000, drawn at random.
- **Hard negative:** a citer, up to 2000, of another work from the same home
  area, drawn at random.

The pairs are capped at 3,000, drawn at random. Text is title + ". " +
abstract, as in Phase 26.

Every training year is ≤ 2005. The lists' model learns from labels in
2006–2011 and is graded on 2012–2021, so the encoder sees no year either one
uses. **Sizing rule (fixed now):** if cutoff 2000 gives fewer than 300 pairs,
the cutoff moves to 1998, with arrivals in 1999–2005. The count is reported
either way.

**Training** is full fine-tuning (110M parameters), with
`MultipleNegativesRankingLoss` (in-batch plus the hard negative):

- learning rate 2e-5, batch 32, 2 epochs, warmup 10%;
- maximum 256 tokens, bf16;
- seed 20261017.

These are sentence-transformers' standard settings; nothing is tuned.

**Embedding:** papers up to 2021 are encoded exactly as
`embed-phase26.py` encodes them (fp16, unit-normalized, same batch). The
resulting vectors are the **trained** text model.

## Population, model, lists

Phase 26's settings, unchanged: Phase 25's surprising population at each
cutoff, Phase 25's logistic model with similarity as one feature, train at
2005 (label 2006–2011), apply at 2011, list the top 20 per area, and grade
**met** as at least 1 target-area citer in 2012–2021. The textbook filter is
on. Seed **20261017**.

There are three text models, each trained and listed separately:

- **TF-IDF** (Phase 25's);
- **embedding** (sentence-t5-base off the shelf, Phase 26's);
- **trained** (above).

## Tests

### H1 (primary) — does training on past jumps make better lists?

Met pairs in the **trained** lists minus met pairs in the **embedding**
lists, filter on, summed over areas. 95% interval from 10,000 bootstrap draws
over target areas, as Phase 26's H2.

| outcome | verdict |
|---|---|
| interval above 0 | **training helps** |
| interval contains 0 | **no measurable difference** |
| interval below 0 | **training hurts** |

Prediction: training helps.

### H2 — does the trained embedding beat TF-IDF?

The same, trained minus **TF-IDF**.

| outcome | verdict |
|---|---|
| interval above 0 | **trained beats TF-IDF** |
| interval contains 0 | **no measurable difference** |
| interval below 0 | **trained is worse than TF-IDF** |

Prediction: no measurable difference. TF-IDF led the untrained embedding by
21, and a gain of that size is about the most training can plausibly
deliver.

### Reported, not tested

- For each text model, filter on and off: met and caught-on counts,
  precision, base rate, lift, and met per area.
- Phase 23's within-route AUC test at 2011 for each text model, with a 95%
  interval for trained.
- Overlap between the trained lists and each of the other two.
- The training pairs: count, cutoff used, areas, loss.
- The reproduction of Phase 26 (above).

## Out of scope

Any other base model, loss, pair rule, cutoff (beyond the sizing rule),
filter level or list length. Anything the results suggest is reported as
exploratory in its own section.

## Run and budget

1. **Laptop:** the arXiv harvest, $0.
2. **One AWS CPU worker** (the Phase 12 launcher, `USERDATA=phase27data`):
   the snapshot join for references. About 20 minutes, under $0.50.
3. **One AWS GPU worker** with 64 GB of memory (g6.4xlarge, else g5.4xlarge;
   `USERDATA=phase27`), with a smoke pass first:
   - the off-the-shelf embedding;
   - the Phase 26 reproduction;
   - the training pairs and fine-tuning;
   - the trained embedding;
   - Phase 27.

   About 2 hours, about $3. The power-off timer is raised to 3 hours for
   this run.

Both workers self-terminate, have an idle-log watchdog and are torn down
with verification. Ceiling: **$10** in total, the approved budget.

---

## Results

*Appended after the run. Nothing above this line changed.* Run
`noema-p12-20261010-182539` (`USERDATA=phase27`, resumed from run
`noema-p12-20261010-172904`). Both ran on one g6.4xlarge (NVIDIA L4), torn
down and verified. Numbers are from `results/phase27.json`.

### Verdict

| test | result | verdict |
|---|---|---|
| **H1** trained vs untrained embedding, filter on | 65 vs 69 met; difference **−4** [−18, +10] | **no measurable difference** (predicted: training helps) |
| **H2** trained vs TF-IDF, filter on | 65 vs 90 met; difference **−25** [−49, −3] | **trained is worse than TF-IDF** (predicted: no difference) |

Training on 1,244 past surprising jumps did not improve the embedding's
lists, and TF-IDF stays well ahead.

### Data rebuilt, and Phase 26 reproduced

- **arXiv:** 600,987 math-primary papers; Phase 11 had 597,860.
- **References:** 526,556 papers were found in the OpenAlex snapshot,
  303,804 of them with references; Phase 11 had 526,506 and 303,714.
- **Phase 26 reproduced exactly** on the rebuilt data
  (`results/phase26-reproduced.json`):

| Phase 26 result | Rebuilt data |
|---|---|
| TF-IDF, filter on | 90 met |
| Embedding, filter on | 69 met |
| H2 difference | −21 [−42, −2] |
| H1 lift | 20.7 [15.7, 26.4] |
| Forecast gain at 2011, TF-IDF | +0.193 |
| Forecast gain at 2011, embedding | +0.095 |

### Training

- **Pairs:** cutoff 2000 gave 49,002 surprising pairs and 918 jumps
  (2001–2005), so the sizing rule kept cutoff 2000.
- **By target area:** most pairs went to rings and algebras (125), then
  algebraic topology (98) and combinatorics (81).
- **Fine-tuning:** 1,244 pairs, 2 epochs, 3.6 minutes.
- **The loss barely moved,** from 4.03 to 3.89. Picking at random among the
  64 candidates (32 positives plus 32 hard negatives) gives ln 64 = 4.16, so
  the model learned very little. An arriving paper and a random earlier citer
  of the same work are only loosely related texts.

### All six variants (lists at 2011, graded 2012–2021)

| variant | met of 560 | caught on (≥ 5) | lift |
|---|---:|---:|---:|
| TF-IDF, filter off | 128 | 10 | 20.7 |
| TF-IDF, filter on | 90 | 8 | 18.4 |
| embedding, filter off | 93 | 3 | 15.1 |
| embedding, filter on | 69 | 4 | 14.1 |
| trained, filter off | 103 | 3 | 16.7 |
| trained, filter on | 65 | 3 | 13.3 |

- **Overlap, filter on:** the trained lists share 344 of 560 pairs with the
  untrained embedding's and 108 with TF-IDF's. Training moved the lists only
  a little.
- **Forecast test at 2011** (Phase 23's, within route, filter off; this
  run's bootstrap seed):

| text model | forecast gain |
|---|---|
| TF-IDF | +0.176 |
| embedding | +0.098 |
| trained | +0.097 [+0.050, +0.148] |

- **Filter off,** trained beats the untrained embedding by 10 (103 vs 93).
  This was not tested and is within the noise that H1 shows.

### What this establishes

- **Dianoia's recipe does not carry over in this form.** Training the
  sentence model on 1,244 past surprising jumps neither improved its lists
  nor closed the gap to TF-IDF.
- **The training signal was weak, not the budget.** The loss barely fell
  below chance. In Dianoia, the pair was a citing text and the text it
  cited. Here the cited work has no text of its own, so its "text" is one
  random earlier citer, and the pairs carry little that a model can learn.

### What it does not establish

- That trained embeddings cannot help. Three untested reasons it might have
  failed here, each a separate test:
  - **A better pair:** a work's own abstract, or the mean of its citers.
  - **More pairs:** a later cutoff with a different split.
  - **A base model** that matches TF-IDF's word-level signal.
- That training hurts: H1's interval runs from −18 to +10.

### Deviations

- **Two failed GPU runs, both before any Phase 27 number:**
  - **First run** (`…-171344`): the checkpoint is stored in float16, which
    transformers 5 keeps, and T5's attention mask overflowed float16 under
    bf16. Training now loads float32 weights and trains in float32 (bf16
    off). Encoding stays fp16, as in Phase 26.
  - **Second run** (`…-172904`): batch 32 in float32 ran out of the L4's 22
    GB. Training now uses `CachedMultipleNegativesRankingLoss` (mini-batches
    of 8), which computes the same batch-32 loss. That run had already
    written the off-the-shelf embedding, the Phase 26 reproduction and the
    pairs. The final run reused them by checksum (`RESUME`) instead of
    recomputing.
- **Laptop harvest:** it was killed once for memory. The harvest
  (`run-phase11.py harvest`) now checkpoints every page and resumes; a
  killed-and-resumed test gave a byte-identical file.

### Cost and teardown

| run | instance | time | cost |
|---|---|---|---|
| references | m6i.4xlarge | ~15 min | ~$0.20 |
| GPU run 1 (failed smoke) | g6.4xlarge | ~8 min | ~$0.20 |
| GPU run 2 (out of memory) | g6.4xlarge | ~46 min | ~$1.00 |
| GPU run 3 (final) | g6.4xlarge | ~51 min | ~$1.10 |

**Total: about $2.50** of the approved $10. Every instance, role, instance
profile, security group and task object was deleted. A check found no Noema
instance or role left.
