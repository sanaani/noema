"""Generate the independently normalized fixture and distinction controls in Lean."""

from pathlib import Path

from noema.paths import result_path

ROOT = Path(__file__).resolve().parents[1]
OUT = result_path("encoder-comparison-v1")

NORMALIZER = r"""
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
"""

# Context, proposition A, proposition B, explicit substituted propositions.
PAIRS = [
    ("(P Q : Prop)", "P ∧ Q", "P ∨ Q", "False ∧ True", "False ∨ True"),
    ("(P Q : Prop)", "P → Q", "Q → P", "False → True", "True → False"),
    ("(P : Prop)", "P", "¬ P", "True", "¬ True"),
    ("(P Q : Prop)", "P ∧ Q", "P", "True ∧ False", "True"),
    ("(P Q : Prop)", "P ∨ Q", "P", "False ∨ True", "False"),
    ("(P Q : Prop)", "P → Q", "P ∧ Q", "False → False", "False ∧ False"),
    ("(P Q : Prop)", "P ↔ Q", "P ∨ Q", "False ↔ False", "False ∨ False"),
    ("(P Q : Prop)", "¬ (P ∧ Q)", "¬ P ∧ ¬ Q", "¬ (True ∧ False)", "¬ True ∧ ¬ False"),
    ("(n : Nat)", "n = 0", "n = 1", "(0 : Nat) = 0", "(0 : Nat) = 1"),
    ("(n m : Nat)", "n ≤ m", "n < m", "(0 : Nat) ≤ 0", "(0 : Nat) < 0"),
    ("(xs : List Nat)", "xs = []", "xs ≠ []", "([] : List Nat) = []", "([] : List Nat) ≠ []"),
    ("(n m : Nat)", "n + m = m + n", "n + m = n", "(0 : Nat) + 1 = 1 + 0", "(0 : Nat) + 1 = 0"),
]


def main():
    source = (result_path("encoder-invariance-v1/Fixtures.lean")).read_text()
    prefix = source.split('elab "observe "')[0] + NORMALIZER
    audits = source.split('elab "audit_fixture "')[1].split("\n theorem and_swap_0")[0]
    prefix += '\nelab "audit_fixture "' + audits
    fixtures = prefix + "\n theorem and_swap_0" + source.split("\n theorem and_swap_0", 1)[1]
    (OUT / "Fixtures.lean").write_text(fixtures)
    controls = prefix
    for i, (ctx, a, b, va, vb) in enumerate(PAIRS):
        controls += (
            f'\nexample {ctx} : True := by\n  contrast "c{i:02}" ({a}) versus ({b})\n  trivial\n'
        )
        controls += (
            f"theorem witness_{i} : ¬ (({va}) ↔ ({vb})) := by decide\naudit_fixture witness_{i}\n"
        )
    (OUT / "Controls.lean").write_text(controls)


if __name__ == "__main__":
    main()
