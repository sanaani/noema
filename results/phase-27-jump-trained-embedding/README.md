# Phase 27 — train the embedding on past surprising jumps

**Pre-registration.** Everything in this file is written and committed before
any Phase 27 number is computed. Results go in a section appended below;
nothing above that section changes.

**Approval.** Shaun approved a phase applying Dianoia's recipe (training the
encoder on far jumps) to Noema, with an AWS budget of $10, on 10/10/2026.
H1 and H2 below await his approval. The data rebuild may run first, because
it computes no Phase 27 number.

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
