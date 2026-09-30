# Phase 22 follow-up — are the model's hits obvious or surprising?

**Written and committed before the list is computed.** Results go in a section
appended below; nothing above it changes.

## Why

Phase 22 showed that similarity picks which works on a route will jump. But an
"important jump" only needs 5 follow-on papers, so a slow, predictable spread
of a well-known tool counts the same as a surprising one. This check asks
whether the model's hits are mostly the predictable kind.

## The list

Phase 22's primary out-of-fold BASE+SIM scores at the 2005 cutoff, recomputed
with Phase 22's seed and code path (same folds, same scores). The **top 100**
far pairs by that score; the important jumps among them (Phase 22 reported
31).

## The rule, fixed now

Each important jump (work W, target area A) gets one label, from data up to
2005 only:

1. **Knocking**: at least one paper that lists A as a *secondary* arXiv
   category cited W. The connection already existed under another label.
2. **Next door**: not knocking, and at least one paper whose primary area is
   one of A's **3 nearest areas** cited W. Nearest = highest co-citation
   share F[A | B] (Phase 18's table, up to 2005), B ≠ A.
3. **Surprising**: neither.

The same labels are computed for **all 229** important jumps, to compare the
model's hits against real jumps as a whole.

Also reported: each hit's work (title and OpenAlex type, looked up after the
run), home area, target area, citers, breadth, span, similarity and follow-on
papers 2006–2015.

## What would count as what

- If hits are mostly **knocking or next door** and at a higher share than
  among all 229 jumps: the model mainly finds predictable spread.
- If the hits' share of **surprising** is similar to or higher than among all
  229: the model is not biased toward the obvious ones.

Prediction: mostly knocking or next door, at a higher share than overall.

## Run

One AWS m6i.4xlarge (the Phase 12 launcher, `USERDATA=phase22hits`), smoke
first, under $0.50, teardown verified.

---

## Results

*Appended after the run. Nothing above this line changed.* Run
`noema-p12-20260930-193955`, one m6i.4xlarge, 4 minutes, torn down and
verified. Numbers from `results/hits.json`; titles and record types from
OpenAlex in `results/names.json`. The top 100 holds 31 important jumps, as in
Phase 22, so the list is the one Phase 22 scored.

### Labels

| | knocking | next door | surprising | total |
|---|---:|---:|---:|---:|
| important jumps in the model's top 100 | 17 | 12 | **2** | 31 |
| all important jumps | 59 | 75 | **95** | 229 |

Surprising jumps are **41%** of all real jumps but **6%** of the model's top
hits. Median rank among the 146,938 far pairs: knocking 857, next door 873,
**surprising 3,244**.

### What the hits are

Nearly all are standard references reaching optimization and control: Feller's
*Introduction to Probability Theory*, Gilbarg–Trudinger, Federer's *Geometric
Measure Theory*, Rockafellar's *Convex Analysis*, Cover–Thomas, Shannon,
Billingsley, Evans–Gariepy, Stanley's *Enumerative Combinatorics*, the
Abramowitz–Stegun handbook. 13 of 31 are books, 4 book chapters. The two
surprising hits are both on **backward stochastic differential equations**
(Pardoux–Peng 1990; El Karoui–Peng–Quenez 1997) reaching control, and BSDEs
also lead the best-ranked surprising jumps overall.

### Verdict

The prediction held: **the model's hits are mostly predictable spread** (29
of 31 knocking or next door), at a far higher share than among real jumps
(94% against 59%). Similarity forecasts the kind of jump the project cares
least about.

### Next

Make "surprising" part of the target: count surprising jumps at the far and
wide thresholds, then (if enough) test whether similarity ranks surprising
jumps among pairs that are neither knocking nor next door.
