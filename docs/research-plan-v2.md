# Research Plan: Latent Geometry of Mathematical Theorems

## 1. Core conjecture

A mathematical theorem may have many valid proofs. Each proof passes through a collection of intermediate mathematical states: assumptions, goals, substitutions, decompositions, equivalent formulations, intermediate lemmas, and other formal configurations.

The central conjecture is that **the collection of states associated with proofs of a theorem forms a meaningful geometric object in latent space**.

For a formal mathematical state \(S\), let an encoder produce:

\[
E(S)=z\in\mathbb{R}^d
\]

For theorem \(T\), collect states from many independently discovered valid proofs:

\[
P(T)=\{p_1,p_2,\ldots,p_m\}
\]

and define:

\[
X_T =
\bigcup_{p\in P(T)}
\{E(S):S\in p\}.
\]

Crucially, once those states have been collected, we deliberately discard:

- proof order;
- transitions between states;
- graph edges;
- tactic sequence;
- which particular proof produced each state.

The theorem is therefore represented not as a path and not as a graph, but initially as an **unordered point cloud or empirical distribution of mathematical states**.

The conjecture is:

> **The states sampled by multiple valid proofs of a theorem occupy a reproducible region or structure in mathematical representation space, and different theorems may exhibit meaningful geometric overlap even when they appear unrelated in notation, domain, or statement.**

The longer-term possibility is that such overlaps reveal recurring structures of mathematical thought that are not captured by traditional theorem classifications or by individual proof trajectories.

---

## 2. Why this matters

Most representation-learning approaches compress a theorem into something like:

\[
T\rightarrow z_T.
\]

That destroys internal variation.

The proposed representation instead gives a theorem an entire object:

\[
T\rightarrow X_T.
\]

Two theorems could therefore have distant centroids while sharing an important subregion:

\[
X_A \cap X_B 
eq \varnothing
\]

in an appropriate geometric sense.

Likewise, two theorem clouds might have similar centers but radically different internal structure.

The scientific opportunity is therefore not merely better theorem similarity. It is the possibility that **mathematical ideas themselves correspond to recurring regions, configurations, or motifs in the space of formal mathematical states.**

---

## 3. What “intersection” means

Literal equality between high-dimensional vectors is unlikely to be useful.

The intersection between theorem geometries should instead mean measurable shared structure, such as:

- overlapping density support;
- mutual nearest-neighbor regions;
- low optimal-transport distance between subsets;
- shared local geometric structure;
- common clustering structure;
- common persistent topological features.

We should not assume in advance that these point clouds form smooth manifolds or meaningful topologies.

The empirical progression is:

\[
\text{point cloud}
\rightarrow
\text{reproducible geometry?}
\rightarrow
\text{topological structure?}
\]

Calling \(X_T\) a manifold should therefore be an experimental conclusion, not a premise.

---

## 4. Relationship to existing research

### 4.1 Mathematical reasoning in latent space

Lee, Szegedy, Rabe, Loos, and Bansal showed that formal mathematical expressions can be embedded into fixed-dimensional latent representations that retain enough semantic structure to support several approximate rewrite operations. Their experiments demonstrate that mathematical state representations can contain information about which formal transformations are possible.

Reference: https://research.google/pubs/mathematical-reasoning-in-latent-space/

This supports an important prerequisite of the conjecture:

\[
\text{formal mathematical state}
\rightarrow
\text{meaningful latent representation}.
\]

However, their research studies operations on individual representations. It does not collect states across alternative proofs and treat that collection as the representation of a theorem.

### 4.2 Dartmouth: proof trajectories in latent space

Samoylov and Vosoughi's 2026 work, *Representing Lean Proofs as Trajectories in Latent Space*, is the closest recent empirical neighbor.

They encode **changes between consecutive Lean proof states** and analyze complete proofs as trajectories through the resulting latent space. They find measurable geometric structure involving path length, endpoint span, directness, curvature, and torsion, and show that the learned transition representation contains more useful structure than a matched surface-syntax representation.

Reference: https://aclanthology.org/volumes/2026.acl-srw/

Their object is:

\[
\Delta S_1
\rightarrow
\Delta S_2
\rightarrow
\Delta S_3
\rightarrow \cdots
\]

The proposed research instead studies:

\[
\{E(S_1),E(S_2),E(S_3),\ldots\}.
\]

Dartmouth asks:

> What geometry does a proof trajectory have?

This project asks:

> What geometry is occupied by the mathematical states encountered across many different proofs of the same theorem?

The distinction is central. Dartmouth preserves the path. This project deliberately removes it.

Their results nevertheless provide important evidence that formal proof representations can exhibit nontrivial geometry.

### 4.3 Multiple proofs contain additional information

Kühlwein and Urban investigated learning from multiple proofs of the same theorem and showed that the particular alternative proofs used for learning materially affect automated theorem-proving performance.

Reference: https://citeseerx.ist.psu.edu/document?doi=f6dbc7e8a1efca9e8b1c252e1bdd0ed810960993&repid=rep1&type=pdf

This supports another premise of the project:

> Alternative proofs should not be assumed to contain redundant information.

Different proofs may expose different portions of the underlying mathematical state space.

### 4.4 Graph embeddings and geometric fidelity

We do **not** need to establish from scratch whether vector embeddings can preserve structural information from graphs.

Liu et al. directly studied how much graph topology survives embedding, measuring graph reconstruction, link distributions, community preservation, and link prediction. They found that embeddings preserve meaningful but incomplete portions of the original topology.

Reference: https://doiserbia.nb.rs/Article.aspx?ID=1820-02141900011L

RESTORE subsequently formalized graph reconstruction as an intrinsic way of measuring how much topology and semantic information survives vectorization. Its experiments likewise show measurable but imperfect recovery of graph structure.

Reference: https://arxiv.org/abs/2308.14659

We can therefore rely on the established position:

> **Embedding fidelity is neither perfect nor unknowable; it can be measured.**

This project should report structural fidelity as a validation metric, but graph reconstruction is not itself the research contribution.

---

## 5. Research gap

Existing research establishes several individual pieces:

\[
\text{formal mathematical states can be embedded;}
\]

\[
\text{latent mathematical representations can support operations;}
\]

\[
\text{proof transitions exhibit measurable geometry;}
\]

\[
\text{alternative proofs contain different useful information;}
\]

and

\[
\text{embedding fidelity can be quantified.}
\]

The literature reviewed so far does **not** appear to perform the following composition:

\[
\boxed{
\text{many proofs of theorem }T
\rightarrow
\text{embed every intermediate state independently}
\rightarrow
\text{remove paths and connectivity}
\rightarrow
X_T
}
\]

followed by comparison of:

\[
X_A,\;X_B,\;X_C,\ldots
\]

as theorem-associated geometric objects.

The novelty claim should remain precisely this narrow.

---

## 6. Main hypotheses

### H1 — Theorem geometry exists

Independent samples of proofs for the same theorem will generate more similar state clouds than appropriately controlled samples from different theorems:

\[
D(X_T^A,X_T^B)
<
D(X_T^A,X_U).
\]

If this fails, the fundamental object \(X_T\) is unstable and the strong conjecture fails.

### H2 — Geometry is not merely syntax

Same-theorem reproducibility will survive controls for:

- notation;
- definition files;
- theorem statement similarity;
- shared premises;
- proof-search algorithm.

### H3 — Cross-theorem geometry contains additional mathematical information

Some theorem pairs will show geometric similarity or local overlap that cannot be explained by statement embeddings, domain labels, shared definitions, shared tactics, or direct dependency.

### H4 — Shared regions are mathematically meaningful

When statistically significant cross-theorem intersections are inspected, they will correspond more often than chance to identifiable common mathematical structures.

---

## 7. Phase 0 — Cheap synthetic validation

Before extracting a large multi-proof corpus, validate the measurement pipeline on synthetic data where the ground truth is known.

Generate synthetic point-cloud families containing:

- identical underlying shapes with different samples;
- partially overlapping shapes;
- completely different shapes;
- unimodal and multimodal distributions;
- structures with holes or branches;
- varying noise levels;
- realistic embedding dimensionalities.

The synthetic study must explicitly sweep the two quantities that determine whether the later theorem-cloud experiment is statistically feasible:

- \(m\): number of independent proofs sampled per theorem;
- \(n\): number of retained states per proof.

It should also sweep embedding dimension \(d\), including dimensions representative of the encoders likely to be used later.

Run exactly the same metrics intended for the mathematical experiment.

Candidate metrics include:

- maximum mean discrepancy;
- Wasserstein distance;
- neighborhood overlap;
- energy distance;
- persistent-homology summaries.

All comparisons use **equal-size or size-matched clouds**.

The objective is not merely to show that a metric works in principle. Phase 0 must estimate its statistical power as a function of:

