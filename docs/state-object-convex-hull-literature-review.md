# State objects, convex hulls, and mathematical overlap

The convex hull is a defensible first definition of a theorem's State object.
It gives a precise version of the rubber-band intuition, preserves an extended
object, and permits direct tests of intersection. Existing research supports
representing concepts as regions and learning useful representations of formal
reasoning. It does not establish that the convex hull of states from multiple
proofs corresponds to a theorem's mathematical content.

The most useful next investigation would therefore ask whether this particular
region definition produces reproducible, interpretable intersections. A new
prediction contest against a centroid would not answer that question. The
literature also identifies two distinctions that must be kept explicit:
the geometry imposed by the construction versus the geometry supported by the
data, and mathematical relationships versus relationships learned for a specific
encoder training task.

This review covers relevant primary publications available through September 14,
2026. It combines formal-proof representation research, conceptual and ontology
semantics, and convex geometry. The recommendations and elementary deductions
below are analytical conclusions, not reported experimental findings. No new
State-object intersection experiment is reported here.

**The proposed object.** Let a proof state contain the formal local context and
the current goal or goals. Let a fixed encoder map that state to a vector. Gather
states across the sampled proofs of theorem T, discard their order for the
geometric representation, and call the resulting finite set of vectors Z_T.
The proposed State object is

\[
X_T=\operatorname{conv}(Z_T).
\]

This includes the enclosure's interior and boundary. It is not just a tour
through the points or the boundary surface. Every nonnegative weighted
combination of the vectors whose weights sum to one belongs to the hull; the
collection of all such combinations is the object. The convex hull is the
smallest convex set containing the samples. In 2D it is the familiar rubber-band
enclosure. Higher-dimensional hulls extend that definition without requiring a
new surface-area minimization claim. [1](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf)

The choice adds an assumption: space between observed states belongs to the
object. An interior location need not decode to a valid formal state. That is
acceptable for a geometric abstraction, provided intersection is initially
interpreted as geometric evidence rather than as a new mathematical theorem.

| Term | Meaning in this investigation |
|---|---|
| Proof state | Context and outstanding goal or goals at one point in a proof |
| State vector | One encoding of one proof state |
| State object | The convex hull of vectors gathered across proofs of one theorem |
| Intersection | At least one location belongs to both hulls; contact counts |
| Containment | Every location in one hull belongs to the other |
| Connectivity | Objects are joined directly or through a chain of intersections |
| Volume overlap | A stronger, dimension-dependent question than nonempty intersection |
| Geometric witness | Weighted combinations of sampled states demonstrating an intersection |

