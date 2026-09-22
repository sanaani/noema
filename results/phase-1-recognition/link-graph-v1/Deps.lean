import Mathlib
import Lean

open Lean Elab Command

/-- All constants referenced by an expression into a balanced set.
    Explicit heap worklist (no C-stack growth); NameSet insert is
    tree-balanced. Core only, no Batteries. -/
partial def accDeps (e : Expr) : Lean.NameSet := go [e] {}
where go : List Expr → Lean.NameSet → Lean.NameSet
  | [], ds => ds
  | .const n _ :: rest, ds => go rest (ds.insert n)
  | .app f a :: rest, ds => go (f :: a :: rest) ds
  | .lam _ t b _ :: rest, ds => go (t :: b :: rest) ds
  | .forallE _ t b _ :: rest, ds => go (t :: b :: rest) ds
  | .letE _ t v b _ :: rest, ds => go (t :: v :: b :: rest) ds
  | .mdata _ b :: rest, ds => go (b :: rest) ds
  | .proj _ _ b :: rest, ds => go (b :: rest) ds
  | _ :: rest, ds => go rest ds

/-- Node count with early exit past a cutoff (heap-light pre-screen). -/
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

elab "dump_deps" : command => do
  let env ← getEnv
  let mut count := 0
  for (name, info) in env.constants.toList do
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
            let deps := ((Lean.RBMap.toList (accDeps v.value)).map (·.1) |>.map toString).toArray.qsort (· < ·)
            IO.println <| "EDGE " ++ (Json.mkObj [
              ("theorem", toJson name.toString),
              ("module", toJson modName.toString),
              ("deps", toJson deps)]).compress
          count := count + 1
          if count % 1000 == 0 then
            IO.println s!"PROGRESS {count}"
            (← IO.getStdout).flush
    | _ => pure ()
  IO.println s!"DONE {count}"

dump_deps
