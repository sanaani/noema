# History

The working tree holds one line of work: theorem-link discovery through the
geometry of proof states. Four earlier lines ran before it. They are not in the
tree, and they are not deleted — every file, every result and every protocol is
in the commit history at the point where it was written, which is also the point
at which it was believed.

Read any of it without disturbing the tree:

```bash
git checkout full-research-trail       # the whole pre-prune tree, 2026-09-21
git show <sha>:docs/<file>.md          # one file as it stood at one commit
git log --all --full-history -- docs/<file>.md   # that file's own history
git log --oneline <first>..<last>      # a phase, commit by commit
```

Each phase below ran to a preregistered gate and is reported at its outcome,
not at its hope. Three of the four failed their gate. That is why they are
history and not the tree.

---

## 1. Synthetic benchmark and the first formal study

**2026-09-13 · `c8937aa..92347cc` · 18 commits**

Start of the project, from
[the original proposal](latent_geometry_mathematical_theorems_research_plan.md).
Built a reproducible synthetic pipeline comparing unordered point clouds
(Gaussian MMD², energy V-statistic, sliced Wasserstein-1, radius coverage,
centroid distance) with permutation nulls and Benjamini–Hochberg correction,
qualified it on held-out synthetic regimes, then ran it on real Lean proofs:
3,072 machine-verified proofs, frozen disjoint sampling, three pinned encoders.

**Outcome: negative.** The distributional metrics carried no information beyond
the centroid baseline. Reported in full at `docs/final-research-status.md` and
`docs/checkpoint-2-results.md`; the archived corpus and embedding caches are at
`results/corpus-v1/` and `results/formal-v1/`.

## 2. The revised matched study (canonical v3)

**2026-09-13 · `85c166e..4193f79` · 14 commits**

The first study's task was saturated, so the population was rebuilt with exact
common-length and depth matching, proof-block permutation, clustered power
calibration, and a fresh independently seeded corpus: 1,864 verified proofs,
60,501 states. Energy was selected as the primary metric by the power study
before any embedding was computed.

**Outcome: reproducibility survives, the added-information gate fails.**
`docs/revised-plan-results.md`, `docs/cluster-power-results.md`,
`docs/reproduction-v3.md`, `results/canonical-v3/report.md`.

## 3. Strategy transfer

**2026-09-14 · `3e68fc4..255fe51` · 32 commits**

If a State object carries information a centroid does not, it should predict
which of two proof strategies transfers to a new theorem. An adversarial
analysis first showed why the earlier centroid scored perfectly: invariant
premise text was sufficient, and all 12 contexts were constructively equivalent
in Lean, so that ceiling was never an informative test. A first screen failed
its task and budget gates; a structurally matched redesign passed both (all
nine baseline upper bounds below 71.2%), and a 512-triplet confirmation was
acquired with exact matching and no minimum-gain rule. All 6,144 sampled
proofs and 30,720 intermediate states passed Lean.

**Outcome: no advantage for the sampled-state predictor.** 53.91% against the
centroid's 54.49%, paired gain **−0.59 points**, bootstrap 95% interval
[−2.54, +1.37]. None of the three sampled-state arms beat its centroid. Tactic
histograms scored 82.03% and complete proof programs 92.19%, so the information
is in the proof text, not in the sampled state cloud.
`docs/gpu-execution-results-v1.md`,
`docs/strategy-transfer-confirmation-results-v1.md`,
`docs/adversarial-centroid-results-v1.md`. The GPU archive at
`results/gpu-execution-check-v1/` reproduces every score without a GPU.

## 4. State objects and convex hulls

**2026-09-14 – 2026-09-16 · `e1b1f2a..b314eae` · 17 commits**

A shift from comparing distributions to describing one theorem's states as an
object: every nonempty proof state of a theorem, its rays from the initial
state, and cumulative mass. Complete acquisition of 26,820 state records, one
physical vector row per record; convex hulls and inward-bending area boundaries
for all 102 admitted theorem groups; interactive explorers; a printed-state
identity audit; an enforced admission rule that excluded six groups whose
assumptions were proved contradictory in Lean and held 148 with unresolved
source identity.

**Outcome: the forms could not be interpreted.** Every object touches at the
empty-goal encoding and formatting sensitivity is substantial, so the hulls
cannot be read as the shapes of mathematical ideas.
`docs/theorem-forms-v1.md`, `docs/theorem-admission-remediation-v1.md`,
`docs/state-object-convex-hull-literature-review.md`,
`docs/current-state-object-spec.md`. The explorers are at
`results/theorem-boundaries-v2/explore.html` and
`results/theorem-forms-v1/explore.html`; the full archive at
`results/state-object-records-v1/`.

Two things from this phase are still in the tree because the current line
measures against them: `results/state-object-v1/` (the 128-object, 3,659-state
ReProver archive) and `results/historical-connections-v1/` (the initial-State
pilot that produced the first bridge families).

`docs/theorem-density-usefulness.md`, written at the end of this phase, argued
for the usefulness of these objects and proposed the next investigation. The
pivot below chose a different one.

---

## 5. Theorem-link discovery — the current line

