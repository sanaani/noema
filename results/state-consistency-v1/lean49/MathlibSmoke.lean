import Noema.StateEncoding
import Mathlib.NumberTheory.SumTwoSquares

open Lean Meta Elab Command Noema
set_option maxHeartbeats 4000000
set_option maxRecDepth 2048

def renameBinders : Expr → Expr
  | .forallE _ a b i => .forallE `renamed (renameBinders a) (renameBinders b) i
  | .lam _ a b i => .lam `renamed (renameBinders a) (renameBinders b) i
  | .app f a => .app (renameBinders f) (renameBinders a)
  | .letE _ t v b n => .letE `renamed (renameBinders t) (renameBinders v) (renameBinders b) n
  | e => e

def captureIntroduced (ty : Expr) : MetaM Captured :=
  forallTelescope ty fun _ target => do
    capture [(← mkFreshExprMVar target).mvarId!]

elab "check_theorem " name:ident : command => liftTermElabM do
  let info ← getConstInfo name.getId
  unless info matches .thmInfo _ do throwError "not a theorem"
  let original ← captureIntroduced info.type
  let renamed ← captureIntroduced (renameBinders info.type)
  -- Wrap each goal target, retaining its introduced local context.
  let wrapped ← forallTelescope info.type fun _ target => do
    let target ← mkAppM ``id #[target]
    capture [(← mkFreshExprMVar target).mvarId!]
  unless ← equivalent original renamed do throwError "renaming lost equivalence"
  unless ← equivalent original wrapped do throwError "id wrapper lost equivalence"
  unless original.payload == renamed.payload do throwError "names leaked into payload"
  for (suffix, captured) in [("original", original), ("renamed", renamed), ("wrapped", wrapped)] do
    let label := name.getId.toString ++ "/" ++ suffix
    samples.modify (·.push (label, captured))
    IO.println <| "STATE " ++ (Json.mkObj [
      ("id", toJson label), ("shape", toJson captured.shape),
      ("payload", captured.payload)]).compress
  IO.println <| "MATHLIB " ++ (Json.mkObj [
    ("theorem", toJson name.getId.toString),
    ("shape", toJson original.shape),
    ("payload", original.payload),
    ("rename_equal", toJson true), ("wrapper_equal", toJson true),
    ("wrapper_same_payload", toJson (original.payload == wrapped.payload))]).compress

check_theorem Nat.Prime.sq_add_sq
check_theorem Nat.sq_add_sq_mul
check_theorem Nat.eq_sq_add_sq_iff
check_theorem ZMod.isSquare_neg_one_iff
check_theorem sq_add_sq_mul

run_meta do
  let rows ← samples.get
  for i in [:rows.size] do
    for j in [i:rows.size] do
      let equal ← equivalent rows[i]!.2 rows[j]!.2
      IO.println <| "PAIR " ++ (Json.mkObj [
        ("a", toJson rows[i]!.1), ("b", toJson rows[j]!.1),
        ("defeq_state", toJson equal)]).compress
