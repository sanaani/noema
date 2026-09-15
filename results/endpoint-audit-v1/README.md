# Do different proofs have the same final embedding?

**A concrete identical-input case exists. Numerical closeness for different
Dartmouth inputs is still unresolved because the model checkpoint was not located.**

The user means the last dot in the Dartmouth proof trajectory, not a separately
embedded theorem statement. The paper defines that dot as a pooled representation
of the final before/after state change and typed edit indicators. The default
step vector excludes the tactic token itself (sections 4.5 and 4.7):
https://aclanthology.org/2026.acl-srw.105.pdf

## Identical final transition inputs

Two admitted source proofs of `lean_workbook_490`, in the same Lean4.9 environment,
prove `3 ∣ c → 3^2 ∣ 3*c → 3 ∣ c` by these scripts:

```lean
-- Proof A
intro h1 h2
simp [pow_two] at h2
exact h1

-- Proof B
intro h1 h2
simp [sq] at h2
omega
```

Their recorded states before the final tactics are byte-for-byte identical:

```text
c : ℕ h1 : 3 ∣ c h2 : 9 ∣ 3 * c ⊢ 3 ∣ c
```

Both after-states are `no goals`. Their final tactics differ, but the default
published Delta step representation is computed from the same before/after
inputs, excluding the tactic token from the pooled step representation.
**For fixed model weights and deterministic inference, these identical inputs
therefore yield identical final embeddings.** This is a consequence of input
identity under the published method, not a claimed numerical execution of the
unavailable Dartmouth model.

The stored ReProver BEFORE-state vectors also have exactly zero distance. That
separate measured fact is unsurprising given identical text. There are 500
qualifying same-environment, same-theorem different-source pairs with identical
before/after text, changed text from their initial observation on both paths, and
different final tactic strings. The example above was chosen after measurement as
the shortest combined source among those pairs; it is an illustration, not a
representative sample or an independent success criterion.

See `identical-transition-witness.json` for complete sources, original record IDs,
trace IDs, source positions, selection rule and inference scope. Same displayed
text does not establish identity of all hidden formal-State context. Nor does one
matching endpoint establish a unique theorem center, or distinguish that theorem
from different theorems in Dartmouth's anonymized transition space.

## Existing-state-encoder controls

All 5,844 archived `no goals` records, covering 813 proof records and 102 theorem
groups, have bitwise-identical stored vectors (distance zero). Local completions
are included in that count. This completion-display point is not theorem-specific.

The source-position closing-step audit found 756 eligible trace candidates across
97 theorems. Same-environment comparisons of different source bodies were possible
for 49 theorems. Fifty-four complete tactic traces had ambiguous before-states at
the last source position and were not arbitrarily resolved; three complete traces
were not tactic-level. All exclusions and the 128 non-complete/local traces are
recorded. No underlying record, proof or theorem object was deleted or changed.

The following are **last BEFORE-state ReProver distances, not Dartmouth final-step
distances**. They are a separate diagnostic and cannot resolve the primary
transition-embedding question:

| Same-environment comparison | Pairs | Exact zero | Median distance |
|---|---:|---:|---:|
| Same theorem, different source bodies | 6,117 | 1,373 | 0.4954 |
| Different theorems | 210,876 | 0 | 1.3407 |
| Same theorem, different bodies, identical closing tactic | 928 | 125 | 0.3816 |
| Different theorems, identical closing tactic | 2,545 | 0 | 1.1274 |

The first distribution ranges from 0 to 1.3698: equality is not universal.
The largest within-theorem contrast also occurs in `lean_workbook_490`, where
one source reaches a different final arithmetic obligation than another. Full
examples are retained in `examples.json`.

These summaries are pair-weighted descriptive statistics. Distinct source bodies
can differ in comments or implementation detail and do not establish independent
mathematical arguments. There is no chosen 'close' cutoff, significance claim,
new encoder, or new acquired proof. Enclosing `by` blocks and nested tactic nodes
make endpoint extraction nontrivial; the source-position rule is an explicit
operational candidate rule, not a proof of complete semantic-state capture.

## Dartmouth artifact availability and remaining test

Bounded searches checked the ACL paper, author/title web searches, GitHub repository
searches for Lean2Vec and proof trajectories, Hugging Face indexed results, and the
author's thesis landing page:
https://digitalcommons.dartmouth.edu/cs_senior_theses/65/

No compatible public weights/vocabulary/preprocessing release was located. This is
not a claim that none exists. The thesis download returned HTTP 403. A prize-page
arXiv link resolved to an unrelated physics paper and was not used. No author was
contacted and no substitute encoder was trained.

The remaining numerical test needs the pinned Dartmouth checkpoint and exact
preprocessing, or published per-step embeddings with proof/state provenance.
Then compare every eligible same-theorem distinct-proof endpoint with between-
theorem endpoints and controls for closing tactic, input identity and serialization.
Exact matches caused by identical inputs must be reported separately from closeness
between different inputs. Do not choose a tolerance merely to obtain convergence.

## Reproduction and validation

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python scripts/audit-proof-endpoints.py
.venv/bin/pytest -q tests/test_proof_endpoints.py
```

The protocol was saved before distance computation. The identical-transition
illustration was added after inspecting zero-distance pairs and is labeled as such.
Three focused extractor checks pass: prefer the final local tactic over an enclosing
wrapper, reject an earlier local completion if later work remains, and reject
conflicting observations at a terminal source position. Ruff passes for the script
and tests. Source/archive, script and protocol hashes are in `summary.json`.
Original data and explorer artifacts are unchanged. No GPU or new encoding was needed.
