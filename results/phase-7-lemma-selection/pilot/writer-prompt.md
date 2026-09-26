# Phase 7 part 3 — writer prompt (fixed before any pair is written)

Phase 6's writer prompt with the hit rule extended as
`results/phase-7-lemma-selection/README.md`, part 3, fixes it: rules 4 and 5
are new, the checker is `scripts/phase7-check.py`, and nothing else changes.
Every writer subagent receives exactly this text, with `{PAIR}`, `{A}`,
`{A_STATEMENT}`, `{B}`, `{B_STATEMENT}`, `{RUN}` and `{WORKDIR}` filled in
from `pairs.jsonl` and phase 5's 2026 statement print. Nothing else about the
pair is given; in particular not its arm.

---

You are writing new Lean 4 theorems for Mathlib (revision `09712d48`, Lean
`v4.35.0-rc2`). You are given two existing Mathlib lemmas. Your job is to
state and prove up to three theorems that **genuinely need both** of them.

**Lemma A:** `{A}`

```
{A_STATEMENT}
```

**Lemma B:** `{B}`

```
{B_STATEMENT}
```

(Each statement is shown as a goal: hypotheses above the line, the claim after
`⊢`.)

## What counts

A candidate succeeds only if all five hold:

1. It compiles against Mathlib with no `sorry` and no axioms beyond `propext`,
   `Classical.choice` and `Quot.sound` (`choice`, as Lean prints it under
   `open Classical`, is `Classical.choice` and is accepted).
2. Its proof term refers to **both** `{A}` and `{B}` by name, directly (a tactic
   such as `simp [{A}]` or `rw [{B}]` or an explicit term application counts if
   the lemma ends up in the proof term; a lemma that `simp` does not end up
   using does not count).
3. It is not already in Mathlib: `exact?` must fail to close the statement
   within 60 seconds.
4. Its conclusion is not a conjunction or an iff. After every hypothesis and
   variable is introduced, the claim must not have `∧` (`And`) or `↔` (`Iff`)
   at its head. This is checked on the elaborated statement, so hiding the
   `∧` behind a reducible definition does not help.
5. It is not routine automation: `aesop` must fail to close the statement
   within 60 seconds.

Aim for a statement a mathematician would find a meaningful combination of
the two ideas, not a conjunction or a rewrite chain glued together. Aim first
for a theorem that succeeds, then for one that is interesting.

## How to submit a candidate

Write a JSON file in `{WORKDIR}` with these fields:

```json
{"opens": ["open Real"],
 "statement": "theorem noema_pilot_candidate (x : ℝ) (hx : 0 < x) : ...",
 "proof": "by\n  ..."}
```

- The theorem must be named `noema_pilot_candidate`.
- `opens` holds only plain `open ...` lines, and may be empty.
- Forbidden anywhere: `sorry`, `admit`, `axiom`, `native_decide`, `import`,
  `unsafe`, `implemented_by`, `extern`.

Check it by running:

```
cd ~/Documents/noema && .venv/bin/python scripts/phase7-check.py --run {RUN} --pair {PAIR} --attempt <n> <file>
```

Number your attempts 1, 2, 3, … across the whole pair. The command takes
about a minute or two and prints whether the candidate compiled, which
endpoints its proof cites, the head of its conclusion and whether that is a
conjunction or iff, whether `exact?` or `aesop` closed it, whether it is a
hit, and Lean's output.

## Budget

- At most **three candidates**. For each candidate: one first attempt plus at
  most **three repairs** using Lean's messages. That is at most 12 checks in
  total. Stop a candidate once it is a hit, then move to the next one if you
  want another.
- The checker is your only way to run Lean. Do not use the web, and do not
  read anything in the repository except running the command above. In
  particular, do not open `results/`, `outputs/` or any README.

## Report

End with one JSON object and nothing after it:

```json
{"pair": {PAIR}, "checks": <number of checks run>, "hits": [<attempt numbers that were hits>],
 "notes": "<one sentence>"}
```
