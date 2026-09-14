# Enforced admission and data repair

The admission mistake was treating a successful proof check as sufficient evidence
that a theorem was a useful, non-vacuous instance. The six excluded statements
have checked proofs, but their assumptions are impossible. Leaving them in the
active set with warnings did not fix that mistake.

The active dataset now contains **102 theorem groups, 813 source proof records and
16,592 separate state-vector rows**. Every recorded state of each admitted theorem
remains, including repeated inputs and coordinates. The full 26,820-row archive
remains available for recovery; it is no longer the active analysis set.

## Corrections applied

| Problem | Applied correction |
|---|---|
| Contradictory assumptions remained active | Six groups excluded: 44 proof records and 558 states. Lean independently proves False from their exact source assumptions. |
| Unverified proof records remained in the inclusion count | Exact-target verified proof/axiom evidence is required for every inventoried proof record. Otherwise hold the whole theorem group. |
| Unresolved theorem identity was only annotated | Groups with unresolved Mathlib identity are held. A whole-statement check also holds three Workbook groups with versioned declaration differences. |
| Incomplete proof acquisition could produce an active partial object | An operational trace is required for every inventoried proof record. Missing traces hold the whole group. |
| Warnings did not change the actual analysis | Active vector files, membership, projection, pair results and explorer were rebuilt. Verification, analysis and rendering enforce the admission ledger. |
| Proof copies inflated diversity claims | Every copy remains, but counts explicitly say source proof records; independent mathematical arguments are not counted. |

The partition is **102 admitted, six excluded, 148 held**. Held groups account for
9,670 recorded states. Held does not mean false or unprovable; reinstatement requires
evidence resolving the applicable gaps. Admission does not target a desired sample
size or select on geometric outcomes. There is no replacement sampling or proof/state cap.

Three newly held Workbook groups are `lean_workbook_9279`, `lean_workbook_3429`
and `lean_workbook_38894`. Their big-operator declarations use different syntax
across versions. This does not assert mathematical inequivalence: verified
cross-version elaborated-type comparison is needed to discharge the hold.

## Contradictions checked in Lean

The [fixture](../results/theorem-admission-v1/Contradictions.lean) and
[verification receipt](../results/theorem-admission-v1/contradiction-verification.json)
establish these exclusions:

| Workbook ID | Impossible assumptions |
|---|---|
| `lean_workbook_plus_5257` | Three natural numbers are each at least 20, but their sum is at most 18. |
| `lean_workbook_plus_63727` | The lower bound on `k` exceeds its upper bound by 1/2. |
| `lean_workbook_plus_44565` | Positive `a,b,c` have product 1 and sum of squares 1. |
| `lean_workbook_19088` | The same incompatible product and sum-of-squares assumptions. |
| `lean_workbook_plus_68017` | Positive `a,b,c` have product 1 and their squared pairwise products sum to 1. |
| `lean_workbook_9657` | `a³ = a+1` and `a⁶ ≤ 4a` force `a=1`, contradicting the first equation. |

Every source record in each excluded group has the same outer binders as its
diagnostic proof, apart from whitespace. Every body hash is pinned. Changed sources
cannot silently inherit old exclusions. No diagnostic uses `sorryAx` or an added axiom.

A bounded contradiction screen ran on the original outer binders of **all 128
Workbook groups**. Six contradictions were proved; **122 checks were unresolved**.
It does not inspect every implication embedded in a conclusion, does not cover
the Mathlib groups, and does not prove consistency when automation fails. Compiler
diagnostics and exact generated sources are retained for every case.

The independent diagnostics use Lean4.9.0 and Mathlib
`f0957a7575317490107578ebaee9efaf8e62a4ab`, with the exact source binders and basic
Nat/Real arithmetic. Original proofs were checked separately in their archived
source environments. No new encoder or GPU run was needed.

## Still open, not declared repaired

- Full internal state/context capture requires improved extraction and replay in
  the original environments. Operational trace completion is not exhaustive
  internal capture; separate rows do not recover missing context.
- All-known-proof coverage, unresolved cross-version identities and broader scale
  require additional acquisition and identity evidence. Quarantine repairs active
  admission, not the missing acquisition itself.
- Script counts do not establish independent proof diversity.
- Encoder faithfulness and the best State-object definition remain research
  questions. Proof eligibility cannot validate those hypotheses.
- All admitted objects still contain the encoded empty active-goal display.
  Their common contact and convexity-imposed connectivity are not discoveries of
  mathematical relatedness. No inconvenient state was removed to alter this result.

These are open tasks, not problems marked fixed by documentation. The present
active set supports exploratory geometry of recorded goal displays; it does not
yet fulfill the full scientific specification.

## Results and recovery

Use the [active archive](../results/state-objects-admitted-v1/README.md) and
[active explorer](../results/state-objects-admitted-v1/explore.html).
`results/state-objects-admitted-v1/admission.json` lists every decision and pins
its evidence. Original archives and failed attempts remain unchanged.

The 5,151 active pairs were checked against every retained physical row: 5,150
have only the shared-point contact, and one has a shared segment. These are
numerical certificates for encoded displays. The projection was refitted using
all 16,592 active rows. All active coordinates match their saved encoder outputs
exactly. CI checks exclusion evidence, recalculates admission and verifies row
and pair coverage.
