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

The third is about visibility, and it is the one that mattered. **Output goes
to a file handle, not to stdout.** Lean 4.35 captures a command elaborator's
stdout and releases it only when the command completes, so `IO.println`
followed by an explicit `(<- IO.getStdout).flush` still leaves the redirect
target empty for the entire run. Two prints fifteen seconds apart were both
withheld until process exit; on the real sweep the worker had burned seventy
minutes of CPU having written exactly two bytes. Phase 1 ran on Lean 4.9,
which streamed, so nothing in phase 1 warned about this.

`SMap.foldM` also replaces `env.constants.toList`. That one is a cleanup, not
a fix: `SMap.toList` is `fold` with `(a, b) :: es`, so it is O(n) and measured
at 192ms over 808,723 constants.

For the record, since two runs were torn down over it: none of the obvious
suspects were slow. Measured on the 2026 library with oleans warm,
`import Mathlib` takes about four seconds, `getUsedConstants` about zero
milliseconds per theorem, and twenty theorems complete in 258ms.

Run it from a built Mathlib worktree. `NOEMA_DEPS_OUT` names the output file;
it defaults to `edges-2026.jsonl` in the working directory. Nothing useful
appears on stdout -- watch the output file instead:

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
  -- Not stdout. Lean 4.35 captures a command elaborator's stdout and only
  -- releases it when the command finishes, so `IO.println` plus an explicit
  -- flush still produces a zero-byte log for the whole run -- verified: two
  -- prints fifteen seconds apart both appeared only at process exit. Phase 1
  -- ran on Lean 4.9, which streamed, which is why this never came up before.
  -- A direct file handle bypasses the capture and writes immediately.
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
