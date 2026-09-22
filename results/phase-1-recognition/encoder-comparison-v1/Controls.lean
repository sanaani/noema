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


-- Limited, explicit policy: alpha annotations, metadata, beta/zeta and id.
-- This deliberately does not unfold arbitrary definitions or prove equivalences.
partial def canonicalExpr (e : Expr) (depth : Nat := 0) : Expr :=
  let name := Name.mkSimple s!"v{depth}"
  match e with
  | .mdata _ b => canonicalExpr b depth
  | .letE _ _ value body _ => canonicalExpr (body.instantiate1 value) depth
  | .app (.app (.const ``id _) _) value => canonicalExpr value depth
  | .app f a =>
    let f := canonicalExpr f depth
    let a := canonicalExpr a depth
    match f with
    | .lam _ _ body _ => canonicalExpr (body.instantiate1 a) depth
    | _ => .app f a
  | .forallE _ a b bi =>
    .forallE name (canonicalExpr a depth) (canonicalExpr b (depth+1)) bi
  | .lam _ a b bi => .lam name (canonicalExpr a depth) (canonicalExpr b (depth+1)) bi
  | .proj n i b => .proj n i (canonicalExpr b depth)
  | _ => e

def captureGoal (goal : MVarId) (arm : String) : MetaM (String × String × String × Json) :=
  goal.withContext do
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
    if arm == "defeq_id" then target ← mkAppM ``id #[target]
    withLCtx ctx (← getLocalInstances) do
      let transformed ← closedGoal target
      unless ← isDefEq closed transformed do throwError "changed obligation"
      if transformed.hasExprMVar then throwError "unresolved transformed goal"
      let g ← mkFreshExprMVar target
      let opts ← getOptions
      let printOpts := if arm == "pretty_no_notation" then
        opts.setBool `pp.notation false |>.setBool `pp.fullNames true else opts
      let display ← withOptions (fun _ => printOpts) (ppGoal g.mvarId!)
      let signatureExpr := canonicalExpr transformed
      unless ← isDefEq signatureExpr transformed do throwError "normalization changed type"
      if signatureExpr.hasExprMVar || signatureExpr.hasFVar || signatureExpr.hasLooseBVars then
        throwError "open canonical signature"
      let signature := (Json.mkObj [
        ("local_declarations", toJson ctx.getFVarIds.size),
        ("closed_expr", toJson (reprStr signatureExpr))]).compress
      let mut normalizedCtx := ctx
      for decl in ctx do
        -- The frozen suite contains no local lets; reject instead of dropping a value.
        if decl.isLet then throwError "local lets unsupported in this finite control"
        let ty := canonicalExpr decl.type
        unless ← isDefEq ty decl.type do throwError "context normalization changed type"
        normalizedCtx := normalizedCtx.modifyLocalDecl decl.fvarId fun d =>
          (d.setUserName (Name.mkSimple s!"s{d.index}")).setType ty
      let normalized := canonicalExpr target
      let canonicalDisplay ← withLCtx normalizedCtx (← getLocalInstances) do
        unless ← isDefEq (← closedGoal normalized) closed do
          throwError "canonical display changed obligation"
        let cg ← mkFreshExprMVar normalized
        withOptions (fun o => o.setBool `pp.notation false |>.setBool `pp.fullNames true
          |>.setBool `pp.universes true |>.setBool `pp.showLetValues true) do
          return (← ppGoal cg.mvarId!).pretty 1000
      return (display.pretty (if arm == "pretty_narrow" then 20 else 1000),
        canonicalDisplay, signature, Json.mkObj [
          ("original_closed_expr", toJson (reprStr closed)),
          ("transformed_closed_expr", toJson (reprStr transformed)),
          ("defeq", toJson true), ("canonical_defeq", toJson true)])

elab "observe " label:str : tactic => do
  let goals ← getGoals
  for arm in ["original", "alpha", "pretty_narrow", "pretty_no_notation", "defeq_id"] do
    let mut texts : Array String := #[]
    let mut canonicals : Array String := #[]
    let mut signatures : Array String := #[]
    let mut evidence : Array Json := #[]
    for goal in goals do
      let (text, canonical, signature, cert) ← captureGoal goal arm
      texts := texts.push text
      canonicals := canonicals.push canonical
      signatures := signatures.push signature
      evidence := evidence.push cert
    IO.println <| "STATE " ++ (Json.mkObj [
      ("checkpoint", toJson label.getString), ("arm", toJson arm),
      ("text", toJson (if goals.isEmpty then "no goals" else
        String.intercalate "\n\n" texts.toList)),
      ("canonical_text", toJson (String.intercalate "\n\n" canonicals.toList)),
      ("structural_text", toJson (toJson signatures).compress),
      ("goals", toJson evidence), ("goal_count", toJson goals.length)]).compress

