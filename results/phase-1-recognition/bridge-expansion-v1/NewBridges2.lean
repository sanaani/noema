import Mathlib
import Lean
import Lean

/- Typed ordered-obligation serialization. No pretty printer is used here.
   Expressions and universe parameters must be resolved. The caller freezes
   environment/policy identity; this module does not serialize a tactic VM. -/
open Lean Meta
namespace Noema

def node (tag : String) (args : Array Json := #[]) : Json :=
  Json.arr (#[toJson tag] ++ args)

def nameJson : Name → Json
  | .anonymous => node "anonymous"
  | .str p s => node "name" #[nameJson p, toJson s]
  | .num p n => node "numName" #[nameJson p, toJson n]

def levelJson : Level → Except String Json
  | .zero => return node "zero"
  | .succ l => return node "succ" #[← levelJson l]
  | .max a b => return node "max" #[← levelJson a, ← levelJson b]
  | .imax a b => return node "imax" #[← levelJson a, ← levelJson b]
  | .param n => return node "universe" #[nameJson n]
  | .mvar _ => throw "unresolved universe metavariable"

-- Binder names, metadata and binder elaboration hints are deliberately absent.
-- Every expression constructor and argument boundary has an explicit tag.
def exprJson (e : Expr) (depth : Nat := 0) : Except String Json := do
  match e with
  | .bvar i =>
    if i >= depth then throw "loose bound variable"
    return node "var" #[toJson i]
  | .fvar _ => throw "unabstracted free variable"
  | .mvar _ => throw "unresolved expression metavariable"
  | .sort l => return node "sort" #[← levelJson l.normalize]
  | .const n ls => return node "const" #[nameJson n, toJson (← ls.mapM (fun l => levelJson l.normalize))]
  | .app f a => return node "app" #[← exprJson f depth, ← exprJson a depth]
  | .forallE _ a b _ => return node "forall" #[← exprJson a depth, ← exprJson b (depth+1)]
  | .lam _ a b _ => return node "lambda" #[← exprJson a depth, ← exprJson b (depth+1)]
  | .letE _ t v b _ =>
    return node "let" #[← exprJson t depth, ← exprJson v depth, ← exprJson b (depth+1)]
  | .lit (.natVal n) => return node "nat" #[toJson n]
  | .lit (.strVal s) => return node "string" #[toJson s]
  | .proj n i b => return node "projection" #[nameJson n, toJson i, ← exprJson b depth]
  | .mdata _ b => exprJson b depth

-- Kernel-checked local invariance laws. They hold for arbitrary names, binder
-- annotations, domains and bodies, including the rejection branches.
theorem forall_names (n m : Name) (a b : Expr) (i j : BinderInfo) (d : Nat) :
    exprJson (.forallE n a b i) d = exprJson (.forallE m a b j) d := rfl
theorem lambda_names (n m : Name) (a b : Expr) (i j : BinderInfo) (d : Nat) :
    exprJson (.lam n a b i) d = exprJson (.lam m a b j) d := rfl
theorem metadata_irrelevant (md : MData) (e : Expr) (d : Nat) :
    exprJson (.mdata md e) d = exprJson e d := rfl

def normalize (e : Expr) : MetaM Expr := do
  let e ← instantiateMVars e
  if e.hasMVar then throwError "unresolved metavariable"
  let result ← withTransparency .reducible do
    Meta.transform e
      (pre := fun e => do
        let e := e.consumeMData
        return .continue (← whnf e))
      (post := fun e => do
        let r := (← whnf e).consumeMData.eta
        if r == e then return .done r else return .visit r)
  unless ← isDefEq e result do throwError "normalization changed expression"
  return result

structure Captured where
  shape : Array Nat
  closedFields : Array Expr
  payload : Json
  deriving Inhabited

-- Acquisition buffer used by the audit commands in a separate importing module.
initialize samples : IO.Ref (Array (String × Captured)) ← IO.mkRef #[]

def capture (goals : List MVarId) : MetaM Captured := do
  let mut shape := #[]
  let mut fields := #[]
  let mut goalJson := #[]
  let mut sharedLocals : Array FVarId := #[]
  for goal in goals do
    let (gshape, gfields, gjson, locals) ← goal.withContext do
      let mut xs : Array Expr := #[]
      let mut declarations : Array Json := #[]
      let mut fields : Array Expr := #[]
      let mut shape : Array Nat := #[]
      let field (e : Expr) (xs : Array Expr) : MetaM (Expr × Json) := do
        let e ← instantiateMVars e
        if e.hasMVar then throwError "unresolved metavariable"
        let normalized ← normalize e
        let json ← match exprJson (normalized.abstract xs) xs.size with
          | .ok value => pure value
          | .error reason => throwError "{reason}"
        let closed ← instantiateMVars (← mkLambdaFVars xs e (usedLetOnly := false))
        if closed.hasFVar || closed.hasMVar || closed.hasLooseBVars then
          throwError "open field in State"
        return (closed, json)
      for decl in (← getLCtx) do
        let (closedType, typeJson) ← field decl.type xs
        fields := fields.push closedType
        if let some value := decl.value? then
          let (closedValue, valueJson) ← field value xs
          fields := fields.push closedValue
          declarations := declarations.push (node "definition" #[typeJson, valueJson])
          shape := shape.push 1
        else
          declarations := declarations.push (node "assumption" #[typeJson])
          shape := shape.push 0
        xs := xs.push decl.toExpr
      let (closedTarget, targetJson) ← field (← goal.getType) xs
      fields := fields.push closedTarget
      return (#[xs.size] ++ shape, fields, node "goal" #[toJson declarations, targetJson],
        xs.map Expr.fvarId!)
    let mut sharing : Array Nat := #[]
    for fvar in locals do
      if let some index := sharedLocals.findIdx? (· == fvar) then
        sharing := sharing.push index
      else
        sharing := sharing.push sharedLocals.size
        sharedLocals := sharedLocals.push fvar
    shape := shape ++ gshape ++ sharing
    fields := fields ++ gfields
    goalJson := goalJson.push (node "scoped-goal" #[toJson sharing, gjson])
  return ⟨#[goals.length] ++ shape, fields, node "ordered-obligations-v1" goalJson⟩

-- Bounded inventory relation. Each call is isolated so checking one pair cannot
-- assign metavariables or alter a later State. Input capture rejects mvars.
def equivalent (a b : Captured) : MetaM Bool := withoutModifyingState do
  if a.shape != b.shape || a.closedFields.size != b.closedFields.size then return false
  for x in a.closedFields, y in b.closedFields do
    unless ← withTransparency .all (isDefEq x y) do return false
  return true

end Noema
open Lean Meta Elab Command Noema
open scoped IntermediateField Pointwise
set_option linter.setOption false
set_option maxHeartbeats 0
elab "typed_center " target:ident : command => do
  let name := target.getId
  let info ← getConstInfo name
  unless info matches .thmInfo _ do throwError "not a theorem"
  let (_, ax) := ((CollectAxioms.collect name).run (← getEnv)).run {}
  for a in ax.axioms do
    unless a == ``propext || a == ``Classical.choice || a == ``Quot.sound do
      throwError "unexpected axiom {a} for {name}"
  liftTermElabM do
    let closedGoal ← mkFreshExprMVar info.type
    let closed ← capture [closedGoal.mvarId!]
    let introduced ← forallTelescope info.type fun _ body => do
      let goal ← mkFreshExprMVar body
      capture [goal.mvarId!]
    IO.println <| "CENTER " ++ (Json.mkObj [
      ("name", toJson name.toString),
      ("closed_shape", toJson closed.shape), ("closed_payload", closed.payload),
      ("introduced_shape", toJson introduced.shape), ("introduced_payload", introduced.payload)]).compress
typed_center MeasureTheory.Measure.map_linearMap_addHaar_pi_eq_smul_addHaar
