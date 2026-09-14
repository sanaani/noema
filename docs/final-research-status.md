# Final research status: bounded feasibility study

Historical v1 result. The user subsequently supplied a revised research plan;
the [continuation protocol](continuation-protocol-v2.md) and
[clustered power study](cluster-power-results.md) supersede this document's
whole-project completion claim. See the [current final result](revised-plan-results.md).
Its original measurements remain unchanged.

**The implementation and gated study are complete. The formal feasibility gate
failed.** This execution provides a verified multi-proof corpus and reproducible
negative evidence about this particular sampling/representation design. It does
not establish or globally refute the proposed geometry of mathematical theorems.
The plan's stopping rule closes the intersection/discovery phase without mining
or interpreting pairs from an inadequate population.

## Recovery and delivered work

The interruption occurred after Phase 0 qualification, apparently during the
first theorem of corpus collection. The working tree was clean at `4dbd37a`;
there were no saved corpus proofs or completed theorem checkpoints. The original
research document remains byte-identical to its initial commit.

Recovery added bounded, isolated Lean verification; atomic corpus and analysis
checkpoints; checked resume paths; complete corpus/split auditing; theorem-cluster
uncertainty; proof-sampling and diversity sensitivities; omitted baselines; graph
fidelity diagnostics; a unified CLI; compact evidence archives; and an independent
reproduction command. Existing Phase 0 metric files and thresholds were preserved.

| Implementation checkpoint | Final disposition | Evidence |
|---|---|---|
| 1. Repository and design | Complete; private `sanaani/noema`, preserved source document and committed protocols | [Recovery record](recovery-and-completion.md) |
| 2. Executable foundation | Complete; reproducible synthetic statistics, uncertainty, provenance, CLI and CI | [Reference smoke](../results/reference-smoke/report.md) |
| 3. Qualify and freeze | Qualified only in the restricted low-noise regime; failed v1 and noisy pilot retained | [Phase 0 review](phase-0-review.md), [stress supplement](../results/stress-v1/report.md) |
| 4. Verified multi-proof corpus | Complete for the preregistered Horn population, using two different search algorithms | [Corpus census](corpus-results.md), [audit](../results/corpus-v1/audit.json) |
| 5. Encoders and H1/H2 evaluation | Executed with three representations; feasibility gate failed | [Full formal report](../results/formal-v1/report.md) |
| 6. Added information and intersections | Baselines, sensitivities and fidelity executed; bounded negative result; intersection search closed by the failed upstream gate and absent cross-domain population | This report and the [pre-embedding supplement](formal-analysis-completion-v1.md) |

Proof navigation remains outside the research plan's primary scope. No positive
mathematical discovery, manifold, topology, or universal geometry claim is made.

## Corpus and inference

All 24 predetermined theorems supplied 64 Lean-verified proofs per generator:
3,072 proofs and 66,322 retained intermediate state occurrences. Verification
reported no errors, admitted proofs, or axioms. Canonical proof-tree identities
and normalized state-sequence duplicates were removed before splitting. There
were 108 duplicate forward state sequences; 2,964 proofs remained eligible.

Every primary cloud uses 32 distinct proofs and four state occurrences per proof,
without replacement, for 128 points. All 24 theorems qualify for cross-generator
and within-backward comparisons. Only one qualifies for within-forward replication,
so those tests were skipped under the fixed requirement of at least 12 theorems.
States are observations from this bounded search population, not all possible
states or independent iid samples of a theorem.

The corpus and exact proof/state splits were committed at `6211c0a` before
embedding. The formal run records that clean launch revision. Encoders receive
only normalized individual state content. The text model and tokenizer have
pinned revisions/checksums; syntax hashing and exact truth-table representations
are separate controls. No encoder was trained or calibrated on these evaluation
theorems. General-text pretraining contamination cannot be exhaustively audited,
and MiniLM is not claimed to be a validated mathematical state encoder.

There are 12 primary tests in one BH family, with 9,999 whole-theorem gallery-label
permutations per test. Proof/state blocks remain intact. This conditional null
assumes gallery-label exchangeability under independence in the generated
population; matching file, domain, atom count, premise count and conclusion does
not eliminate every premise-network confound. Percentile intervals use 2,000
paired theorem bootstrap draws, resampling both axes together and excluding
same-theorem copies from mismatched pairs. They are exploratory and conditional
on the observed proofs, not simultaneous guarantees about mathematics at large.

## Main finding and added-information test

For the pretrained text encoder, full-context cross-generator cloud matching has
pairwise win rate **0.862**, with theorem-bootstrap 95% interval **[0.782, 0.934]**.
Its raw permutation p-value is 0.0001 and BH-adjusted q is approximately 0.0001714.
Thus a full-context association exists in this bounded population.

That association is insufficient for the specified claim:

| Cross-generator text comparison | Pairwise win rate |
|---|---:|
| Full state cloud | 0.862 |
| Centroid | 0.877 |
| One sampled proof cloud | 0.777 |
| One proof's trajectory summary | 0.893 |
| Initial-state/statement representation | 1.000 |
| Used-premise overlap | 1.000 |
| Available-premise-network overlap | 1.000 |
| Hypothesis-structure counts | 0.920 |
| Tactic histogram | 0.500 |
| Constant file/domain/definition control | 0.500 |

Chance pairwise win rate is 0.5; tied comparisons receive half credit. The full
cloud-minus-centroid gain is **−0.014**, with paired 95% interval
**[−0.059, 0.031]**. The cloud improves on one sampled proof but offers no demonstrated
increment over the centroid or simpler statement/premise baselines. Statement
self-matching has a ceiling advantage in this task; it cannot by itself evaluate
added cross-theorem mathematical information.