elab "contrast " label:str lhs:term " versus " rhs:term : tactic => do
  withMainContext do
    let left ← Term.elabType lhs
    let right ← Term.elabType rhs
    Term.synthesizeSyntheticMVarsNoPostponing
    if ← isDefEq left right then throwError "contrast accidentally defeq"
    let saved ← getGoals
    for (ty, side) in [(left, "a"), (right, "b")] do
      let g ← mkFreshExprMVar ty
      setGoals [g.mvarId!]
      let label := Syntax.mkStrLit (label.getString ++ "/" ++ side ++ "/0")
      evalTactic (← `(tactic| observe $label:str))
    setGoals saved
    IO.println <| "CONTRAST " ++ (Json.mkObj [
      ("id", toJson label.getString), ("non_defeq", toJson true)]).compress

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

example (P Q : Prop) : True := by
  contrast "c00" (P ∧ Q) versus (P ∨ Q)
  trivial
theorem witness_0 : ¬ ((False ∧ True) ↔ (False ∨ True)) := by decide
audit_fixture witness_0

example (P Q : Prop) : True := by
  contrast "c01" (P → Q) versus (Q → P)
  trivial
theorem witness_1 : ¬ ((False → True) ↔ (True → False)) := by decide
audit_fixture witness_1

example (P : Prop) : True := by
  contrast "c02" (P) versus (¬ P)
  trivial
theorem witness_2 : ¬ ((True) ↔ (¬ True)) := by decide
audit_fixture witness_2

example (P Q : Prop) : True := by
  contrast "c03" (P ∧ Q) versus (P)
  trivial
theorem witness_3 : ¬ ((True ∧ False) ↔ (True)) := by decide
audit_fixture witness_3

example (P Q : Prop) : True := by
  contrast "c04" (P ∨ Q) versus (P)
  trivial
theorem witness_4 : ¬ ((False ∨ True) ↔ (False)) := by decide
audit_fixture witness_4

example (P Q : Prop) : True := by
  contrast "c05" (P → Q) versus (P ∧ Q)
  trivial
theorem witness_5 : ¬ ((False → False) ↔ (False ∧ False)) := by decide
audit_fixture witness_5

example (P Q : Prop) : True := by
  contrast "c06" (P ↔ Q) versus (P ∨ Q)
  trivial
theorem witness_6 : ¬ ((False ↔ False) ↔ (False ∨ False)) := by decide
audit_fixture witness_6

example (P Q : Prop) : True := by
  contrast "c07" (¬ (P ∧ Q)) versus (¬ P ∧ ¬ Q)
  trivial
theorem witness_7 : ¬ ((¬ (True ∧ False)) ↔ (¬ True ∧ ¬ False)) := by decide
audit_fixture witness_7

example (n : Nat) : True := by
  contrast "c08" (n = 0) versus (n = 1)
  trivial
theorem witness_8 : ¬ (((0 : Nat) = 0) ↔ ((0 : Nat) = 1)) := by decide
audit_fixture witness_8

example (n m : Nat) : True := by
  contrast "c09" (n ≤ m) versus (n < m)
  trivial
theorem witness_9 : ¬ (((0 : Nat) ≤ 0) ↔ ((0 : Nat) < 0)) := by decide
audit_fixture witness_9

example (xs : List Nat) : True := by
  contrast "c10" (xs = []) versus (xs ≠ [])
  trivial
theorem witness_10 : ¬ ((([] : List Nat) = []) ↔ (([] : List Nat) ≠ [])) := by decide
audit_fixture witness_10

example (n m : Nat) : True := by
  contrast "c11" (n + m = m + n) versus (n + m = n)
  trivial
theorem witness_11 : ¬ (((0 : Nat) + 1 = 1 + 0) ↔ ((0 : Nat) + 1 = 0)) := by decide
audit_fixture witness_11
