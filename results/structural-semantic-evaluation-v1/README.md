# Structural semantic evaluation attempt

This attempt used complete `Noema.capture` structural payloads from the pinned
Lean 4.9/Mathlib theorem-center capture, not pretty-printed text. The frozen
semantic selection contains 76 centers; all fit Qwen's 32,768-token context
(maximum 29,535 tokens), but the longest CPU attention passes did not complete
after 36 minutes. No vectors or semantic scores were written.

The attempt was stopped cleanly. It must be rerun on GPU or with an explicitly
approved compact structural representation before making a semantic claim about
the real structural States. The earlier `semantic-encoder-evaluation-v1`
results are text-input results and are not a substitute for this run.
