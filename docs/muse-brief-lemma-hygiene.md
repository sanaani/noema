# Brief: anonymous-lemma detector for Mathlib

**For:** Muse
**From:** noema (link-graph line of work)
**Repo:** new, standalone — see "Why a new repo" below.

## Goal

Find statements that Mathlib proves **inline and anonymously**, inside two or more
proofs in distant files, and that deserve to be named lemmas. Output a reviewable
list; land the good ones as PRs.

This is a library-maintenance tool, not a discovery engine. Every hit is
actionable by construction: the proof already exists in the library.

## Why this, and the worked example

The noema bridge scan (`scripts/scan-bridge-triples.py`) pairs theorems that share
rare citations with a third. Hand-inspecting 8 of its 2,946 candidates produced
exactly one thing worth keeping, and it was not a hidden mathematical connection —
it was an unnamed lemma:

```lean
theorem isSemisimpleRing_quotient_span_singleton_of_squarefree
    {K : Type*} [Field K] {p : K[X]} (hp : Squarefree p) :
    IsSemisimpleRing (K[X] ⧸ Ideal.span {p})
```

Mathlib proves this in four lines inside
`Module.End.isSemisimple_of_squarefree_aeval_eq_zero`
(`Mathlib/LinearAlgebra/Semisimple.lean:119`) as an anonymous `have`, and names it
nowhere. Not in the pinned checkout (`f0957a75`), and not visible in current
Mathlib's `RingTheory.SimpleModule` docs.

**The finding came from reading the proof, not from the graph.** That is the
observation this brief turns into a tool.

Status when this brief was written: the extraction compiles as far as the local
Mathlib build has progressed; the full check was still running. Confirm before
citing it anywhere.

## Scope

**In scope**
- Extract `have`/`suffices` statements (and their proof terms) from every Mathlib proof.
- Normalise statements up to α-renaming and instance/implicit-argument noise, so the
  same mathematical claim in two files compares equal.
- Report claims that appear in ≥2 proofs in modules with no direct import relationship.
- Rank by how substantial the claim is (proof-term size of the inline proof, number
  of distinct files, distance between the files in the module graph).

**Out of scope**
- Embeddings, GPUs, learned rankers. This is set comparison over syntax trees.
- Proof-state capture.
- Any claim about discovering new mathematics.

## Method notes

- Start from `Deps.lean` (in `results/phase-1-recognition/link-graph-v1/`, 2.6KB, core-only Lean, no
  Batteries). It already walks every non-internal `Mathlib.*` theorem's proof term.
  Extend it to record inline `have` statements rather than only referenced constants.
- Giant proof terms (>3M nodes) must stay skipped, as in the current sweep — 1,056
  of 206,889 theorems. Record them as skipped, do not silently drop.
- The pinned Mathlib is `f0957a75`, Lean 4.9.0. Pin whatever you use and say so in
  the README; findings are worthless without a commit hash.
- Expect typeclass plumbing to dominate raw output. The filter that worked in the
  bridge scan: require the statement's own proof to be at least median size
  (20 constants) — it removed `Prod.fst_zero`-class trivia without touching real
  content.

## Acceptance criteria

1. Runs in one command against a built Mathlib; runtime stated in the README.
2. Produces ≥20 candidates that survive hand inspection as genuinely duplicated
   mathematical claims.
3. A measured false-positive rate from a hand-checked sample of ≥50. Report it
   honestly; an accurate 60% is more useful than an unverified 95%.
4. Output names file, line, the statement, and each site that re-proves it.

## Sharing sequence (do not skip step 0)

0. **Search Zulip first.** Duplicate-lemma detection has been attempted in that
   community before. Build on prior work rather than announcing a rediscovery.
1. Post 15–20 candidates to the `#mathlib4` stream on `leanprover.zulipchat.com`
   and ask whether they are worth naming. Learn which categories are noise.
2. Land 2–3 PRs from the best findings. Credibility comes from merged PRs.
3. Only then propose the tool, citing `shake` (unnecessary-import detection) as the
   in-repo precedent. Anything needing full-environment traversal is a nightly job,
   never per-PR CI — their CI is a scarce resource.
4. Apache 2.0, matching Mathlib.

Current contribution process: https://leanprover-community.github.io/contribute/

## Why a new repo

Yes — build it standalone.

- **Different audience.** noema is a research line with negative results and
  exploratory scaffolding. This is a tool for Mathlib maintainers, who will read the
  repo before trusting the output.
- **No dependency on noema.** The only asset it needs is `Deps.lean`, which is 2.6KB
  and self-contained. Copy it; do not import noema.
- **Cleaner provenance for PRs.** A maintainer clicking through from a PR should land
  on a focused tool, not a 5GB research corpus.
- **noema keeps its narrative.** The bridge scan remains what it is — a search whose
  honest score so far is one hygiene finding out of eight candidates inspected.

Cross-link the two repos in their READMEs so the lineage is visible.
