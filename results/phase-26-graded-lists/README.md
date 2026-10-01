# Phase 26 — grade the matchmaker lists, then fix them

**Pre-registration.** Everything in this file is written and committed before
any Phase 26 number is computed. Results go in a section appended below;
nothing above that section changes.

## Why

Phase 25 made per-area lists (20 pairs per area) at 2021. Reading them showed
two defects that need no mathematics to see:

- **Word collisions.** The text model counts words, so set-theory "ideals"
  land in commutative algebra and "Yang–Baxter" papers land in PDE.
- **Textbooks.** A book cited across many fields looks "unconnected" to every
  field that has not cited it yet.

Nobody on the project can judge the remaining third by reading it. So the
lists are graded by the data instead: make them at **2011**, exactly as at
2021, and count how many of each area's 20 the area actually picked up by
**2021** (references are intact to 2021; Phase 21 sizing). Then test the two
fixes against that grade, and ship the 2021 lists with their grade attached.

Already seen before this file was written: all results of Phases 11–25,
including Phase 25's 2021 lists.

## Data

Phase 11's arXiv math papers and OpenAlex references (28 areas,
`W4285719527` dropped).

## Text models

- **TF-IDF**: Phase 25's (TF-IDF + 256-dimension SVD), fitted on papers up to
  the cutoff only.
- **Embedding**: `sentence-transformers/sentence-t5-base`, title + abstract,
  unit-normalised, computed once for papers up to 2021
  (`scripts/embed-phase26.py`). It is chosen because it was **not trained on
  citation links**: many scientific embedding models (SPECTER, all-mpnet,
  E5, BGE) were trained to place citing and cited papers close together,
  including citations after 2011, which would leak the outcome. Residual
  leak: the model was pretrained on web text that may include post-2011
  mathematics. It is stated, not removed.

Similarity, as in Phase 25: cosine between the mean vector of the work's
citers up to the cutoff and the mean vector of the area's papers in the last
5 years up to the cutoff.

## Textbook filter

A work is dropped when its **breadth** (number of areas citing it up to the
cutoff) is in the **top 10%** of works with at least 5 citers at that cutoff
(computed at each cutoff, from citations only). This is a product choice, not
a tested improvement: textbooks are cited widely, so dropping them is
expected to *lower* the hit count while removing entries a reader would
discard. Its cost in hits is reported.

## Population, model, lists

Phase 25's population at each cutoff: **surprising** unconnected pairs
(work with at least 5 citers; no citer in the area, none listing it as a
secondary category, none in the area's 3 nearest areas by co-citation), span
≥ **4.65 bits**. Phase 25's model: logistic regression, BASE (log citers, log
recent citers, log area size, span, breadth, home and target dummies) plus
similarity; features standardised on the training population.

**Graded lists (no outcome overlap):**

- **Train at 2005**, label = at least 5 target-area papers citing the work in
  **2006–2011** (the window is cut at 2011 so that no training label uses a
  year the lists are graded on).
- **Apply at 2011**; for each area, the **20 pairs with the highest score**.
- **Grade**: a listed pair is **met** if at least 1 target-area paper cites
  the work in 2012–2021; it **caught on** if at least 5 do.

Four variants: text ∈ {TF-IDF, embedding} × filter ∈ {off, on}. Each is
trained and listed separately. Seed **20261016**.

## Tests

### H1 — the grade of Phase 25's lists (TF-IDF, filter off)

Precision = met pairs / listed pairs. Lift = precision / base rate, where the
base rate is the share of all pairs in the same 2011 population that are met.
95% interval for the lift from 10,000 bootstrap draws over target areas
(base rate held fixed).

| outcome | verdict |
|---|---|
| lower bound of lift > 1 and lift ≥ 10 | **far better than chance** |
| lower bound of lift > 1, lift < 10 | **better than chance** |
| interval contains 1 | **no better than chance** |

Prediction: far better than chance.

### H2 (primary) — does the embedding make better lists?

With the filter **on** (the lists as they would ship): met pairs in the
embedding lists minus met pairs in the TF-IDF lists, summed over areas; 95%
interval from 10,000 bootstrap draws over target areas.

| outcome | verdict |
|---|---|
| interval above 0 | **embedding is better** |
| interval contains 0 | **no measurable difference** |
| interval below 0 | **embedding is worse** |

Prediction: no measurable difference (lists are small; the embedding's gain
is expected mostly in fewer word collisions, which this count does not see).

### Which lists ship (fixed now)

The 2021 lists use the embedding unless H2 says **embedding is worse**, in
which case they use TF-IDF. The burden is on the embedding only to not be
worse, because it removes a defect seen by reading. The filter is on. The
2021 model is trained at 2011 with Phase 25's 10-year label (2012–2021), as
in Phase 25.

### Reported, not tested

- For all four variants: met and caught-on counts, precision, base rate,
  lift; per area, met of 20.
- The cost of the filter: met pairs with filter off minus on, per text model.
- Overlap between the TF-IDF and embedding lists (shared pairs).
- The 2021 lists, each area headed by its 2011 grade.
- Phase 23's within-route AUC test at 2011 for the embedding (as Phase 25's
  H1), to see whether the embedding forecasts as well as TF-IDF.

## Out of scope

Any other embedding model, threshold, filter level or list length. Anything
the results suggest is reported as exploratory in its own section.

## Run and budget

One AWS GPU instance with 64 GB of memory (g6.4xlarge, else g5.4xlarge) via
the Phase 12 launcher (`USERDATA=phase26`), self-terminating, idle-log
watchdog, 2-hour power-off; smoke pass first (every 4th paper). Embedding
about 10 minutes, five builds about 30 minutes: under $2. Teardown verified.
