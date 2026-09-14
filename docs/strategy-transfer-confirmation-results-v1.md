# Fresh confirmation without a minimum gain requirement

**Status: acquisition in progress.** The user rejected the ten-point requirement
after the development result and directed continuation. The new primary rule
requires exact paired-test evidence of positive added information over every
control, with no minimum gain. The completed development measurements and the
original failed margin gate remain preserved in the [v2 report](strategy-transfer-results-v2.md).

## Preregistration and frozen population

The [new protocol](strategy-transfer-confirmation-protocol-v1.md) was committed
at `d2bb6d6`, before nine-leaf assignments or embeddings. Analysis source was
committed at `30337a3`; the assignments and power calculations were frozen at
`ec6dfb1` before acquisition. The acquisition run started from that clean commit.
The assignment manifest reports a dirty tree because it was written after the
new archive files were created; its analysis source hashes match the committed
source. No measurement informed assignment selection.

The deterministic search found all 512 triplets after examining 795 anchors in
the 226,600-record nine-leaf population. They contain 1,536 distinct theorem
endpoint pairs and 14,433 distinct proof programs. No program is reused across
confirmation triplets. Source-clade overlap, target-clade overlap and premise
overlap match exactly between the positive and negative candidates.

There are 272 address-based program templates shared with development, although
the different leaf count prevents theorem endpoint reuse. This is a held-out
population within one synthetic rewrite family, not independence from every
development structural motif or evidence across mathematical domains.

An independent indexed, depth-limited graph enumeration reconstructs all 1,536
complete shortest-proof banks exactly. Literal replay validates 28,053 directed
program-transfer attempts. The full Lean acquisition must verify all 6,144 sampled
proofs and 30,720 intermediate states before encoding the 8,500 unique inputs.

## Sensitivity to smaller effects

Exact paired-test power averages the conditional binomial rejection rule over
the discordant-pair count. The archived table covers 72 combinations of sample
size, gain and discordance. The table below assumes total discordance .05,
close to the development resampling mean .049375 for energy versus centroid.
It describes one paired comparison; joint success against all nine controls
cannot have greater power than its least powerful component.

| Triplets | 1.2-point gain | 2-point gain | 3-point gain |
|---|---:|---:|---:|
| 512 | .2703 | .5900 | .9129 |
| 1,024 | .4791 | .8731 | .9970 |
| 2,048 | .7575 | .9916 | 1.0000 |

The acquisition remains the preregistered 512-triplet budget. This has useful
sensitivity to some sub-ten-point effects but limited sensitivity to a gain near
the development mean of 1.19 points. Neither a nonsignificant outcome nor the
original larger-effect power analysis would establish absence of a small gain.
Effect estimates and marginal triplet-bootstrap intervals are required outputs.

## Acquisition and reproducibility

The initial sequential acquisition was paused using its successful triplet
checkpoints, then split into even/odd triplets on two processes. Both call the
same frozen Lean-audit implementation and write to disjoint output paths. The
worker preserves proof source, actual Lean response and every global triplet ID;
only audit-record indexing is remapped from the one-triplet helper invocation.
The final archive verifier independently validates all sources, responses and
contexts, so scheduling is not relied upon for correctness.

Encoding can likewise run on two disjoint, lexicographically interleaved input
shards. Each uses the unchanged pinned encoder implementation, including singleton
ReProver batches and its original CPU thread count. The merge requires identical
manifests, exact input coverage and exact preservation of any existing vectors.
No floating-point reduction or statistical rule is changed by this scheduling.

See the [reproduction guide](reproduction-strategy-transfer-confirmation-v1.md)
for sequential execution, resumption and the parallel acquisition commands.
The results section will be completed after all registered observations finish.
