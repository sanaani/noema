import Mathlib
import Lean

/-!
Dependency edges for Mathlib at `09712d48` (2026-09-21), Lean `v4.35.0-rc2`.

Phase 1's `Deps.lean` ported forward. The edge semantics are deliberately
unchanged, because phase 2's argument is a comparison against the 2024 graph
and a changed definition of "depends on" would make it meaningless:

* one record per `thmInfo` constant whose module starts with `Mathlib.` and
  whose name is not internal;
* `deps` is the sorted set of constant names appearing anywhere in the proof
  term, with no transitive closure and no filtering;
* a proof term past the node cutoff is recorded as `skipped: "oversize"`
  rather than dropped, so the two graphs account for the same population.

Three things differ from phase 1, none of which moves an edge:

* `Expr.getUsedConstants` replaces the hand-rolled `accDeps` worklist. Core's
  version does the same collection and is maintained.
* `SMap.foldM` replaces `env.constants.toList`, streaming rather than
  allocating the whole constant list up front.
* **Output goes to a file handle, not stdout.** Lean 4.35 captures a command
  elaborator's stdout and releases it only when the command completes, so
  `IO.println` plus an explicit flush leaves the redirect target empty for the
  whole run. Phase 1 ran on Lean 4.9, which streamed.

The node-count pre-screen is kept verbatim, so the same proofs are declared
oversize. Any further change should be checked by diffing edge lists against
the previous build over core Lean's own environment.

Run from a built Mathlib worktree. `NOEMA_DEPS_OUT` names the output file and
defaults to `edges-2026.jsonl`. Nothing useful appears on stdout:

    NOEMA_DEPS_OUT=/opt/work/edges.jsonl lake env lean Deps2026.lean
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
  -- A file handle, not stdout: see the header note on Lean 4.35's capture.
  let path := (← IO.getEnv "NOEMA_DEPS_OUT").getD "edges-2026.jsonl"
  let h ← IO.FS.Handle.mk path IO.FS.Mode.write
  let env ← getEnv
  h.putStrLn s!"STAGE environment loaded, {env.constants.map₁.size} imported constants"
  h.flush
  let count ← env.constants.foldM (init := 0) fun count name info => do
    match info with
    | .thmInfo v =>
      if let some idx := env.getModuleIdxFor? name then
        let modName := env.header.moduleNames[idx.toNat]!
        if modName.toString.startsWith "Mathlib." && !name.isInternal then
          h.putStrLn s!"THEOREM {name}"
          match countNodes v.value 3000000 with
          | none =>
            h.putStrLn <| "EDGE " ++ (Json.mkObj [
              ("theorem", toJson name.toString),
              ("module", toJson modName.toString),
              ("skipped", toJson "oversize")]).compress
          | some _ =>
            h.putStrLn <| "EDGE " ++ (Json.mkObj [
              ("theorem", toJson name.toString),
              ("module", toJson modName.toString),
              ("deps", toJson (depNames v.value))]).compress
          let count := count + 1
          if count % 100 == 0 then
            h.putStrLn s!"PROGRESS {count}"
            h.flush
          return count
        else return count
      else return count
    | _ => return count
  h.putStrLn s!"DONE {count}"
  h.flush

dump_deps
