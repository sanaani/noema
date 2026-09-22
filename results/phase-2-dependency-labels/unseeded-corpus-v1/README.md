# Unseeded corpus v1 — the draw, before the capture

**Pre-registration.** Everything here was written before a single proof was
replayed.

Phase 1's 1,797 theorems were chosen one at a time, by criteria that may
correlate with the geometry under test. No analysis can remove that. Phase 2
replaces the corpus with **350 Mathlib files drawn once from seed 20260922**,
stratified by area, and keeps every theorem in them that will replay.

| | |
|---|---:|
| files | 350 of 4,148 (8.4%) |
| areas | 28 |
| theorems | 16,708 |
| **predicted positives** | **5,527** |
| ... cross-area | 2,738 |
| predicted connectors | 5,674 |
| predicted pairs | 6,987 |

## Why the positives are known in advance

A pair is positive when some theorem new since 2024 cites both halves. That
depends only on which theorem *names* are in the corpus — not on any state, any
vector or any geometry. So the label of this draw is computable from the two
committed edge lists alone, and `scripts/draw-corpus-sample.py` computed it here
before the capture was launched.

This is the point. A corpus drawn after seeing which draw scores well is not a
test of anything. The seed was fixed, the draw was taken once, the yield was
written down, and the corpus is used whatever it gives.

The realized count will be lower: a theorem that fails to replay leaves the
corpus, and positives fall roughly as the square of the fraction kept. At phase
1's 76% completion rate that is ~3,200 — still well past the 1,000 the sizing
asked for.

## Files

| file | what it is |
|---|---|
| `sample.json` | the draw: seed, strategy, the 350 modules, per-area counts, predicted yield |
| `modules.txt` | the 350 modules, for `DeclRanges.lean` |
| `names.txt` | the 16,708 theorem names, for `DeclRanges.lean` |

Reproduce:

```bash
scripts/draw-corpus-sample.py --files 350 --seed 20260922 \
  --edges-2026 ../link-graph-2026-v1/edges-2026.jsonl.gz --out sample.json
```

## Capture

`scripts/run-capture-aws.sh` replays these files in phase 1's exact environment
— Lean 4.9.0, Mathlib `f0957a7`, REPL `d920817` plus
[the noema patches](../../../scripts/state-object-patches/) — so the new
centroids are comparable with the old ones.

The run is staged and the throughput gates the spend: it replays 18 random files
first, measures seconds per file and the memory low-water mark, projects the
rest, and continues only if the projection fits the hour budget. Over budget, it
ships the measurement and terminates.

The replay is **per file, not per theorem**: one REPL elaborates the whole file
and every requested declaration in it comes out of that one pass. Phase 1 paid
567 file elaborations to keep 1,797 theorems, 3.2 per file. That is why 350
files can yield 16,708.
