
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

state "equivalent/rename/0" : ∀ (x : Nat), x = x

state "equivalent/rename/1" : ∀ (y : Nat), y = y

state "equivalent/dependent/0" : ∀ (A : Type u) (x : A), x = x

state "equivalent/dependent/1" : ∀ (B : Type u) (y : B), y = y

state "equivalent/beta/0" : ∀ (n : Nat), n = n

state "equivalent/beta/1" : ∀ (n : Nat), (fun x : Nat => x) n = n

state "equivalent/nested_beta/0" : ∀ (n : Nat), n = n

state "equivalent/nested_beta/1" : ∀ (n : Nat), (fun f : Nat → Nat => f n) (fun x => x) = n

state "equivalent/zeta/0" : ∀ (n : Nat), n = n

state "equivalent/zeta/1" : ∀ (n : Nat), (let k := n; k) = n

state "equivalent/projection/0" : ∀ (n m : Nat), n = n

state "equivalent/projection/1" : ∀ (n m : Nat), (n, m).1 = n

state "equivalent/iota/0" : ∀ (n : Nat), n = n

state "equivalent/iota/1" : ∀ (n : Nat), (match true with | true => n | false => 0) = n

state "equivalent/eta/0" : ∀ (f : Nat → Nat), f = f

state "equivalent/eta/1" : ∀ (f : Nat → Nat), (fun x => f x) = f

state "equivalent/reducible_alias/0" : ∀ (p : Prop), p ∨ p

state "equivalent/reducible_alias/1" : ∀ (p : Prop), reducibleAlias (p ∨ p)

state "equivalent/ordinary_alias/0" : ∀ (p : Prop), p ∨ p

state "equivalent/ordinary_alias/1" : ∀ (p : Prop), ordinaryAlias (p ∨ p)

state "equivalent/context_alias/0" : ∀ (p : Prop) (h : p ∨ p), p ∨ p

state "equivalent/context_alias/1" : ∀ (p : Prop) (h : ordinaryAlias (p ∨ p)), p ∨ p

state "equivalent/instance/0" : ∀ (A : Type u) [i : Inhabited A], (default : A) = default

state "equivalent/instance/1" : ∀ (B : Type u) [j : Inhabited B], (@Inhabited.default B j) = default

state "equivalent/shadow/0" : ∀ (f : Nat → Nat), (fun x => (fun x => x) x) = f

state "equivalent/shadow/1" : ∀ (g : Nat → Nat), (fun a => (fun b => b) a) = g

state "equivalent/level_arithmetic/0" : ∀ (A : Sort (max u u)) (a : A), a = a

state "equivalent/level_arithmetic/1" : ∀ (B : Sort u) (b : B), b = b

state "equivalent/string/0" : "x ≠ y" = "x ≠ y"

state "equivalent/string/1" : id "x ≠ y" = "x ≠ y"

state "equivalent/dependent_fn/0" : ∀ (A : Type u) (B : A → Type v) (f : (x : A) → B x), f = f

state "equivalent/dependent_fn/1" : ∀ (X : Type u) (Y : X → Type v) (g : (z : X) → Y z), (fun z => g z) = g

state "distinct/goal/0" : ∀ (n : Nat), n = 0

state "distinct/goal/1" : ∀ (n : Nat), n = 1

state "distinct/type/0" : ∀ (n : Nat), n = n

state "distinct/type/1" : ∀ (n : Int), n = n

state "distinct/unused/0" : ∀ (n : Nat), n = n

state "distinct/unused/1" : ∀ (n m : Nat), n = n

state "distinct/dependent_reference/0" : ∀ (n m : Nat), n = 0

state "distinct/dependent_reference/1" : ∀ (n m : Nat), m = 0

state "distinct/literal/0" : "x" = "x"

state "distinct/literal/1" : "y" = "x"

state "distinct/operator/0" : ∀ (xs : List Nat), xs = []

state "distinct/operator/1" : ∀ (xs : List Nat), xs ≠ []

state "distinct/assumption/0" : ∀ (p q : Prop) (h : p), p ∨ q

state "distinct/assumption/1" : ∀ (p q : Prop) (h : q), p ∨ q

state "distinct/universe/0" : ∀ (A : Type) (a : A), a = a

state "distinct/universe/1" : ∀ (A : Type 1) (a : A), a = a

 theorem and_swap_0 : ∀ (A B : Prop), A ∧ B → B ∧ A := by
  observe "and_swap/0/0"
  intro A B h
  observe "and_swap/0/1"
  constructor
  observe "and_swap/0/2"
  exact h.2
  observe "and_swap/0/3"
  exact h.1
  observe "and_swap/0/4"
audit_fixture and_swap_0

 theorem and_swap_1 : ∀ (A B : Prop), A ∧ B → B ∧ A := by
  observe "and_swap/1/0"
  intro A B h
  observe "and_swap/1/1"
  exact ⟨h.2, h.1⟩
  observe "and_swap/1/2"
