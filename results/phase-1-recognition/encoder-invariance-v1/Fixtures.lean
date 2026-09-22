import Lean

open Lean Meta Elab Tactic Command

set_option linter.unusedVariables false
set_option pp.showLetValues true

-- Rename binder annotations, never free-variable identities or constants.
partial def alphaExpr (e : Expr) (depth : Nat := 0) : Expr :=
  let name := Name.mkSimple s!"v{depth}"
  match e with
  | .forallE _ a b bi => .forallE name (alphaExpr a depth) (alphaExpr b (depth+1)) bi
  | .lam _ a b bi => .lam name (alphaExpr a depth) (alphaExpr b (depth+1)) bi
  | .letE _ a v b nd =>
    .letE name (alphaExpr a depth) (alphaExpr v depth) (alphaExpr b (depth+1)) nd
  | .app f a => .app (alphaExpr f depth) (alphaExpr a depth)
  | .mdata m b => .mdata m (alphaExpr b depth)
  | .proj n i b => .proj n i (alphaExpr b depth)
  | _ => e

def closedGoal (target : Expr) : MetaM Expr := do
  let xs := (← getLCtx).getFVarIds.map mkFVar
  instantiateMVars (← mkForallFVars xs target (usedLetOnly := false))

elab "observe " label:str : tactic => do
  let goals ← getGoals
  for arm in ["original", "alpha", "pretty_narrow", "pretty_no_notation", "defeq_id"] do
    let mut texts : Array String := #[]
    let mut evidence : Array Json := #[]
    for goal in goals do
      let (text, certificate) ← goal.withContext do
        let original ← instantiateMVars (← goal.getType)
        let closed ← closedGoal original
        if closed.hasExprMVar then throwError "unresolved original goal"
        let mut ctx ← getLCtx
        let mut target := original
        if arm == "alpha" then
          for decl in ctx do
            ctx := ctx.modifyLocalDecl decl.fvarId fun d =>
              (d.setUserName (Name.mkSimple s!"x{d.index}")).setType (alphaExpr d.type)
          target := alphaExpr target
        if arm == "defeq_id" then
          target ← mkAppM ``id #[target]
        withLCtx ctx (← getLocalInstances) do
          let transformed ← closedGoal target
          unless ← isDefEq closed transformed do throwError "transformation changed obligation"
          if transformed.hasExprMVar then throwError "unresolved transformed goal"
          let displayGoal ← mkFreshExprMVar target
          let opts ← getOptions
          let opts := if arm == "pretty_no_notation" then
            opts.setBool `pp.notation false |>.setBool `pp.fullNames true else opts
          let display ← withOptions (fun _ => opts) (ppGoal displayGoal.mvarId!)
          return (display.pretty (if arm == "pretty_narrow" then 20 else 1000), Json.mkObj [
            ("original_closed_expr", toJson (reprStr closed)),
            ("transformed_closed_expr", toJson (reprStr transformed)),
            ("defeq", toJson true)])
      texts := texts.push text
      evidence := evidence.push certificate
    IO.println <| "STATE " ++ (Json.mkObj [
      ("checkpoint", toJson label.getString), ("arm", toJson arm),
      ("text", toJson (if goals.isEmpty then "no goals" else String.intercalate "\n\n" texts.toList)),
      ("goals", toJson evidence), ("goal_count", toJson goals.length)]).compress

elab "audit_fixture " name:ident : command => do
  let info ← getConstInfo name.getId
  unless info matches .thmInfo _ do throwError "fixture is not a theorem"
  let axioms ← collectAxioms name.getId
  for a in axioms do
    unless a == ``propext || a == ``Classical.choice || a == ``Quot.sound do
      throwError "unexpected axiom {a}"
  IO.println <| "PROOF " ++ (Json.mkObj [
    ("name", toJson name.getId.toString),
    ("axioms", toJson (axioms.map Name.toString))]).compress

-- The check must distinguish false obligations, not merely accept every pair.
run_meta do
  if ← isDefEq (mkConst ``True) (mkConst ``False) then
    throwError "negative defeq control accepted"
  IO.println "NEGATIVE_CONTROL rejected"

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
