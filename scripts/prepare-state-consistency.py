"""Generate a broader independent State inventory and exhaustive Lean pair audit."""

from pathlib import Path

from noema.paths import result_path

ROOT = Path(__file__).resolve().parents[1]
OUT = result_path("state-consistency-v1")

HEADER = r"""
import Noema.StateEncoding
open Lean Meta Elab Command Tactic Noema
set_option Elab.async false
set_option maxHeartbeats 4000000
set_option maxRecDepth 2048
set_option linter.unusedVariables false

def retain (label : String) (goals : List MVarId) : MetaM Unit := do
  let state ← capture goals
  samples.modify (·.push (label, state))
  IO.println <| "STATE " ++ (Json.mkObj [
    ("id", toJson label), ("shape", toJson state.shape), ("payload", state.payload)]).compress

elab "state " label:str " : " ty:term : command => liftTermElabM do
  let ty ← Term.elabType ty
  Term.synthesizeSyntheticMVarsNoPostponing
  forallTelescope ty fun _ body => do
    unless ← isProp body do throwError "State target is not a proposition"
    let goal ← mkFreshExprMVar body
    retain label.getString [goal.mvarId!]

elab "closed_state " label:str " : " ty:term : command => liftTermElabM do
  let ty ← Term.elabType ty
  Term.synthesizeSyntheticMVarsNoPostponing
  unless ← isProp ty do throwError "State target is not a proposition"
  retain label.getString [(← mkFreshExprMVar ty).mvarId!]

elab "observe " label:str : tactic => do retain label.getString (← getGoals)

elab "audit_fixture " name:ident : command => do
  let info ← getConstInfo name.getId
  unless info matches .thmInfo _ do throwError "not a theorem"
  let axioms ← collectAxioms name.getId
  for a in axioms do
    unless a == ``propext || a == ``Classical.choice || a == ``Quot.sound do
      throwError "unexpected proof axiom"
  IO.println <| "PROOF " ++ (Json.mkObj [
    ("name", toJson name.getId.toString), ("axioms", toJson (axioms.map Name.toString))]).compress

-- Ordinary definitions exercise the equivalence registry beyond reducible NF.
def ordinaryAlias (p : Prop) : Prop := p
abbrev reducibleAlias (p : Prop) : Prop := p
universe u v

-- Rejections must be genuine failures rather than silently encoded metavariables.
run_meta do
  let bad ← mkFreshExprMVar (mkSort .zero)
  let goal ← mkFreshExprMVar bad
  let rejected ← try
    let _ ← capture [goal.mvarId!]
    pure false
  catch _ => pure true
  unless rejected do throwError "expression metavariable accepted"
  IO.println "REJECTED expr_mvar"
  let lvl ← mkFreshLevelMVar
  let ty := mkForall `A BinderInfo.default (mkSort lvl) (mkConst ``True)
  let goal ← mkFreshExprMVar ty
  let rejected ← try
    let _ ← capture [goal.mvarId!]
    pure false
  catch _ => pure true
  unless rejected do throwError "universe metavariable accepted"
  IO.println "REJECTED universe_mvar"
  match exprJson (.bvar 0) with
  | .error _ => pure ()
  | .ok _ => throwError "loose variable accepted"
  IO.println "REJECTED loose_bvar"
"""

# Each group has an independent original and transformation; expected equivalence
# labels are checked, never used as inputs to the serializer or pair comparator.
GROUPS = {
    "rename": ["∀ (x : Nat), x = x", "∀ (y : Nat), y = y"],
    "dependent": ["∀ (A : Type u) (x : A), x = x", "∀ (B : Type u) (y : B), y = y"],
    "beta": ["∀ (n : Nat), n = n", "∀ (n : Nat), (fun x : Nat => x) n = n"],
    "nested_beta": [
        "∀ (n : Nat), n = n",
        "∀ (n : Nat), (fun f : Nat → Nat => f n) (fun x => x) = n",
    ],
    "zeta": ["∀ (n : Nat), n = n", "∀ (n : Nat), (let k := n; k) = n"],
    "projection": ["∀ (n m : Nat), n = n", "∀ (n m : Nat), (n, m).1 = n"],
    "iota": ["∀ (n : Nat), n = n", "∀ (n : Nat), (match true with | true => n | false => 0) = n"],
    "eta": ["∀ (f : Nat → Nat), f = f", "∀ (f : Nat → Nat), (fun x => f x) = f"],
    "reducible_alias": ["∀ (p : Prop), p ∨ p", "∀ (p : Prop), reducibleAlias (p ∨ p)"],
    "ordinary_alias": ["∀ (p : Prop), p ∨ p", "∀ (p : Prop), ordinaryAlias (p ∨ p)"],
    "context_alias": [
        "∀ (p : Prop) (h : p ∨ p), p ∨ p",
        "∀ (p : Prop) (h : ordinaryAlias (p ∨ p)), p ∨ p",
    ],
    "instance": [
        "∀ (A : Type u) [i : Inhabited A], (default : A) = default",
        "∀ (B : Type u) [j : Inhabited B], (@Inhabited.default B j) = default",
    ],
    "shadow": [
        "∀ (f : Nat → Nat), (fun x => (fun x => x) x) = f",
        "∀ (g : Nat → Nat), (fun a => (fun b => b) a) = g",
    ],
    "level_arithmetic": ["∀ (A : Sort (max u u)) (a : A), a = a", "∀ (B : Sort u) (b : B), b = b"],
    "string": ['"x ≠ y" = "x ≠ y"', 'id "x ≠ y" = "x ≠ y"'],
    "dependent_fn": [
        "∀ (A : Type u) (B : A → Type v) (f : (x : A) → B x), f = f",
        "∀ (X : Type u) (Y : X → Type v) (g : (z : X) → Y z), (fun z => g z) = g",
    ],
}

