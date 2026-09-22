# A checked State encoding contract

**Result:** the checked Qwen adapter passes the frozen inventory: 61 nonempty
classes, 106 occurrence rows, zero repeat drift, and no collisions among 1,830
distinct-class pairs. All 189 repository tests pass. This implements a usable
encoding path and separates exact State identity and Lean-certified equivalence
from numerical similarity. Use `Noema.capture` in
[`lean/Noema/StateEncoding.lean`](../../../lean/Noema/StateEncoding.lean) to capture
typed ordered obligations, then certify and freeze their equivalence registry.
[`RegisteredStateEncoder`](../../../src/noema/state_consistency.py) accepts only
registered structural inputs in the pinned environment. It returns separate
physical rows for repeated occurrences; unknown inputs never fall back to text.

## The guarantee

For an accepted encoder artifact and frozen registry:

1. Local and bound **display names never enter the structural expression**.
   Variable references use binding positions. The serializer uses no pretty
   printer. Lean kernel-checks general binder-name and metadata-erasure lemmas.
   Their axiom audit uses only `propext`, `Classical.choice`, and `Quot.sound`;
   no placeholders or added axioms are accepted.
2. Every recorded equivalence is checked in Lean, including types and local
   values. The complete pair relation must be reflexive and transitive; every
   class member has a direct check against its representative. Identical
   normalized syntax in different Lean classes is an error.
3. Every admitted equivalent input selects the **same stored vector**. This is
   guaranteed by the checked mapping, not by a model approximately learning
   equivalence. Consequently replacing any admitted State or center by an
   admitted equivalent preserves every distance and F_T exactly.
4. All distinct admitted classes are checked for token and vector collisions.
   Independent repeated inference must agree within 1e-6; vector files and
   class associations are pinned. An encoder failing these checks is rejected.
5. Unknown structural keys, unresolved variables, a different environment,
   changed artifacts, and terminal States submitted for geometric encoding fail
   explicitly. Terminal observations remain in the acquisition archive.

In symbols, the installed encoder is `E_R(s) = V_R[C_R[K(s)]]`: `K` is the
typed structural key, `C_R` the checked class lookup, and `V_R` the frozen vector
array. For every admitted Lean-certified pair, the exhaustive audit establishes
`C_R[K(s)] = C_R[K(t)]`; array lookup therefore gives `E_R(s) = E_R(t)` exactly.
Renaming local/bound display names while preserving binding structure leaves
`K` unchanged by construction. That property is not restricted to the handful
of variable spellings used in the tests. A new, structurally different key must
receive Lean evidence before it can enter a future registry version.

This is an **exhaustively checked finite-inventory contract**, not a proof that
one fixed neural network is injective on every possible Lean State. SHA-256 is
used for artifact identity and lookup with its usual cryptographic assumption;
the files are integrity checks, not signed remote attestations. Callers must
obtain payloads from the declared Lean acquisition environment.

## Independent extension beyond the original screen

The inventory contains 123 State occurrences, including all 60 checkpoints of
the original 16 proofs, plus new independently specified examples. Lean evaluates
all **7,626 pairs including the diagonal**. They form **62 equivalence classes**,
one of which is the archived empty-goal class. All 34 declared paired expectations
pass. Three deliberate invalid-input checks reject expression metavariables,
universe metavariables and loose bound variables.

| Extension | Required behavior |
|---|---|
| Local renaming, shadowed binders, dependent functions | Preserve equivalence |
| Beta, nested beta, zeta, iota, projection and eta reduction | Preserve equivalence |
| Reducible and ordinary aliases, including context types | Preserve equivalence |
| Explicit typeclass instances, polymorphic types, equivalent universe expressions | Preserve equivalence |
| Renamed local definitions with equivalent values | Preserve equivalence |
| Changed type, assumption, target, literal or local-definition value | Preserve the declared distinction |
| Unused assumptions, context/target boundary, goal count and order | Preserve the declared distinction |
| Shared locals across goals versus independent locals | Preserve the declared distinction |
| Pretty-printer changes | Have no effect on structural capture |

Three classes contain **different normalized payloads**: ordinary aliases,
aliases inside context types, and a wrapped string expression. This demonstrates
why a serializer alone is insufficient for general defeq consistency. Lean's
pair checks admit those payloads to the same class without requiring their
normalized syntax to match.

There are 106 nonempty occurrences and 61 nonempty classes. Class-level model
inference is expanded to all physical occurrences. This shares an encoder input;
it does not remove observations or alter their cumulative mass.

## What failed under the stronger contract

The existing 256-coordinate signed token-ngram baseline is **rejected**. Two
distinct class pairs have exactly the same vector: ordered versus reversed
pending goals, and two equality-symmetry proof checkpoints with different target
directions. The earlier small-suite success of a structural token baseline did
not establish this stronger property. The failed vectors and witnesses are
retained in `syntax/`.

LeanStateSearch is **rejected for this whole-input structural adapter**: the
largest input is 4,743 tokens, beyond its 512-token context. No input was truncated,
sampled, or silently replaced. This does not claim that no longer-input adapter
could ever use that model. Its token inventory and rejected class indices are
retained in `leansearch/`.

Qwen's full structural-input execution is **accepted** in `qwen/validation.json`.
Independent repeated inference has zero drift; the smallest Euclidean separation
between distinct unit class vectors is 0.00746151 (acceptance threshold 1e-6).
All 141 equivalent nonempty occurrence pairs return exactly identical vectors.
The largest input is 2,374
tokens, within its context. It receives the entire typed structural representation,
not a pretty-printed display. No prompt or model weights were trained or tuned.
The completed candidate uses CPU float32 with PyTorch SDPA attention. An earlier
eager-attention attempt was stopped for runtime cost after reaching 11 of 61
first-pass class encodings; its metadata and progress log are retained under
`execution-attempts/`. Numerical validation is restarted completely under SDPA;
no partial outputs from the interrupted attempt are mixed into the result.

