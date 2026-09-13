# Literature and scope audit

Checked against primary publication pages on 2026-09-13. The original research
plan is preserved unchanged; this note records what the cited evidence supports.
This is a bounded reference check, not a systematic review establishing novelty.

| Source | Supported connection | Boundary for Noema |
|---|---|---|
| [Mathematical Reasoning in Latent Space](https://research.google/pubs/mathematical-reasoning-in-latent-space/) | Learned representations support nontrivial predictions about repeated higher-order-logic rewrites. | This does not establish that unordered samples from independent proofs form reproducible theorem objects. |
| [Samoylov and Vosoughi, Representing Lean Proofs as Trajectories in Latent Space](https://aclanthology.org/2026.acl-srw.105/) | Contextualized state-change representations outperform a matched syntax control on held-out tactic retrieval and support trajectory measurements. | The authors describe a small, short-proof-heavy population. Their transition/context encoder is not a drop-in state-content-only encoder for this experiment. |
| [Kühlwein and Urban, Learning from Multiple Proofs: First Experiments](https://citeseerx.ist.psu.edu/document?doi=f6dbc7e8a1efca9e8b1c252e1bdd0ed810960993&repid=rep1&type=pdf) | Alternative proofs affect learned premise selection and ATP performance; proof quality matters. | This motivates diversity auditing, not an assumption that different proof scripts are independent samples. The indexed paper abstract was available; direct PDF retrieval was intermittent. |
| [Liu et al., How much topological structure is preserved by graph embeddings?](https://doiserbia.nb.rs/Article.aspx?ID=1820-02141900011L) | Reconstruction, link-distribution, community and link-prediction evaluations reveal partial preservation. | Fidelity must be measured for the actual representation; published graph-embedding results cannot qualify Noema's encoders. |
| [Yip et al., RESTORE](https://arxiv.org/abs/2308.14659) | Intrinsic reconstruction evaluates topological and semantic information retained by graph embeddings. | A local edge-ranking diagnostic is narrower than complete graph reconstruction or a topology claim. |

The ACL citation now has an exact article URL, rather than only a proceedings
volume. Its object is a sequence of state changes; Noema's primary object remains
individual state content pooled after proof splitting. This distinction survives
the source check. None of these sources establishes H1–H4 for the present corpus.

Bounded searches included the exact paper titles, `theorem point clouds proofs
geometry embedding`, `theorem unordered proof embeddings geometry`, `theorem
clouds proofs`, and site-restricted Lean/proof-state/multiple-proof searches in
arXiv and ACL Anthology. The results did not establish a prior implementation of
the exact proposed composition. Search noise was substantial and this is **not**
evidence sufficient for a first-of-its-kind claim. The research gap remains a
working hypothesis. No novelty or broad mathematical discovery claim is made.

The selected forward and backward searches are inspectable algorithms over one
constructive fragment, and Lean's pinned standard library is sufficient to check
them. They establish a CPU-feasible two-strategy corpus, not robustness across
large general-purpose learned provers. The quantized general-text model is a
pretrained representation baseline; the exact truth-table encoder supplies a
materially different denotational control. Neither should be described as a
validated learned mathematical state encoder.
