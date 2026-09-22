import Mathlib
import Lean

/-!
Dependency edges for Mathlib at `09712d48` (2026-09-21), Lean `v4.35.0-rc2`.

This is phase 1's `Deps.lean` ported forward. The edge semantics are deliberately
unchanged, because phase 2's whole argument is a comparison against the 2024
graph and a changed definition of "depends on" would make that comparison
meaningless:

* one record per `thmInfo` constant whose module starts with `Mathlib.` and
  whose name is not internal;
* `deps` is the sorted set of constant names appearing anywhere in the proof
  term, with no transitive closure and no filtering;
* a proof term past the node cutoff is recorded as `skipped: "oversize"`
  rather than dropped, so the two graphs account for the same population.

Three things changed in the port, none of which moves an edge. Phase 1 walked
the term itself with an explicit worklist (`accDeps`) because it was avoiding a
stack overflow on Mathlib's largest proofs; core's `Expr.getUsedConstants` does
the same collection and is maintained, so it is used here and the hand-rolled
walker is gone. `NameSet` iteration was replaced for the same reason. The
node-count pre-screen is kept verbatim, so the same proofs are declared
oversize.

The third is about visibility rather than semantics. Phase 1 iterated
`env.constants.toList`, which builds a cons-list of every constant -- 471,260
of them here -- before the loop can print anything. `SMap.foldM` streams the
same entries in the same order and threads the counter instead, so nothing is
allocated up front and the first theorem prints as soon as one is found.

Be careful about what that buys. `SMap.toList` is `fold` with `(a, b) :: es`,
so it is O(n) and costs about a second, not minutes -- it is *not* the reason
a run sits silent after launch. That silence is `import Mathlib`: Lean's
module loader is single-threaded and takes tens of minutes on the 2026
library, and no change in this file affects it. The `STAGE` line below is the
actual fix, because it fires the moment the environment is up and so
distinguishes "still importing" from "running but producing nothing".

Run it from a built Mathlib worktree:

    lake env lean --run ../../results/phase-2-dependency-labels/Deps2026.lean

or as a command file with `lake env lean Deps2026.lean`.
-/

open Lean Elab Command

/-- Node count with early exit past a cutoff, kept from phase 1 so that the
same proofs fall on the same side of the oversize boundary. -/
partial def countNodes (e : Expr) (limit : Nat) : Option Nat := go [e] 0
where go : List Expr → Nat → Option Nat
  | [], n => some n
  | e :: rest, n =>
    if n >= limit then none
    else match e with
      | .const _ _ => go rest (n + 1)
      | .app f a => go (f :: a :: rest) (n + 1)
      | .lam _ t b _ => go (t :: b :: rest) (n + 1)
      | .forallE _ t b _ => go (t :: b :: rest) (n + 1)
      | .letE _ t v b _ => go (t :: v :: b :: rest) (n + 1)
      | .mdata _ b => go (b :: rest) (n + 1)
      | .proj _ _ b => go (b :: rest) (n + 1)
      | _ => go rest (n + 1)

/-- Sorted, deduplicated constant names used by a proof term. -/
def depNames (e : Expr) : Array String :=
  let used := e.getUsedConstants.map Name.toString
  let sorted := used.qsort (· < ·)
  sorted.foldl (init := #[]) fun acc n =>
    if acc.back? == some n then acc else acc.push n

elab "dump_deps" : command => do
  let env ← getEnv
  IO.println s!"STAGE environment loaded, {env.constants.map₁.size} imported constants"
  (← IO.getStdout).flush
  let count ← env.constants.foldM (init := 0) fun count name info => do
    match info with
    | .thmInfo v =>
      if let some idx := env.getModuleIdxFor? name then
        let modName := env.header.moduleNames[idx.toNat]!
        if modName.toString.startsWith "Mathlib." && !name.isInternal then
          IO.println s!"THEOREM {name}"
          match countNodes v.value 3000000 with
          | none =>
            IO.println <| "EDGE " ++ (Json.mkObj [
              ("theorem", toJson name.toString),
              ("module", toJson modName.toString),
              ("skipped", toJson "oversize")]).compress
          | some _ =>
            IO.println <| "EDGE " ++ (Json.mkObj [
              ("theorem", toJson name.toString),
              ("module", toJson modName.toString),
              ("deps", toJson (depNames v.value))]).compress
          let count := count + 1
          if count % 100 == 0 then
            IO.println s!"PROGRESS {count}"
            (← IO.getStdout).flush
          return count
        else return count
      else return count
    | _ => return count
  IO.println s!"DONE {count}"

dump_deps