**2026-09-18 – 2026-09-21 · `d0a459f..HEAD`**

The hypothesis changed: relatedness is learnable from denoised
theorem↔theorem edges — two theorems are linked when their proofs depend on
the same lemmas, regardless of vocabulary. See
[theorem-link-discovery-plan.md](theorem-link-discovery-plan.md) for the
argument and [state-bridge-run-plan.md](state-bridge-run-plan.md) for the run.

What was known, and when:

| date | commit | what changed |
|---|---|---|
| 09-18 | `d0a459f` | Qwen on complete Lean states: targets beat background in 5 of 6 families, but lose to lexical lookalikes in 4 of 6. The geometry tracked "talks about the same things". |
| 09-18 | `b557be1` | Two new machine-checked bridge families; the benchmark reaches six cases. |
| 09-18 | `e3473a3` | 206,889 dependency edges from pinned Mathlib. The graph the rest of the line runs on. |
| 09-19 | `824f3c2` | **First real signal.** State centroids on the archived 128-object corpus predict shared rare lemmas at AUC 0.786 (p=0.0001) — on 14 positives. |
| 09-19 | `21276e6` | 4,000 near-miss (A, B, bridge) triples from the citation graph. |
| 09-19 | `b072f9f` | Hand-inspecting 8 of them yields no hidden connection, but one genuinely unnamed lemma — the observation behind [muse-brief-lemma-hygiene.md](muse-brief-lemma-hygiene.md). |
| 09-19 | `2390fbf` | Linear ranking head beats the frozen encoder 3/3 on held-out families — but beats the *lexical* baseline in only 1 of 3. See the statement-ranker section below; this is not part of the state-geometry line. |
| 09-20 | `c9a6f73` | Capture complete: 99,275 states over 1,797 theorems. |
| 09-20 | `cf50941` | The replication test scored AUC 0.702 **on random vectors** — the terminal `"no goals"` state, shared by every tactic proof, was carrying it. Caught and fixed before the run. |
| 09-20 | `b4cda9d` | Both tests pass. AUC 0.877 (+0.164 over the shuffled control); all six bridges in the top 4.3% by betweenness. |
| 09-21 | `5443083` | Forward test: the 2024 geometry ranks the pairs Mathlib connected by 2026. 124× lift in the 45–55° band. |
| 09-21 | `a142bcc` | Proof size — the confound that faked AUC 0.740 on the replication target — is a coin flip on the 2026 label at 0.498 (0.515 as first published, before ties were averaged), against the angle's 0.958. |
| 09-21 | `6a08a17` | Both result READMEs rewritten to say plainly what is still open. A sealed 2025-split rerun is considered and rejected: splitting 22 positives costs more power than the ceremony buys. |
| 09-21 | `544d980` | **The rename threat closes.** Every binder and hypothesis renamed in all 1,797 theorems, certified in Lean on the `Expr`: forward 0.958 → 0.964, betweenness 6/6 inside the top 3.3%, replication margin +0.167 → +0.162, while the lexical baseline the angle is scored against drops 0.764 → 0.610. Centroids move a median 20.0°, so the encoder is not name-blind — *exact invariance is false, discriminative invariance holds*. [`rename-control-v1`](../results/rename-control-v1/README.md). |

The question the project exists to ask — can the geometry find a connection
nobody has made — is still untested. Everything above is recognition of links
that already exist.

## The statement ranker, and why it is not in the tree

Between 09-18 and 09-19, before any proof state had been captured, a separate
line of work built a ranker over theorem **statements**: a linear contrastive
head (`scripts/train-link-ranker.py`) over frozen Qwen vectors of theorem
s-expressions (`scripts/encode-training-texts-gpu.py` encoded `sexpr`, the
theorem center, not proof states). Its artifacts were
`results/link-ranker-v1/`, and two structural follow-ups,
`results/structural-semantic-evaluation-v1/` (which produced no vectors and no
scores — a CPU attention pass that never finished) and its GPU rerun
`results/structural-semantic-qwen-gpu-v1/`.

None of it is read by any current analysis, test or CI step, and it uses a
different encoder on different inputs from the measurements in the tree, so it
was moved here on 09-21. Recover it with `git show b072f9f` or the
`full-research-trail` tag.

What it found, which is worth keeping on the record:

| commit | what it showed |
|---|---|
| `2390fbf` | The head beat the frozen encoder on all three held-out directions (ranks 61→13, 9→6, 13→7) but beat the best *lexical* decoy in only one of them. |
| `b072f9f` | Asked for hidden connections, it produced 30 candidates. Hand-investigated: 12 noise, 9 "genre resemblance" (same proof flavour, generic deps only), 4 topical, 2–3 bridgeable. Its own lesson: "the head reliably finds shared proof machinery, but shared machinery ≠ composable statements." |
| `aca2cca` | One candidate did compose, was conjectured and machine-checked in Lean, and is the only machine-proposed result the project has: `results/bridge-conjecture-v1/`. |
| — | Training loss rises every epoch in all three heads, so the head was not converging. |

**This does not bear on the proof-state geometry.** It is a different encoder
over different inputs, and the state geometry has never been asked to propose a
connection. That question is still untested, not failed.
