# Semantic encoder evaluation

This is a fixed-control, descriptive follow-up to the historical-connection
pilot. It uses the 106 round-trip-checked, type-aware Mathlib theorem-center
inputs from `historical-connections-v1`, with the four prespecified connection
triples and their frozen background and lexical controls. No control or model
was selected after inspecting distances.

Five transformer encoders were run on all 106 typed centers: LeanStateSearch,
E5-small-v2, BGE-small-en-v1.5, Qwen3-Embedding-0.6B, and Qwen with the fixed
instruction. The archived ReProver analysis is retained separately as the
historical baseline.

Here “typed” means the round-trip-checked type-aware textual display. These
results do not use the later complete `Noema.capture` structural JSON payloads;
that separate structural run is recorded in `structural-semantic-evaluation-v1`.

Across the ten directed target-vs-background comparisons, the mean fraction of
background controls farther away was 0.988--0.992 for the five new encoders.
Against the four lexical controls, the mean farther fraction was 0.125--0.188;
the target pair was therefore never unusually close in this small control set.
The bridge theorem was likewise not unusually close to its endpoints relative
to the background controls. These results provide no evidence that these
embeddings measure the intended mathematical connections.

This is not a universal negative claim: it is a small, prespecified benchmark
of theorem-center representations. The inputs are typed theorem obligations,
not complete proof trajectories or State objects with all tactic history. The
structural capture and equivalence contract is archived separately in
`state-consistency-v1`; its registry must not be confused with these semantic
scores.

`analysis.json` contains every case and direction. The vector arrays and model
manifests make the run reproducible without AWS. The prior AWS GPU calculation
was a complete, independently verified ReProver hardware run for the old
display-based inventory; it is not necessary to rerun it for this benchmark.