With the premise context removed, cross-generator matching is **exactly 0.500**
for all three encoders, with q=1. The forward search retains the same final goal
while adding facts. Its goal-only cloud therefore contains one identical vector
at every occurrence, across all theorems. The text goal-only gain over centroids
is zero, below the preregistered 0.05 requirement, and the representation-collapse
criterion also fails.

This control deletes newly derived facts as well as initial premises. Its failure
therefore cannot uniquely distinguish a syntax confound from loss of legitimate
contextual proof progress. Moreover, in this Horn population the initial facts
and implications entail all eight atoms. The premise networks can consequently
have equivalent denotational contexts despite different presentations. The exact
truth-table control exposes that collapse. These are limitations of the selected
corpus and state views, not grounds for rejecting all contextual representations.

Within-backward goal-only matching remains above chance: text 0.806, syntax 0.848,
and truth 0.848. However, cloud gains over their centroids are only approximately
0.002, 0.002, and 0.005, with intervals including zero. The full-context cross-generator
association also fails to replicate in the other representations: syntax cloud
win rate is 0.391 and truth is 0.500. A positive, encoder-independent theorem
geometry has not been established.

## Robustness and fidelity

The two separately fixed proof/state sampling seeds produce full-context text
win rates of 0.882 and 0.866; stricter used-premise-set deduplication gives 0.868.
Every corresponding goal-only cross-generator result remains 0.500. The stricter
tactic-histogram policy leaves no eligible theorem, which is reported as inadequate
coverage rather than repaired by lowering the sample threshold. These 18
sensitivity results are descriptive and carry no additional significance claims.

Operational graph alignment succeeded for the selected validation proofs. For
the full text encoder, mean edge-versus-nonedge AUC is 0.505 on backward proof trees
and 0.637 on forward fact-dependency graphs. Goal-only text scores are 0.587 and
0.500. The different graph types and focused Lean tactic records make this a local
operational fidelity diagnostic, not full kernel-graph reconstruction. The full
report includes all encoders, per-theorem records, and zero alignment failures.

The supplementary synthetic audit ran 400 comparisons. Null rejection rates were
0.05 and 0.04; both known alternatives were detected in 100/100 trials. Common
rotation/translation changed exact metric diagnostics only at floating-point
precision. The anisotropic null's upper Wilson bound was 0.112, so this small
supplement does not extend the qualification regime. Changes in mixture sampling
weights were readily detected despite unchanged component support, illustrating
why prover sampling frequencies are a genuine confound for empirical clouds.

## Hypotheses and kill criteria

| Question or kill criterion | Outcome |
|---|---|
| H1 / independent proof-sample reproducibility | Supported conditionally within backward search; full-context text association also appears across generators. Strong sampler-independent geometry is not established. |
| H2 / survival of syntax and premise controls | Not established. Goal-only cross-generator controls collapse, and simple premise/hypothesis controls account for strong matching. |
| H3 / information beyond simpler representations | No demonstrated increment in this task. Cross-domain mathematical added information is untested because there is only one domain. |
| H4 / meaningful shared regions beyond chance | Untested. There is no eligible cross-domain candidate family and the upstream feasibility gate failed. |
| Kill 1: within-theorem instability | Not a blanket failure within backward search; within-forward replication is unavailable at the required coverage. |
| Kill 2: loss across proof generators | Triggered for the required goal-only view; full text association alone does not satisfy the gate. |
| Kill 3: file/definition/syntax explanations | File/domain/vocabulary are matched, but premise and hypothesis controls are stronger than the cloud; contextual versus syntactic causes are not uniquely separated. |
| Kill 4: no added information beyond centroid/statement | Triggered for this feasibility task. |
| Kill 5: overlaps fail multiplicity control | Not tested; no overlap search was run. It would be incorrect to report a failed intersection p-value. |
| Kill 6: encoder robustness | No positive cross-generator finding robust to all representations. |
| Kill 7: synthetic measurement failure | Restricted low-noise v2 passed; high-noise power limits and the earlier failed qualification remain. Formal 384-dimensional text results are explicitly exploratory. |

The correct terminal outcome is a **failed bounded feasibility design**, not a
claim that mathematical theorem geometry does not exist. A different study would
need semantically richer populations, adequate within-forward diversity, controls
that distinguish initial premises from derived facts, and independently validated
mathematical encoders. Those would require a new preregistration; no thresholds,
corpus selection, or representations were retuned after these geometric results.

## Reproducibility and artifacts

The [reproduction guide](reproduction.md) covers installation, collection, checkpoint
recovery, archive verification, the exact split freeze, analysis and cached-vector
recomputation. The [formal JSON and vector checksums](../results/formal-v1/SHA256SUMS)
retain all primary distance matrices, controls, confidence intervals, collapse
checks, sensitivity results and graph diagnostics. The corpus archive retains
proof sources and Lean evidence; the formal archive retains all three vector caches.

Local validation passed **68 tests**, including actual Lean and pinned CPU-model
integration, plus lint and formatting. All 12 primary results were reproduced exactly in a fresh process from the
archived corpus, frozen splits and vector caches by
`scripts/verify-formal-result.py`. This is a reproducibility check using the same
implementation, not a new statistical replication. The [validation record](../results/formal-v1/validation.json) retains the output. A [training manifest](../results/formal-v1/training-manifest.json)
documents the immutable model card and the limits of the training-data audit;
that metadata review occurred after the run and did not change model selection. Historical literature inputs were checked in a
[bounded source audit](literature-audit.md); no first-of-its-kind claim is asserted.
