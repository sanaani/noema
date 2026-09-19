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
elab "typed_cclosed " target:ident : command => do
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
    IO.println <| "CENTER " ++ (Json.mkObj [
      ("name", toJson name.toString),
      ("closed_shape", toJson closed.shape), ("closed_payload", closed.payload)]).compress
typed_cclosed AddCircle.exists_gcd_eq_one_of_isOfFinAddOrder
typed_cclosed AddSubmonoid.LocalizationMap.lift_left_inverse
typed_cclosed Asymptotics.IsEquivalent.trans_isTheta
typed_cclosed Complex.cosh_add
typed_cclosed Complex.exp_add
typed_cclosed Complex.exp_mul_I
typed_cclosed Complex.exp_sub
typed_cclosed ContinuousMap.specializes_coe
typed_cclosed ENNReal.le_tsum_condensed
typed_cclosed ENat.top_pow
typed_cclosed Embedding.toOpenEmbedding_of_surjective
typed_cclosed Equiv.Perm.sumCongr_one
typed_cclosed Field.FiniteDimensional.of_finite_intermediateField
typed_cclosed Filter.map_one'
typed_cclosed Finset.card_nbij
typed_cclosed Function.Periodic.exists_mem_Ioc
typed_cclosed GaussianInt.prime_iff_mod_four_eq_three_of_nat_prime
typed_cclosed GaussianInt.sq_add_sq_of_nat_prime_of_not_irreducible
typed_cclosed HasCompactSupport.extend_zero
typed_cclosed HasDerivAt.const_smul
typed_cclosed HasSum.tsum_eq
typed_cclosed IntermediateField.adjoin.finrank
typed_cclosed IntermediateField.algHomEquivAlgHomOfSplits_apply
typed_cclosed IsBoundedLinearMap.fderivWithin
typed_cclosed IsGalois.IntermediateField.AdjoinSimple.card_aut_eq_finrank
typed_cclosed IsGalois.card_aut_eq_finrank
typed_cclosed IsGalois.of_card_aut_eq_finrank
typed_cclosed IsLowerSet.compl
typed_cclosed IsModularLattice.inf_sup_inf_assoc
typed_cclosed IsMulCentral.right_comm
typed_cclosed IsNilpotent.zero
typed_cclosed IsRightRegular.pow
typed_cclosed IsSMulRegular.isLeftRegular
typed_cclosed IsSelfAdjoint.all
typed_cclosed IsUnit.isRegular
typed_cclosed MeasurableSpace.measurableSet_enumerateCountable_countableGeneratingSet
typed_cclosed MeasureTheory.measure_eq_top_iff_of_symmDiff
typed_cclosed Monotone.map_inf
typed_cclosed MulChar.ringHomComp_eq_one_iff
typed_cclosed MulOpposite.op_inj
typed_cclosed NNRat.commute_cast
typed_cclosed Nat.Prime.sq_add_sq
typed_cclosed Nat.sq_add_sq_modEq
typed_cclosed Odd.zpow_neg
typed_cclosed OmegaCompletePartialOrder.ContinuousHom.ωSup_bind
typed_cclosed OrderAddMonoidHom.toOrderHom_injective
typed_cclosed Ordinal.enumOrd_def'
typed_cclosed Part.of_toOption
typed_cclosed Polynomial.card_support_binomial
typed_cclosed Polynomial.expand_mul
typed_cclosed Polynomial.monomial_mul_monomial
typed_cclosed Real.continuousAt_arcsin
typed_cclosed Real.cos_add
typed_cclosed Real.sin_add
typed_cclosed Relation.equivalence_join_reflTransGen
typed_cclosed Seminorm.coe_bot
typed_cclosed Set.Equicontinuous.closure
typed_cclosed Set.Ioc_union_Ioi_eq_Ioi
typed_cclosed Set.OrdConnected.dual
typed_cclosed Set.ite_inter_inter
typed_cclosed Set.liftCover_coe
typed_cclosed Set.vadd_mem_vadd
typed_cclosed StarAlgHom.coe_codRestrict
typed_cclosed Subgroup.tendsto_coe_cofinite_of_discrete
typed_cclosed Submodule.span_attach_biUnion
typed_cclosed TopologicalSpace.Opens.partialHomeomorphSubtypeCoe_target
typed_cclosed Urysohns.CU.left_U_subset
typed_cclosed ZMod.euler_criterion
typed_cclosed ZMod.exists_sq_eq_neg_one_iff
typed_cclosed ZMod.mod_four_ne_three_of_sq_eq_neg_one
typed_cclosed ZMod.pow_card_sub_one_eq_one
typed_cclosed coe_convexAddSubmonoid
typed_cclosed deriv_add
typed_cclosed finite_of_linearIndependent
typed_cclosed hasSum_L_function_mod_four_eval_three
typed_cclosed hasSum_fourier_series_of_summable
typed_cclosed hasSum_one_div_nat_pow_mul_cos
typed_cclosed hasSum_zeta_two
typed_cclosed has_pointwise_sum_fourier_series_of_summable
typed_cclosed iInf_univ
typed_cclosed iSup_eq_iSup_of_partialSups_eq_partialSups
typed_cclosed iSup_iSup_eq_left
typed_cclosed interior_eq_nhds
typed_cclosed intervalIntegral.integral_add
typed_cclosed intervalIntegral.integral_eq_sub_of_hasDerivAt
typed_cclosed isLUB_of_mem_closure
typed_cclosed ite_eq_iff'
typed_cclosed minpoly.natDegree_le
typed_cclosed ofLex_neg
typed_cclosed sSupHom.coe_copy
typed_cclosed sq_eq_sq_iff_eq_or_eq_neg
