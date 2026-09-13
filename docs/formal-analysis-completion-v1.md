# Pre-embedding analysis completion specification

This supplement fills missing reporting and validation details in the already
committed formal feasibility protocol. It is fixed before the recovered corpus
is embedded. It does not alter eligibility, the primary seed, sample budgets,
metrics, alpha, or feasibility thresholds.

## Audit and uncertainty

Check generated proof sources, canonical proof hashes, verifier axiom evidence,
state hashes, normalized duplicate sequences, and exact disjoint split assignments.
Archive the eligible population and split manifest before embedding. Proof IDs
are interpreted within their theorem because the same local premise name can
denote different formulas in different declarations. No representations are
trained or calibrated on the evaluation theorems; the general-text pretraining
data cannot be exhaustively audited, so absence of pretraining contamination is
not established.

Use 2,000 fixed-seed theorem-cluster bootstrap draws for pairwise win rates,
paired cloud-minus-centroid improvements, and matched/mismatched distance gaps.
Each draw resamples theorem identities on both axes together; duplicate copies
of the same theorem are never counted as mismatched pairs. These percentile
intervals describe variation over this generated population conditional on the
observed proof samples. They are exploratory, not simultaneous intervals or
guarantees about mathematics at large. Supplement with proof/state sampling
sensitivity at seeds 316843 and 316844, keeping budgets and eligibility fixed.
Report their results descriptively, without new significance tests.

The primary whole-theorem permutation test presumes gallery labels are
exchangeable under independence in the generated population. Every theorem has
the same file, domain, atom count, number of premises, and conclusion. Remaining
premise-network differences can violate scientific comparability; full-context
significance alone cannot establish H2. Goal-only and statement controls expose
this limitation. Permutation significance is conditional on the sampled clouds.

## Baselines and diversity sensitivities

Retain the original syntax/truth/text, full/goal, cross/within comparisons and
their single BH family. Add descriptive premise/definition overlap, tactic
histograms, domain/file/hypothesis controls, and a trajectory summary baseline
(mean embedding, mean step displacement, mean step length). These audit features
never reach the state encoder or primary cloud metric. All baseline comparisons
use the same theorem identities and proof selections as the primary comparison.

Repeat cross-generator ranking descriptively after two stricter nongeometric
deduplication policies: identical used-premise sets, and identical tactic-category
histograms. A signature shared by generators is excluded from both sides; within
each side retain the hash-first proof. Do not lower the 32-proof eligibility gate
when the stricter policies leave insufficient data. Report counts and skipped
results. These are sensitivity analyses, not a search for a favorable threshold.

## Fidelity and intersection decision

For one hash-first proof per theorem/generator, reconstruct the backward proof
tree's parent/child edges aligned to actual Lean tactic records, and the forward
script's dependencies between named derived facts. Exclude removed initial
states, use undirected edges for distance ranking, and report the within-proof
edge-versus-nonedge distance AUC by encoder/view, aggregated first within theorem.
Graphs are external validation targets. Goal-focused Lean records do not include
all sibling goals, and the two graph types are operationally different; no full
Lean-kernel graph-fidelity claim follows. Missing alignments must be reported.

If the existing feasibility gate fails, Phase 5 terminates with no candidate
mining, no mathematical pair interpretation, and H3/H4 untested. The frozen
downstream design, usable only after a new adequate cross-domain study, requires
low statement similarity, different domains, little dependency, an explicitly
matched pair-label null, a single BH family for the entire candidate search,
held-out replication, and blinded mathematical review against matched chance
pairs. A reviewer must be unaware of significance status and encoder identity;
independent reviewers label a prespecified structure taxonomy with agreement
and chance-adjusted rates. This corpus has one domain and therefore supplies no
eligible cross-domain candidate family regardless of the feasibility result.