audit_fixture and_swap_1

 theorem and_assoc_0 : ∀ (A B C : Prop), (A ∧ B) ∧ C → A ∧ (B ∧ C) := by
  observe "and_assoc/0/0"
  intro A B C h
  observe "and_assoc/0/1"
  constructor
  observe "and_assoc/0/2"
  exact h.1.1
  observe "and_assoc/0/3"
  constructor
  observe "and_assoc/0/4"
  exact h.1.2
  observe "and_assoc/0/5"
  exact h.2
  observe "and_assoc/0/6"
audit_fixture and_assoc_0

 theorem and_assoc_1 : ∀ (A B C : Prop), (A ∧ B) ∧ C → A ∧ (B ∧ C) := by
  observe "and_assoc/1/0"
  intro A B C h
  observe "and_assoc/1/1"
  exact ⟨h.1.1, ⟨h.1.2, h.2⟩⟩
  observe "and_assoc/1/2"
audit_fixture and_assoc_1

 theorem imp_comp_0 : ∀ (A B C : Prop), (A → B) → (B → C) → A → C := by
  observe "imp_comp/0/0"
  intro A B C f g h
  observe "imp_comp/0/1"
  apply g
  observe "imp_comp/0/2"
  apply f
  observe "imp_comp/0/3"
  exact h
  observe "imp_comp/0/4"
audit_fixture imp_comp_0

 theorem imp_comp_1 : ∀ (A B C : Prop), (A → B) → (B → C) → A → C := by
  observe "imp_comp/1/0"
  intro A B C f g h
  observe "imp_comp/1/1"
  exact g (f h)
  observe "imp_comp/1/2"
audit_fixture imp_comp_1

 theorem or_swap_0 : ∀ (A B : Prop), A ∨ B → B ∨ A := by
  observe "or_swap/0/0"
  intro A B h
  observe "or_swap/0/1"
  apply Or.elim h
  observe "or_swap/0/2"
  exact Or.inr
  observe "or_swap/0/3"
  exact Or.inl
  observe "or_swap/0/4"
audit_fixture or_swap_0

 theorem or_swap_1 : ∀ (A B : Prop), A ∨ B → B ∨ A := by
  observe "or_swap/1/0"
  intro A B h
  observe "or_swap/1/1"
  exact Or.elim h Or.inr Or.inl
  observe "or_swap/1/2"
audit_fixture or_swap_1

 theorem eq_symm_0 : ∀ (a b : Nat), a = b → b = a := by
  observe "eq_symm/0/0"
  intro a b h
  observe "eq_symm/0/1"
  apply Eq.symm
  observe "eq_symm/0/2"
  exact h
  observe "eq_symm/0/3"
audit_fixture eq_symm_0

 theorem eq_symm_1 : ∀ (a b : Nat), a = b → b = a := by
  observe "eq_symm/1/0"
  intro a b h
  observe "eq_symm/1/1"
  exact h.symm
  observe "eq_symm/1/2"
audit_fixture eq_symm_1

 theorem eq_trans_0 : ∀ (a b c : Nat), a = b → b = c → a = c := by
  observe "eq_trans/0/0"
  intro a b c h k
  observe "eq_trans/0/1"
  apply Eq.trans h
  observe "eq_trans/0/2"
  exact k
  observe "eq_trans/0/3"
audit_fixture eq_trans_0

 theorem eq_trans_1 : ∀ (a b c : Nat), a = b → b = c → a = c := by
  observe "eq_trans/1/0"
  intro a b c h k
  observe "eq_trans/1/1"
  exact h.trans k
  observe "eq_trans/1/2"
audit_fixture eq_trans_1

 theorem nat_assoc_0 : ∀ (a b c : Nat), (a + b) + c = a + (b + c) := by
  observe "nat_assoc/0/0"
  intro a b c
  observe "nat_assoc/0/1"
  exact Nat.add_assoc a b c
  observe "nat_assoc/0/2"
audit_fixture nat_assoc_0

 theorem nat_assoc_1 : ∀ (a b c : Nat), (a + b) + c = a + (b + c) := by
  observe "nat_assoc/1/0"
  intro a b c
  observe "nat_assoc/1/1"
  simp only [Nat.add_assoc]
  observe "nat_assoc/1/2"
audit_fixture nat_assoc_1

 theorem list_assoc_0 : ∀ (a b c : List Nat), (a ++ b) ++ c = a ++ (b ++ c) := by
  observe "list_assoc/0/0"
  intro a b c
  observe "list_assoc/0/1"
  exact List.append_assoc a b c
  observe "list_assoc/0/2"
audit_fixture list_assoc_0

 theorem list_assoc_1 : ∀ (a b c : List Nat), (a ++ b) ++ c = a ++ (b ++ c) := by
  observe "list_assoc/1/0"
  intro a b c
  observe "list_assoc/1/1"
  simp only [List.append_assoc]
  observe "list_assoc/1/2"
audit_fixture list_assoc_1

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