DISTINCTIONS = {
    "goal": ["∀ (n : Nat), n = 0", "∀ (n : Nat), n = 1"],
    "type": ["∀ (n : Nat), n = n", "∀ (n : Int), n = n"],
    "unused": ["∀ (n : Nat), n = n", "∀ (n m : Nat), n = n"],
    "dependent_reference": ["∀ (n m : Nat), n = 0", "∀ (n m : Nat), m = 0"],
    "literal": ['"x" = "x"', '"y" = "x"'],
    "operator": ["∀ (xs : List Nat), xs = []", "∀ (xs : List Nat), xs ≠ []"],
    "assumption": ["∀ (p q : Prop) (h : p), p ∨ q", "∀ (p q : Prop) (h : q), p ∨ q"],
    "universe": ["∀ (A : Type) (a : A), a = a", "∀ (A : Type 1) (a : A), a = a"],
}

FOOTER = r"""
-- Context values and goal order/count must remain represented.
example (n : Nat) : True := by
  let x := n
  observe "let/base"
  trivial
example (y : Nat) : True := by
  let z := (fun k : Nat => k) y
  observe "let/renamed"
  trivial
example (n : Nat) : True := by
  let x := n + 1
  observe "let/different"
  trivial
example (A B : Prop) (hA : A) (hB : B) : A ∧ B := by
  constructor
  observe "goals/ordered"
  rotate_left
  observe "goals/reversed"
  exact hB
  observe "goals/single"
  exact hA
  observe "goals/empty"

-- Display settings never enter the structural capture.
set_option pp.all true in
state "printer/all" : ∀ (n : Nat), n = n
set_option format.width 10 in
state "printer/narrow" : ∀ (n : Nat), n = n
closed_state "boundary/closed" : ∀ (n : Nat), n = n
state "boundary/introduced" : ∀ (n : Nat), n = n

-- Universe parameter renaming is outside this version's named-universe scope.
state "universe_name/u" : ∀ (A : Type u) (a : A), a = a
state "universe_name/v" : ∀ (A : Type v) (a : A), a = a

-- A complete ordered goal list must also retain shared local-variable identity.
run_meta do
  withLocalDeclD `n (mkConst ``Nat) fun n => do
    let target ← mkEq n n
    let a ← mkFreshExprMVar target
    let b ← mkFreshExprMVar target
    retain "sharing/shared" [a.mvarId!, b.mvarId!]
  let a ← withLocalDeclD `n (mkConst ``Nat) fun n => do
    mkFreshExprMVar (← mkEq n n)
  let b ← withLocalDeclD `m (mkConst ``Nat) fun m => do
    mkFreshExprMVar (← mkEq m m)
  retain "sharing/separate" [a.mvarId!, b.mvarId!]

elab "compare_inventory" : command => liftTermElabM do
  let rows ← samples.get
  for i in [:rows.size] do
    for j in [i:rows.size] do
      let equal ← equivalent rows[i]!.2 rows[j]!.2
      IO.println <| "PAIR " ++ (Json.mkObj [
        ("a", toJson rows[i]!.1), ("b", toJson rows[j]!.1),
        ("defeq_state", toJson equal)]).compress

compare_inventory
"""


def main():
    import json

    source = HEADER
    expected = []
    for kind, groups in [("equivalent", GROUPS), ("distinct", DISTINCTIONS)]:
        for name, terms in groups.items():
            ids = [f"{kind}/{name}/{i}" for i in range(len(terms))]
            for identifier, term in zip(ids, terms, strict=True):
                source += f'\nstate "{identifier}" : {term}\n'
            expected.append({"a": ids[0], "b": ids[1], "equal": kind == "equivalent"})
    original = (result_path("encoder-invariance-v1/Fixtures.lean")).read_text()
    source += "\n theorem and_swap_0" + original.split("\n theorem and_swap_0", 1)[1]
    source += FOOTER
    for a, b, equal in [
        ("let/base", "let/renamed", True),
        ("let/base", "let/different", False),
        ("goals/ordered", "goals/reversed", False),
        ("goals/ordered", "goals/single", False),
        ("goals/single", "goals/empty", False),
        ("printer/all", "printer/narrow", True),
        ("printer/all", "equivalent/rename/0", True),
        ("boundary/closed", "boundary/introduced", False),
        ("universe_name/u", "universe_name/v", False),
        ("sharing/shared", "sharing/separate", False),
    ]:
        expected.append({"a": a, "b": b, "equal": equal})
    (OUT / "Suite.lean").write_text(source)
    (OUT / "expected.json").write_text(json.dumps(expected, indent=2) + "\n")


if __name__ == "__main__":
    main()
