# Phase 6 pilot — interest rater prompt (fixed before any hit exists)

One separate Claude subagent rates every hit, in a shuffled order and without
the arm label, the pair's score or the writer's notes. It receives exactly
this text with `{HITS}` filled in: for each hit, an id, the two lemma names
with their 2026 statements, and the hit's `opens`, statement and proof.

---

You are reviewing short Lean 4 theorems written for Mathlib. Each one was
written to combine two existing Mathlib lemmas, shown with it. Rate every
theorem on this scale:

- **0: restates or glues.** It is one of the lemmas again, a conjunction of
  the two, or a statement where the two lemmas play no joint role.
- **1: routine combination.** The two lemmas genuinely work together, but the
  result is a direct corollary that nobody would look for.
- **2: worth merging.** Something a Mathlib reviewer might plausibly accept
  as a useful lemma in its own right.

Judge the mathematics, not the proof's length or style. Do not run any tools
and do not read any files.

{HITS}

End with one JSON array and nothing after it:
`[{"id": <id>, "rating": <0|1|2>, "reason": "<one sentence>"}, ...]`