The density check preserves all eight original curves across 44 occurrences.
Those original traces use identical normalized keys. A separate panel substitutes
genuinely different equivalent keys throughout the full nonempty inventory and
checks every occurrence as a center: the entire distance matrix is unchanged.
Both checks verify the registered lookup contract; they do not measure neural
generalization or establish that these distances are mathematically useful.

## Existing Mathlib toolchain

The separate `lean49/` evidence ports capture to the archived Lean 4.9 toolchain
using one array-search API substitution. Its complete 123-occurrence suite has
the same 7,626 pair outcomes as Lean 4.33. Additional capture checks use five real
Mathlib theorem statements from `Mathlib.NumberTheory.SumTwoSquares`: 15 original,
renamed and wrapped States, compared across all 120 pairs, form five classes.
These are introduced theorem-statement States, not complete proof trajectories.

An initial smoke-check assumption that every `id` wrapper would normalize to
identical syntax failed on all five theorem statements; that failed log is
retained. Lean nevertheless certifies equivalence, and the separate registry
correctly maps all variants to their respective classes. This reinforces the
need for the equivalence registry beyond syntactic normalization. No Qwen vectors
are transferred across Lean environments, and the old corpus is not yet recaptured.
Run `scripts/check-state-consistency-lean49.py` with the restored pinned runtime
and existing Mathlib checkout to reproduce these compatibility checks.

## Exact scope and remaining work

The encoded object is the **ordered pending-obligation State**: all local
declarations with types and definition values, the target of each goal, context
boundaries, and which local variables are shared across goals. It is not a full
Lean tactic-execution snapshot. Case labels, elaboration hints and binder names
are not included. Source occurrences and proof order remain external provenance.

Universe parameter names are preserved in this version. A renaming of a universe
parameter requires an explicit scope correspondence and is not silently treated
as equal. Goal/declaration reordering is also preserved, rather than asserted
irrelevant. The `universe_name` case documents this boundary; it is not counted
as a mathematical distinction. General proof-search operational equivalence is
outside the contract.

Normalization uses recursive reducible WHNF and eta contraction, with a Lean
defeq check against the original field. The registry then compares shape-compatible
closed fields using Lean's definitional-equality checker with full transparency.
Failure to equate two expressions is not a proof that no broader mathematical
equivalence exists. Resource failures stop acquisition; no approximate class
assignment is allowed. The frozen inventory comparison is quadratic and intended
as a correctness reference, not a claim of scalable all-mathlib acquisition.

The old 102-theorem display archive lacks the structured local contexts and
metavariable/environment evidence needed to certify all its States. It cannot
be migrated merely by renaming characters or inventing missing structure. New
acquisition must use the typed capture path; any registry extension is a new
version with explicit vector correspondence. These changes preserve the earlier
archives and do not relabel their distances as validated.

The achieved contract addresses **consistency of accepted encodings**. It does
not establish that the angle or distance between distinct classes reflects a
useful mathematical relationship. A one-hot class identifier could satisfy
identity consistency while giving no useful geometry. That remains a separate
evaluation question, not an unresolved variable-name problem.

## Use and reproduce

Compile the reusable capture module with the pinned Lean toolchain:

```bash
.tools/lean-4.33.1-linux/bin/lean -o lean/Noema/StateEncoding.olean \
  lean/Noema/StateEncoding.lean
LEAN_PATH=lean .tools/lean-4.33.1-linux/bin/lean results/phase-1-recognition/state-consistency-v1/Suite.lean
```

The suite includes all acquisition definitions and the complete pair comparison.
The environment manifest pins the Lean version/binary, capture policy, acquisition
source and the public core `.olean` files. The Python acquisition runner checks its logs,
declared expectations and the complete equivalence relation before freezing a
registry. `acquire` refuses to overwrite that registry.

For an accepted artifact, use the API with the environment identity from the
registry receipt:

```python
from pathlib import Path
from noema.state_consistency import RegisteredStateEncoder

encoder = RegisteredStateEncoder(Path("results/phase-1-recognition/state-consistency-v1"), "qwen")
# records are nonempty structural State records acquired in this environment.
vectors = encoder.encode(
    [record["payload"] for record in records],
    environment_id=acquisition_environment_id,
)
```

Do not replace a mismatched acquisition environment with the registry's ID to
bypass the check. The CLI `noema encode-states` (also available through
`scripts/encode-registered-states.py`) accepts the same
inputs and writes vectors plus an occurrence-to-row manifest. It validates the
whole batch before writing, preserves duplicates, and refuses output overwrite.

Recompute every class and vector check without downloading or running a model:

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/audit-state-consistency.py verify
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/check-consistent-density.py
```

`Suite.lean`, `expected.json`, `lean-output.log`, `records.json` and `pairs.json`
are the formal evidence. `registry.json` includes all class memberships and
representatives. Model directories retain token IDs, class vectors, independent
repeats, and accepted occurrence vectors or rejection witnesses. `density-checks.json`
checks the lookup contract throughout the original proof traces, not model
generalization to unseen examples. `validation.json` and `SHA256SUMS` record final
engineering validation and artifact integrity.

## Large artifact

`lean49/typed-centers.json` is 103 MB and stays out of git; the committed
`lean49/typed-centers.json.gz` is byte-identical (`gzip -dk` to unpack). The
checksum list covers the `.gz`, since that is the file a clone has. The
uncompressed file's digest, for anyone who unpacks it, is
`ce6437e3ef638302a6eafd156cd52d1a8e9a9163f8f82a17cfad9c6399c564c9`.