\[
(m,n,d,\text{noise},\text{effect size}).
\]

For each candidate metric and synthetic structure family, estimate the smallest \(m\times n\) sampling regime that can reliably distinguish two samples from the same generating structure from samples of genuinely different structures. The default minimum-viability threshold is **80% power at \(\alpha=0.05\)** for the pre-specified synthetic alternatives.

Phase 0 therefore produces a concrete deliverable:

> **A minimum viable proof/state sampling envelope for each candidate metric.**

That envelope determines the corpus budget in Phase 1. If the required number of proofs or states per theorem is not realistically obtainable, the metric is dropped before expensive proof generation begins. If no candidate metric has acceptable power at feasible sample sizes, stop and redesign the project.

Persistent-homology metrics receive no special status: if their minimum viable sample size is impractical at the intended dimensionality, they are excluded from the primary experiment.

Metric choices, power thresholds, dimensionality safeguards, and significance procedures should be frozen after Phase 0.

---

## 8. Phase 1 — Build the multi-proof corpus

A major limitation of existing formal libraries is that they normally store only one proof of a theorem.

Therefore, \(X_T\) cannot be interpreted as:

> all possible states belonging to theorem \(T\).

It is:

> all states observed in the sampled proof population.

To reduce sampler bias, generate alternative proofs using **at least two substantially different proof-search systems from the beginning**.

For each theorem:

\[
P(T)
=
P_1(T)\cup P_2(T)
\]

where \(P_1\) and \(P_2\) come from different search strategies.

Lean verifies every accepted proof.

This lets us distinguish:

\[
\text{theorem structure}
\]

from:

\[
\text{one prover's preferred basin of search}.
\]

### Corpus size is determined by Phase 0

Phase 1 is not allowed to choose an arbitrary convenient number of proofs per theorem. The acquisition target is derived from the minimum viable \(m\times n\) envelope established in Phase 0.

A small pilot should first measure the empirical distributions of:

- proof length;
- retained states per proof;
- proof yield per theorem;
- proof diversity after deduplication.

Those observations are then checked against the Phase 0 power curves. If the required sampling depth is not economically or computationally attainable for a sufficiently large theorem set, the study must narrow its metrics or stop rather than proceed underpowered.

### Cross-prover depth and length matching

Different proof systems may systematically produce proofs of different lengths and explore states at different depths. A failure of cross-prover reproducibility could therefore reflect trivial sampling differences rather than different theorem geometry.

For every retained state, record at least:

- total proof length;
- raw state depth;
- normalized state depth \(u=i/(L-1)\), where \(i\) is the state's position and \(L\) is proof length.

Primary cross-prover comparisons must use matched or reweighted samples so that proof-length and state-depth distributions are comparable between provers. Unmatched comparisons may be reported as secondary diagnostics but cannot be the primary evidence for or against theorem-specific geometry.

---

## 9. Proof diversity and deduplication

This is load-bearing.

Fifty syntactic variants of one proof cannot count as fifty independent samples.

Before examining the geometric results, define and freeze a diversity rule using information **outside the learned state geometry**.

Possible ingredients include:

- normalized proof-term identity;
- premise sets;
- tactic sequence;
- structural proof-tree differences;
- exact normalized state-sequence duplication.

The rule must not depend on whether two proofs are geometrically near one another, because that would make the later geometry test circular.

Results should also be repeated under several reasonable deduplication thresholds as a robustness analysis.

---

## 10. Phase 2 — Learn state representations

Train or select an encoder:

\[
E(S)\rightarrow z.
\]

The encoder must not receive:

- theorem identity;
- final theorem destination;
- proof order;
- previous or next state;
- proof graph edges;
- knowledge that two states belong to the same theorem.

Otherwise the desired theorem geometry is being explicitly manufactured.

The encoder should operate only on the formal content of an individual mathematical state.

A second encoder with materially different architecture or training objective should eventually replicate the central findings.

However, replication across two encoders trained on the same Lean corpus is only a **limited robustness check**, not evidence of representation independence. The encoders still share training data, notation, library structure, and potentially similar inductive biases.

If the initial result is positive, the stronger follow-up is replication with an encoder that differs not only in architecture but also materially in training objective and/or training corpus. The project should therefore distinguish:

1. **same-corpus robustness** — useful for detecting architecture-specific artifacts;
2. **cross-training robustness** — stronger evidence that the observed geometry is not merely inherited from one representation-learning regime.

Agreement between encoders is never treated as proof of an objective mathematical geometry; disagreement is evidence that the apparent structure is representation-sensitive.

---

## 11. Syntax and vocabulary controls

A serious confound is that states from the same theorem naturally contain related notation, definitions, and local hypotheses.

Therefore comparisons must include difficult controls.

A theorem's cloud should be compared not only against random theorems, but against:

- theorems from the same Lean file;
- theorems using overlapping definitions;
- theorems with similar statement embeddings;
- theorems with similar hypothesis structures;
- theorems from the same mathematical domain.

The question is not whether states from theorem \(T\) resemble one another.

The question is whether they resemble one another **more than these simpler explanations predict**.

---

## 12. Phase 3 — Does theorem geometry reproduce?

This is the decisive first mathematical experiment.

Split the proofs of each theorem:

\[
P(T)=P_A(T)\cup P_B(T)
\]

without overlap.

Construct:

\[
X_T^A,\qquad X_T^B.
\]

Perform this both:

- within each prover;
- across provers.

The strongest result would be:

\[
D(X_{T,P_1},X_{T,P_2})
<
D(X_{T,P_1},X_{U,P_2})
\]

despite the samples being produced by different proof-search systems.

That would indicate that something theorem-specific is surviving differences in how the states were discovered.

Matched null clouds must contain equal numbers of states.

For cross-prover tests, the **primary analysis uses the proof-length/state-depth matching procedure defined in Phase 1**. This prevents one prover's tendency to produce shorter, deeper, or otherwise differently distributed trajectories from masquerading as geometric disagreement.

The report must show both matched and unmatched results. A signal that exists only before matching is interpreted as prover-distribution structure, not theorem geometry.

---

## 13. Phase 4 — Does the geometry add information?

Compare theorem-cloud representations against simpler baselines:

- theorem-statement embeddings;
- premise overlap;
- definition overlap;
- mathematical-domain labels;
- tactic histograms;
- one sampled proof;
- mean state embedding;
- full trajectory representations where available.

This prevents an elaborate geometric representation from receiving credit for information obtainable from a single centroid or obvious textual similarities.

The state-cloud hypothesis gains value only if:

\[
X_T
\]

captures information unavailable to materially simpler representations.

---

## 14. Phase 5 — Cross-theorem intersections

Now test the motivating conjecture.

The pair-testing universe must be defined **before any geometric overlap scores are examined**.

### Confirmatory comparison universe

Let \(\mathcal{U}\) contain every unordered theorem pair in the held-out evaluation set that satisfies all pre-committed non-geometric eligibility rules, including:

- both theorems meet the Phase 0 minimum viable sampling requirement;
- low theorem-statement similarity under a threshold fixed before Phase 5;
- no direct dependency between the theorems;
- definition/premise overlap below a pre-specified threshold;
- cross-domain status where domain labels are available and sufficiently reliable.

The exact thresholds and domain rules must be frozen before geometric pairwise testing begins.

Every pair in \(\mathcal{U}\) is tested. Pairs may not be added or removed after inspecting theorem-cloud geometry.

False-discovery-rate correction is applied across **this entire confirmatory comparison universe**. The number of hypotheses in the FDR procedure is therefore fixed by \(|\mathcal{U}|\), not by a hand-selected shortlist.

A separate all-pairs or relaxed-filter analysis may be performed, but it must be labeled exploratory and corrected within its own explicitly defined hypothesis family.

Only statistically surviving confirmatory pairs are inspected mathematically for the primary claim.

The key question becomes:

> What mathematical structure accounts for two apparently unrelated theorem clouds occupying part of the same latent territory?

---

## 15. What would constitute a major result?

Suppose theorem \(A\) concerns an algebraic problem and theorem \(B\) concerns something apparently unrelated in geometry.

Their statement embeddings are distant.

Their notation differs.

They share few dependencies.

Yet:

\[
X_A
\]

and

\[
X_B
\]

contain highly similar substructures.

Inspection then reveals that these regions correspond to states involving the same deeper mathematical relationship—perhaps symmetry, ordering, decomposition, invariant preservation, induction, equivalence transformation, or something less easily named.

That would suggest that the representation has captured a mathematical relationship not obvious from the conventional descriptions of the theorems.

Even more interesting would be discovering a recurring structure:

\[
M\subset X_{T_1},X_{T_2},\ldots,X_{T_n}
\]

across many unrelated theorem families.

That would be evidence for what might be called a **latent mathematical motif**.

---

## 16. Graph fidelity as validation, not objective

The original proofs still provide known graph structure.

Because previous research establishes that graph topology is recoverable from embeddings to varying degrees, we can measure how much of that known structure our encoder retains.

This tells us whether our representation is:

- highly structurally faithful;
- moderately lossy;
- severely lossy.

But the project does not require perfect graph reconstruction.

The theorem-cloud hypothesis specifically asks whether meaningful aggregate geometry survives **after connectivity is discarded**.

This analysis is **optional and non-gating**. If time or compute is constrained, it may be omitted without weakening the primary test of theorem-cloud reproducibility and cross-theorem overlap.

---

## 17. Kill criteria

The strong hypothesis should be rejected or substantially weakened if:

1. Independent proof samples from the same theorem do not reproduce similar geometry.
2. Same-theorem similarity disappears across different proof generators.
3. Same-file or same-definition controls explain the apparent theorem geometry.
4. Cloud geometry provides no information beyond a centroid or theorem-statement embedding.
5. Cross-theorem overlaps do not survive multiple-comparison correction.
6. Apparent shared structures fail to reproduce with another encoder.
7. Phase 0 shows that the chosen metrics cannot reliably detect known structures at a feasible minimum \(m\times n\) sampling regime.
8. The Phase 0 minimum viable proof/state sampling envelope cannot be achieved for a sufficiently large theorem set within the corpus budget.
9. Cross-prover reproducibility disappears after proof-length and state-depth distributions are matched.

These should be treated as genuine falsification conditions, not problems to optimize away after seeing the results.

---

## 18. Navigation is follow-on research

Using the geometry to prove new theorems is attractive but should **not** be part of the primary project.

If the geometry is real, a new conjecture could eventually be embedded and compared with known theorem regions:

\[
E(C)\rightarrow
\{X_{T_1},X_{T_2},\ldots\}.
\]

That might identify mathematical territory through which a successful proof is likely to pass.

But proving that would require an additional retrieval and theorem-proving system and would confound the scientific question with engineering quality.

Navigation should therefore be treated as a second project unlocked by positive results here.

---

## 19. Interpretation of possible outcomes

### Strong positive

The same theorem produces reproducible geometry across proof samplers and encoders, and portions of that geometry recur meaningfully across unrelated mathematics.

This supports the existence of higher-order organization in mathematical state space.

### Moderate positive

Theorem clouds reproduce reliably, but most cross-theorem structure corresponds to already-known mathematical classifications.

The representation is still valuable, but it is rediscovering known organization rather than exposing a new one.

### Domain-local result

Theorem geometry exists within individual areas of mathematics but does not generalize strongly across domains.

This would imply that mathematical state spaces have domain-specific rather than universal geometry.

### Negative

The apparent geometry is dominated by prover behavior, notation, syntax, or sampling noise.

That would reject the strong conjecture and establish an important limitation of latent representations of formal mathematics.

---

## 20. Potential significance

A successful result would not establish that mathematics possesses one objectively correct Euclidean geometry.

It would establish something narrower:

> **When formal mathematical states are represented independently, the collections of states encountered across alternative proofs exhibit reproducible geometric organization that contains mathematical information not reducible to proof paths, syntax, or theorem statements.**

The strongest speculative possibility is that mathematical concepts themselves sometimes correspond not to individual propositions but to **recurring structures in state space**.

Under that interpretation, two proofs can be unrelated as trajectories yet traverse some of the same conceptual territory.

The theorem cloud captures the territory rather than the route.

---

## 21. The project in one diagram

\[
\boxed{
\begin{array}{c}
\text{many independently generated proofs}\
\downarrow\
\text{extract every mathematical state}\
\downarrow\
E(S)\rightarrow z\
\downarrow\
\textbf{discard order, edges, and proof identity}\
\downarrow\
X_T=\{z_1,z_2,\ldots,z_n\}\
\downarrow\
\text{test whether }X_T\text{ is reproducible}\
\downarrow\
\text{compare theorem geometries}\
\downarrow\
\text{identify statistically significant shared regions}\
\downarrow\
\text{ask what mathematical ideas those regions represent}
\end{array}
}
\]

## Final thesis

**A theorem may be representable not merely as a proposition or a proof path, but as the region of mathematical state space sampled by its alternative proofs. Recurring intersections between these theorem-associated regions may reveal latent mathematical structures shared across problems that appear unrelated at the level of statements, notation, or proof trajectories.**
