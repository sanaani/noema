import Lean
open Lean Meta Elab Tactic Command

-- This constructs diagnostic obligations; it does not assert an unproved theorem.
elab "audit_obligation " label:str target:term : command => do
  liftTermElabM do
    let type ← Term.elabTerm target (some (mkSort .zero))
    Term.synthesizeSyntheticMVarsNoPostponing
    let type ← instantiateMVars type
    let goal ← mkFreshExprMVar type .syntheticOpaque
    let text := (← ppGoal goal.mvarId!).pretty
    let args := type.getAppArgs
    let sidesEqual ← isDefEq args[1]! args[2]!
    logInfo <| "NOEMA_AUDIT " ++ (Json.mkObj [
      ("label", toJson label.getString), ("text", toJson text),
      ("target_expr", toJson (reprStr type)),
      ("equality_sides_definitionally_equal", toJson sidesEqual)]).compress

namespace Distance
 def x : Nat := 5
 audit_obligation "namespace_five" (x = 5)
end Distance
namespace Apples
 def x : Nat := 6
 audit_obligation "namespace_six" (x = 5)
end Apples

-- Snapshots inside a focused branch do not include its pending sibling.
elab "audit_snapshot " label:str : tactic => do
  let views ← (← getGoals).mapM fun g => return (← ppGoal g).pretty
  logInfo <| "NOEMA_AUDIT " ++ (Json.mkObj [
    ("label", toJson label.getString),
    ("text", toJson (String.intercalate "\n\n" views)),
    ("active_goals", toJson views.length)]).compress

example : True ∧ True := by
  constructor
  · audit_snapshot "sibling_true"
    trivial
  · trivial
example : True ∧ (2 = 2) := by
  constructor
  · audit_snapshot "sibling_equality"
    trivial
  · rfl

-- Kernel-checked positive and negative controls for the two namespace examples.
example : Distance.x = 5 := by rfl
example : Apples.x ≠ 5 := by decide
