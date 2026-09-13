# Recovery record and completion criteria

Inspection after the interruption found a clean working tree at `4dbd37a`, successful
Phase 0 v2 artifacts, and an empty `outputs/horn-corpus-v1/proofs` directory. There
was no corpus checkpoint or manifest, and no formal embedding report. Thus the
best supported interruption estimate is the first theorem of corpus collection.
The original research document still has SHA-256
`71879a5fb462f8decfd0ad329347b5e4932792a933636d4dc0ea09e52d599f5a`, matching the initial commit.
The existing 57 tests and lint/format checks passed on recovery.

The original verifier retained a fresh import environment for every declaration
in a 128-proof batch. This is a resource risk, not an established cause of the
machine interruption. Recovery bounds each verifier process to eight declarations
branching independently from one import-only environment. A measured eight-proof
batch took 3.28 seconds and peaked at about 1.52 GiB resident memory. No declaration
can reference another sampled proof. The full source retains `import Lean`; REPL
evidence line positions refer to its body after that import. The compiler's
standard library is the pinned library for this bounded fragment; Mathlib is not used.

Collection defaults now match the committed 64-proof budget, and state-sequence
deduplication uses binder/order-normalized formal content, as the corpus protocol
requires. Checkpoints are atomically replaced after each theorem; `--resume`
checks configuration and saved proof-source hashes and refuses completed outputs.
The empty interrupted directory is preserved; the recovered run uses a new path.

The remaining work is to collect and audit the preregistered corpus, freeze actual
split assignments before embedding, run the controlled encoder comparisons with
theorem-level uncertainty and nongeometric diversity sensitivities, assess added
information and representation fidelity, and document all kill criteria. The
existing feasibility gate remains unchanged. A failed gate closes this bounded
study with a negative or inconclusive result; it does not authorize interpreting
cross-theorem overlaps. Cross-domain discovery and proof navigation cannot be
claimed from this population.
