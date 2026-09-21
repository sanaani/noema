# State-bridge v1 — replication and betweenness

1,797 Mathlib theorems, 99,275 captured proof states, 23,874 unique texts,
encoded with the pinned ReProver ByT5 retriever on an L40S (`device: cuda`,
`int8_float32`, uncapped tokenization — the archive's own settings). 366s.

Reproduce: `.venv/bin/python scripts/analyze-state-bridge.py`, which needs
`outputs/state-bridge-v1/vectors/reprover-embeddings.npz` — 272 MB, too large
for git. Everything upstream of the encode is committed here:

| file | what it is |
|---|---|
| `states-augmented.jsonl.gz` | the 99,275 captured states, so the Lean capture need not be repeated |
| `selected.json.gz` | the 1,797-theorem selection the capture ran against |
| `text-index.jsonl.gz` | the 23,874 unique texts, in encode order |
| `report.json` | every number below, machine-readable |

Rebuild the vectors with `scripts/build-encode-inputs.py --states
results/state-bridge-v1/states-augmented.jsonl.gz ...` then
`scripts/encode-reprover-gpu.py` (L40S, 366s, ~$0.31).

## 1. Replication

| measure | encoder | shuffled control | margin |
|---|---|---|---|
| AUC, all pairs | **0.877** | 0.714 | **+0.164** |
| AUC, cross-area only | **0.863** | 0.749 | **+0.114** |
| AUC, disjoint-state pairs | 0.877 | 0.714 | +0.164 |

n = 1,613,706 pairs, 83,572 positive. z = 368 against the analytic null;
the 20,000-shuffle permutation p bottoms out at 1/20001 and carries no
information at this scale. Observed-state objects alone: 0.863 / 0.850.

The archive got 0.786 on 128 objects, 14 positives. This replicates it and
exceeds it at 14x the objects and 6,000x the positives.

**Read the margin, not the 0.877.** The control keeps every theorem's
state-sharing structure and discards the encoder, and it still scores 0.714.
That is not noise, it is proof size: `min(state count)` alone predicts the
label at AUC 0.740. Large proofs cite more lemmas, so they are likelier to
share a rare landmark, and their centroids sit nearer the corpus mean
direction, so they are mutually similar. Both effects push the same way.
The encoder's claim is the +0.164 it adds on top.

## 2. Betweenness — the decision point

Does each known bridge sit between its endpoints? Scored by detour ratio
`(d(A,C) + d(C,B)) / d(A,B)` in angular distance, ranked against all 1,795
other objects in the corpus.

| family | detour | t | rank | percentile | control pct |
|---|---|---|---|---|---|
| Fourier | 1.453 | 0.17 | **6**/1795 | **0.3%** | 6.9% |
| Galois | 1.647 | 0.59 | **9**/1795 | **0.5%** | 53.2% |
| Euler criterion | 1.629 | 0.74 | **11**/1795 | **0.6%** | 49.5% |
| Euler | 1.569 | 0.29 | **25**/1795 | **1.4%** | 92.1% |
| FTC | 1.894 | 0.76 | **69**/1795 | **3.8%** | 72.0% |
| Fermat | 4.845 | 0.54 | **78**/1795 | **4.3%** | 54.8% |

All six bridges land in the top 4.3% of the corpus by betweenness, four in
the top 1.4% — 1.4% of 1,795 is rank 25, so ranks 6, 9, 11 and 25 qualify and
FTC's 69 and Fermat's 78 do not. The shuffled control scatters across
6.9-92.1% (median ~54%), so this is not the sharing structure or the
proof-size effect.

Fermat's detour of 4.845 is an artifact of a very short baseline
(d(A,B) = 0.541, the closest endpoint pair by far) — the ratio is inflated by
its denominator, which is why the rank against the corpus is the number that
matters, not the raw detour.

## Caveats that travel with these numbers

- The target is partly circular: proofs invoking the same lemma may share
  state shape *because* of that lemma.
- Proof size confounds the replication (see above). The betweenness test does
  not share this weakness — its null is the corpus, scored the same way.
- 5 of the 18 family members are synthetic single points (term-mode proofs,
  initial goal): Euler's bridge, Fermat's B, FTC's A *and* bridge, and Euler
  criterion's A. Fine for betweenness, which needs only a location, but FTC is
  the weak case — two of its three points are statement encodings with no
  captured proof states at all, and it is also one of the two families outside
  the top 1.4%. Any use of diameter, affine dimension or hull separation must
  exclude them.
- The control column is a single shuffle, so those six percentiles are one draw
  of the null and are noisy at n=6. The rank against the 1,795-object corpus is
  the null that carries the weight; the control only rules out the sharing
  structure producing betweenness on its own.
- `"no goals"` is excluded from every centroid (`--max-state-df 0.5`). Left in,
  the test scores AUC 0.702 on random vectors. See the script docstring.

## Status: open, not final

These two tests were the decision point named in issue #1, and betweenness
passed. That licenses continuing the line of work. It does not establish that
the geometry can find a connection nobody has made — every bridge here was
known in advance, and the corpus was deliberately seeded with them as a
positive control.

The follow-on measurement is `results/mathlib-forward-v1/`: freeze this model
at 2024, and check it against connections Mathlib formalized over the
following two years. Its README carries the current open questions, which
supersede the list below.

One number from there belongs here, because it changes how Test 1 should be
read: **proof size predicts the 2026 label at AUC 0.515** — a coin flip —
against the angle's 0.958. So the size confound that eats most of Test 1's
0.877 does not touch the forward result. Test 1 remains the weaker of the two.

