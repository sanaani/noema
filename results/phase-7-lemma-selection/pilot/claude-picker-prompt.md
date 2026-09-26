# Phase 7 part 3 — CLAUDE arm picker prompt (fixed before the offer is drawn)

One fresh Claude subagent picks the CLAUDE arm
(`results/phase-7-lemma-selection/README.md`, part 3). It receives exactly
this text with `{OFFER}` filled in from `claude-offer.md`, written by
`scripts/select-phase7-pairs.py offer`: 400 pool pairs drawn by seed 20260930,
each with an id, the two lemma names and their 2026 statements (phase 5's
print). Nothing else about the pairs is given: no scores, no arm names, no
other arm's pairs. Its reply is saved unedited as `claude-picks.json` and read
by `scripts/select-phase7-pairs.py select`, which keeps the picks in the
order given.

---

You are choosing pairs of existing Mathlib lemmas (Mathlib revision
`09712d48`) for a theorem-writing experiment. For each pair you choose, a
separate writer will try to state and prove a **new** Lean theorem whose proof
genuinely uses both lemmas. The theorem counts only if it compiles, its proof
cites both lemmas, `exact?` and `aesop` each fail to prove it within 60
seconds, and its conclusion is not a conjunction or an iff. Every theorem that
counts is then rated blind: 0 if it restates a lemma or glues the two
together, 1 if it is a routine combination nobody would look for, 2 if a
Mathlib reviewer might plausibly accept it as a useful lemma in its own right.

Below are 400 pairs. Choose the **40 pairs most likely to yield a new,
non-trivial theorem**: pairs where the two lemmas can genuinely work
together and the combination says something that is not already an obvious
restatement of either. The pairs are from different areas of Mathlib and are
not cited together by any existing theorem.

Rules:

- Choose exactly 40 distinct pairs, by id, best first.
- No lemma may appear in more than two of your 40 pairs.
- Use only the text below. Do not run any tools and do not read any files.

(Each statement is shown as a goal: hypotheses above the line, the claim
after `⊢`.)

{OFFER}

End with one JSON array of exactly 40 entries, best first, and nothing after
it:
`[{"id": <pair id>, "reason": "<one sentence>"}, ...]`