**Concepts as regions: the closest conceptual precedent.** Peter Gärdenfors's
*Conceptual Spaces* introduced a geometric account of concepts between symbolic
and connectionist representations. His 2024 treatment states a convexity
constraint for natural properties: if two instances possess a property, instances
between them should possess it too, within the relevant domain. His account of
concepts spans domains and their relations; it should not be reduced to a claim
that every concept is one arbitrary Euclidean hull.
[2](https://direct.mit.edu/books/monograph/2532/Conceptual-SpacesThe-Geometry-of-Thought),
[3](https://link.springer.com/article/10.1007/s11406-024-00734-4)

The useful connection is that an idea can have extent, boundaries and relations
to other regions. A center is not a necessary definition of its meaning.
The important limitation is that perceptual quality dimensions and a learned
1,472-coordinate proof-state embedding are different constructions. This
literature supplies a conceptual rationale for testing convexity; it does not
supply evidence that mathematical reasoning is convex in the existing encoder.

**Geometric semantics: encouraging results with explicit assumptions.**
Gutiérrez-Basulto and Schockaert study relations represented as regions and show
limitations of familiar translation and bilinear embeddings. Their convex-model
existence result applies to quasi-chained ontologies with finite models; broader
consequences require the relevant finite-model conditions. This is a constructive
result about representing specified logical structures, not evidence that an
off-the-shelf neural representation discovers those structures.
[4](https://arxiv.org/html/1805.10461)

Lacerda, Ozaki and Guimarães subsequently prove strong faithfulness for a
specified normalized description logic, ELH, using convex geometric models.
They distinguish an embedding's ability to fit observations from its ability to
respect the ontology's logical consequences. That distinction is directly useful
here: attractive geometric overlap would need an independent mathematical
interpretation. Their existence theorem does not imply faithfulness for arbitrary
Lean theorems, arbitrary dimensions, or the hull of observed proof-state vectors.
[5](https://drops.dagstuhl.de/storage/08tgdk/tgdk-vol002/tgdk-vol002-issue003/html/TGDK.2.3.2/TGDK.2.3.2.html)

Query2box provides an empirical example of replacing point representations with
regions. Ren, Hu and Leskovec represent knowledge-graph queries using boxes and
use intersections to model conjunction. Its query-answering results demonstrate
that regions can serve a practical reasoning task. However, these are trained
query representations tied to sets of answer entities, not enclosures of states
from alternative proofs. The useful idea is the evaluation discipline: define
what membership and intersection should mean, then test those meanings.
[6](https://arxiv.org/html/2002.05969)

Schockaert's analysis of embeddings as epistemic states also addresses the earlier
temptation to call a pooled vector accumulated knowledge. Standard pooling
operators satisfy a proposed evidence-combination principle only under specific
dimensional and representation constraints. This neither rules out all averaging
nor validates the particular centroid used in the completed experiment. It
supports requiring an explicit semantic argument before interpreting a numerical
aggregation as the knowledge of a theorem.
[7](https://orca.cardiff.ac.uk/id/eprint/161290/)

**Formal mathematics: what the neighboring studies actually represent.**
Lee, Szegedy, Rabe, Loos and Bansal train graph-based representations of HOL Light
formulas to predict rewrite success and representations of rewrite results. They
find that useful rewrite predictions survive several approximate latent reasoning
steps. This is evidence that formal mathematical embeddings can retain operational
information. It is not a Lean-trained model, and it does not study a theorem as
an unordered region assembled from multiple proofs.
[8](https://arxiv.org/html/1909.11851)

LeanDojo supplies extraction tools and ReProver, whose retriever learns from proof
states paired with relevant premises, using contrastive training. Its official
implementation provides a Lean 4 proof-state-to-embedding model. This makes it a
reasonable available encoder for an exploratory check. Its training target is
premise retrieval, however, not between-theorem convexity or preservation of
topology. Similar premise needs could shape the space even where the deeper
mathematical relationship differs.
[9](https://arxiv.org/html/2306.15626),
[10](https://github.com/lean-dojo/ReProver)

Kühlwein and Urban's *Learning from Multiple Proofs* studies how alternative
human and automatically found proofs affect premise selection. Different proof
choices materially affect success, and their experiments favor proof quality
over simply adding quantity. This supports treating proof diversity as potentially
informative. It does not establish that thousands of intermediate vectors give
thousands of independent observations, or that their convex hull converges to a
theorem's intrinsic region. The workshop was PAAR 2012; the proceedings publication
is dated 2013.
[11](https://easychair.org/publications/paper/Pc)

Samoylov and Vosoughi's ACL 2026 paper is the closest direct proof-geometry
neighbor in the original plan. It embeds local state changes and studies ordered
proof trajectories, including path length, span, curvature and torsion. The
dataset slice contains 13,517 proofs and 25,214 steps; 58.3% of proofs contain
one tactic. The paper explicitly limits its conclusions because of short proofs
and because its main representations encode transitions rather than states.
It supports examining formal-proof geometry and checking it against surface
controls. It does not establish intersections between theorem State objects.
[12](https://aclanthology.org/2026.acl-srw.105.pdf)

A newer relevant preprint is Mendoza-Smith's *Geometric Measurements of the Axiom
of Choice in Neural Proof Embeddings*, submitted June 26, 2026. It reports
geometric differences associated with kernel-tracked axiom dependence, using
42,355 traced theorems and controls for proof length, file, author and topic.
Its representations aggregate proof sequences, with additional full-source
checks. It does not estimate hulls of intermediate states from multiple proofs.
The useful idea is validation against an independently obtained formal property.
Actual dependence of a particular proof on an axiom also does not show that the
theorem necessarily requires that axiom. These are reported preprint findings,
not independently reproduced results of this project.
[13](https://arxiv.org/html/2606.28572)

| Research line | Represented entity | Useful contribution | Missing link for State objects |
|---|---|---|---|
| Conceptual spaces | Properties and concepts as regions | Rationale for spatial extent and betweenness | Convexity in a learned proof-state space |
| Convex ontology models | Logical concepts or relations | Explicit geometric semantics and faithfulness conditions | Discovery from observed Lean proof states |
| Query2box | Query answer sets | Empirical use of region intersection | Multi-proof theorem representation |
| Lee et al. | Formal formulas | Useful latent rewrite information | Region-level overlap |
| LeanDojo / ReProver | States and premises | Available mathematical encoder and extraction | Geometry suitable for hull interpretation |
| Kühlwein–Urban | Alternative proofs' premise evidence | Proof choice can add information | Occupied regions and topology |
| Samoylov–Vosoughi | Ordered state changes | Descriptive geometry of proof organization | Unordered states across many proofs |
| Mendoza-Smith | Whole-proof representations | Independent axiom-based validation target | Per-theorem state hulls |

The reviewed sources do not establish the full composition: many alternative
proofs of one theorem, independently encoded intermediate states, removal of
proof order, convex enclosure, and independently validated intersections between
theorems. That is a bounded literature finding, not a claim of exhaustive novelty.

**Convex optimization provides the direct test.** Bennett and Bredensteiner show
the geometric relationship between separable support-vector classification and
closest points of two convex hulls. This offers a useful computational connection:
disjoint finite hulls admit a strict separating hyperplane, while intersecting
hulls have minimum distance zero. Their reduced-hull treatment adds parameters
for a different purpose; ordinary hulls suffice for the proposed first check.
[14](https://www.robots.ox.ac.uk/~cvrg/bennett00duality.pdf)

For sample matrices A and B with state vectors as columns, an intersection exists
exactly when the following system has a solution:

\[
A\alpha=B\beta,\qquad
\alpha,\beta\geq0,\qquad
\mathbf1^\top\alpha=\mathbf1^\top\beta=1.
\]

This follows immediately from the definition of the two hulls. The shared
location A alpha = B beta is an intersection witness. The coefficients identify
the sampled states responsible for that witness. They are a certificate for
this one intersection, not a replacement of either object by a center.
Linear-programming software can solve equality constraints with nonnegative
variables directly. A numerical implementation must independently check residuals
and weight constraints, and verify separating inequalities for a disjoint result.
An ambiguous tolerance-scale answer should be reported as unresolved.
[15](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html)

This formulation is attractive because it does not require enumerating every
face of a high-dimensional hull. A nearest-hull-point optimization can separately
quantify a positive gap. Gap size describes separation of the closest portions;
it does not by itself describe overlap extent or mathematical relatedness.

**What topology remains after choosing convex hulls.** Every nonempty convex
object can be continuously contracted to any one of its points by straight-line
motion. Thus each individual hull is connected and has no topological holes.
Those properties are imposed by the definition. They cannot become discoveries
about the theorem.

The interesting topology moves to the arrangement of multiple objects. Bauer,
Kerber, Roll and Rolle provide a nerve theorem for finite covers by closed convex
sets. Their result relates the homotopy type of the union to the nerve: a
combinatorial record of which collections have a common intersection. This applies
to finite theorem hulls without adding neighborhoods around the state vectors.
[16](https://arxiv.org/pdf/2203.03571)

For the first investigation, a table of pairwise intersections already answers
whether objects connect through chains. Later, common intersections among three
or more objects could identify shared regions. Pairwise overlap alone does not
prove a common overlap of the entire group: three line segments forming a
triangle meet in pairs but have no point shared by all three. The union has a
loop. Adding a filled triangle to the nerve merely because its three edges exist
would erase that loop incorrectly. The relevant relation is common intersection,
not just pairwise acquaintance.

This overlap graph is a derived description of relations between theorem objects.
It does not restore tactic edges or proof order inside the State object.

**Four elementary deductions that affect experiment design.** The following
arguments are mathematical consequences of the proposed construction and the
saved representation. They are not measurements of the saved theorem pairs.

First, sample count bounds affine dimension. For n vectors, every point of their
hull has the form z_1 plus a linear combination of the n-1 differences z_i-z_1.
Its affine dimension is therefore at most n-1. With the current eight retained
states, it is at most seven, even in 1,472-dimensional embedding space. Duplicates
can reduce it further. Such a hull has zero 1,472-dimensional volume while still
being a valid geometric object that may intersect another.

There is an even sharper sparse-sample check. If the distinct points from two
nonempty, disjoint samples are jointly affinely independent, their hulls cannot
intersect. An intersection would yield coefficients alpha and minus beta summing
to zero and giving a nontrivial affine dependence, a contradiction. Generic sets
of sixteen points can be affinely independent in 1,472 dimensions. Consequently,
finding separation among eight-point objects could reflect sparse sampling rather
than separate mathematical ideas. Whether the actual samples are independent
remains to be measured; a small numerical singular value needs careful treatment.

Second, the saved ReProver vectors are normalized to unit length. The local
encoder explicitly divides the pooled vector by its Euclidean norm. Normalized
representations on a sphere also appear in the contrastive-learning literature,
where the training objective shapes alignment and dispersion. That literature
does not imply that this particular encoder has a uniform distribution.
[17](https://proceedings.mlr.press/v119/wang20k.html),
[local implementation](../src/noema/reprover.py)

For any unit vector u and any distinct unit vector v, u dot v is less than one.
Therefore u cannot be a convex combination of finitely many distinct unit vectors
v_i: taking the dot product with u would give 1 = sum_i alpha_i (u dot v_i) < 1.
It follows that every distinct sampled unit vector is an exposed vertex of its
hull. Exact membership of a new, distinct normalized state in the old finite hull
is impossible. Floating-point computations approximate this ideal statement.

This rules out exact held-out-state containment as a sensible validation target
for these normalized finite samples. It also means hull containment between two
finite sets of distinct unit vectors occurs only if every vector in the smaller
set is present in the larger set. These are limitations of particular questions,
not a proof that different hulls must be disjoint.

For example, the hull of {(1,0),(-1,0)} intersects the hull of {(0,1),(0,-1)} at
the origin. All four vectors have unit length and none is shared. Thus hulls can
intersect through mixtures even when they share no observed state. It would be
misleading to describe that interior intersection as an observed common state.

Third, projection can manufacture apparent intersections. Consider one triangle
at height z=0 and the identical triangle at height z=1. They are disjoint in 3D,
but their shadows on the xy plane coincide. More generally, for a linear
projection P, P(conv Z)=conv(PZ), and a shared point stays shared after projection.
The converse fails. Therefore separation in a common linear projection certifies
original separation, while overlap in a 2D projection does not certify original
overlap. Separate per-theorem projections cannot be compared as one geometry.

Fourth, collecting additional states enlarges a hull monotonically. If Z is a
subset of Z', then conv Z is a subset of conv Z'. Once two cumulatively enlarged
objects intersect, adding states cannot undo that intersection. Early disjointness
is provisional; an observed intersection persists under additions with the same
fixed encoder. This offers a direct way to study acquisition without a radius:
record when each intersection first appears as proofs are added. It does not
show that the acquired states exhaust all relevant proof approaches.

**Intersections need a mathematical interpretation.** A shared encoded state is
the strongest immediate provenance: the same formal configuration occurs in both
sampled collections. Even that can be trivial. A universal terminal string such
as “no goals” would force every object containing it to intersect. Two independently
sampled proof groups of the same theorem can also share the identical initial
goal, making their hull intersection automatic. These contacts should be labeled
as shared states rather than presented as discovered latent reasoning structure.

An intersection with no shared state is different. It shows that mixtures of
different observed states coincide in the representation. Its mathematical value
requires reading the contributing states or testing an independently specified
relationship. The geometric certificate alone does not decode a common lemma,
show theorem equivalence, or establish that one theorem implies another.

Proof-state serialization matters for the same reason. Local variable names,
unused hypotheses, enclosing theorem identifiers and the choice of displayed
goals can shape the vectors. Removing all context would change what a state
means, so it is not a justified automatic repair. A better diagnostic is to check
mathematically harmless renamings and to record exactly which context is encoded.
Different encoders define different coordinate spaces; their raw vectors must
not be combined into a single hull.

Finally, unlimited proof enumeration is not a neutral population definition.
A proof can include irrelevant established facts and detours while still proving
the same theorem. Those states could enlarge a hull without adding information
about its central argument. A finite, documented acquisition procedure is part
of the interpretation of the object. Proof diversity, proof length and state
coverage should be reported separately. Thousands of vectors are not by
themselves evidence of thousands of distinct reasoning contributions.

**A small investigation suggested by the review.** The recommended first study
is a descriptive geometry audit using the frozen encoder and saved vectors. It
should produce interpretable certificates and a clear account of sampling limits.
No new prediction-accuracy gate or minimum percentage improvement is needed.

| Check | Concrete output | Why it matters |
|---|---|---|
| Geometric sanity examples | Correct separation, contact, interior overlap and projected false overlap | Establish that the intersection procedure answers the intended question |
| Existing assigned pairs | Intersection status for all 1,024 anchor-candidate comparisons | Avoid selecting favorable theorem pairs |
| Affine dimension | Unique-vector counts and rank diagnostics | Distinguish sparse geometric objects from full-dimensional volumes |
| Intersection evidence | Weights and contributing state texts, or a verified separator | Make each result inspectable |
| Shared-state audit | Contacts explained by identical formal states or serialized boilerplate | Separate automatic overlap from interpolation overlap |
| Fixed projection | First assigned examples in a common 2D view, labeled with original-space results | Build intuition without letting the picture decide the answer |

The completed data can support this audit without re-encoding. It cannot support
a claim about the full region of a theorem with hundreds of proofs: it retained
two states from each of four proofs. The 1,024 assigned comparisons also do not
describe every pair among the 1,536 sampled theorems, much less connectivity of
the whole mathematical library. Any graph constructed from only those comparisons
has untested edges, not proven nonedges.

If the existing hulls are almost all disjoint and the combined samples are
affinely independent, the useful finding is that this sampling regime offers
little opportunity for exact overlap. It would not refute the region idea. If
intersections occur, inspect the weighted states for the first fixed examples
and characterize every contact by the same rule. Both outcomes can clarify the
next acquisition without selecting pairs for a success narrative.

A subsequent acquisition, if warranted, should favor a small, prospectively
chosen collection of theorems with several distinct proof approaches and encode
all retained intermediate states, rather than immediately expanding theorem
count. Record cumulative hull changes as proofs are added. Use separate proof
groups to check replication, explicitly accounting for shared starting states.
Measure distance to a hull as a continuous diagnostic if useful; do not relabel
nearby disjoint hulls as intersecting by introducing an unmotivated radius.

Formal validation can then use known shared intermediate lemmas, verified state
equivalences, or proof-specific axiom dependence. The cited axiom study suggests
the last option, with the caution that dependence of a proof is not necessity
for its theorem. Validation pairs and their meanings should be chosen before
inspecting their hulls. Mathematical area alone is not a reliable negative label:
the goal is partly to find relationships across areas.

The strongest reason to continue would be reproducible, nontrivial intersections
whose contributing states exhibit a separately verifiable relationship. The
strongest reason to revise the construction would be a demonstrated mechanism
that makes intersections inevitable or impossible for reasons unrelated to that
relationship. Neither decision requires an arbitrary ten-point advantage over
a centroid. The object definition, sampling and semantic interpretation are the
questions to resolve first.

**Sources and reading priorities.** For immediate design decisions, read
Bennett–Bredensteiner for intersection/separation, Gärdenfors for the conceptual
motivation, and the closed-convex-cover nerve theorem for topology across objects.
Read the formal-proof papers to choose representations and validation targets.
The following references identify the original publications or author-maintained
implementations; preprint status is distinguished where material.

1. Stephen Boyd and Lieven Vandenberghe. *Convex Optimization*. Cambridge
   University Press, 2004. Chapter 2, especially §§2.1 and 2.5.
   [Author-hosted book](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf).
2. Peter Gärdenfors. *Conceptual Spaces: The Geometry of Thought*. MIT Press,
   2000. [Publisher record](https://direct.mit.edu/books/monograph/2532/Conceptual-SpacesThe-Geometry-of-Thought).
3. Peter Gärdenfors. “Natural Concepts and the Economics of Cognition and
   Communication.” *Philosophia* 52, 865–882, 2024. Section 3.
   [Article](https://link.springer.com/article/10.1007/s11406-024-00734-4).
4. Víctor Gutiérrez-Basulto and Steven Schockaert. “From Knowledge Graph
   Embedding to Ontology Embedding? An Analysis of the Compatibility between
   Vector Space Representations and Rules.” KR 2018. Especially Proposition 3
   and its finite-model conditions. [Paper](https://arxiv.org/html/1805.10461).
5. Victor Lacerda, Ana Ozaki and Ricardo Guimarães. “Strong Faithfulness for
   ELH Ontology Embeddings.” *Transactions on Graph Data and Knowledge* 2(3),
   article 2, December 18, 2024.
   [Paper](https://drops.dagstuhl.de/storage/08tgdk/tgdk-vol002/tgdk-vol002-issue003/html/TGDK.2.3.2/TGDK.2.3.2.html).
6. Hongyu Ren, Weihua Hu and Jure Leskovec. “Query2box: Reasoning over Knowledge
   Graphs in Vector Space Using Box Embeddings.” ICLR 2020.
   [Paper](https://arxiv.org/html/2002.05969).
7. Steven Schockaert. “Embeddings as Epistemic States: Limitations on the Use
   of Pooling Operators for Accumulating Knowledge.” *International Journal of
   Approximate Reasoning* 171, 108981, 2024; available online in 2023.
   [Author institution record and paper](https://orca.cardiff.ac.uk/id/eprint/161290/).
8. Dennis Lee, Christian Szegedy, Markus N. Rabe, Sarah M. Loos and Kshitij
   Bansal. “Mathematical Reasoning in Latent Space.” ICLR 2020;
   arXiv first submitted September 26, 2019.
   [Paper](https://arxiv.org/html/1909.11851).
9. Kaiyu Yang and coauthors. “LeanDojo: Theorem Proving with Retrieval-Augmented
   Language Models.” NeurIPS 2023, Datasets and Benchmarks.
   [Paper](https://arxiv.org/html/2306.15626).
10. LeanDojo authors. *ReProver*, official implementation, accessed September
    14, 2026. [Repository and model interface](https://github.com/lean-dojo/ReProver).
11. Daniel Kühlwein and Josef Urban. “Learning from Multiple Proofs: First
    Experiments.” PAAR 2012; *EPiC Series in Computing* 21, 82–94, published
    August 19, 2013. [Proceedings paper](https://easychair.org/publications/paper/Pc).
12. Elisaveta Samoylov and Soroush Vosoughi. “Representing Lean Proofs as
    Trajectories in Latent Space.” ACL 2026 Student Research Workshop,
    1190–1202, July 2026. Especially §§3, 4.7, 6.3 and Limitations.
    [Paper](https://aclanthology.org/2026.acl-srw.105.pdf).
13. Rodrigo Mendoza-Smith. “Geometric Measurements of the Axiom of Choice in
    Neural Proof Embeddings.” arXiv:2606.28572v1, June 26, 2026. Preprint;
    especially §1.1 and Appendix B.
    [Paper](https://arxiv.org/html/2606.28572).
14. Kristin P. Bennett and Erin J. Bredensteiner. “Duality and Geometry in SVM
    Classifiers.” ICML 2000. [Paper](https://www.robots.ox.ac.uk/~cvrg/bennett00duality.pdf).
15. SciPy contributors. `scipy.optimize.linprog`, SciPy 1.18 documentation,
    accessed September 14, 2026.
    [Documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html).
16. Ulrich Bauer, Michael Kerber, Fabian Roll and Alexander Rolle. “A Unified
    View on the Functorial Nerve Theorem and Its Variations.” *Expositiones
    Mathematicae* 41(4), 2023. Author preprint v6 dated June 2, 2025, Theorem
    3.9, consulted here. [Paper](https://arxiv.org/pdf/2203.03571).
17. Tongzhou Wang and Phillip Isola. “Understanding Contrastive Representation
    Learning through Alignment and Uniformity on the Hypersphere.” ICML 2020,
    *PMLR* 119, 9929–9939.
    [Proceedings paper](https://proceedings.mlr.press/v119/wang20k.html).
