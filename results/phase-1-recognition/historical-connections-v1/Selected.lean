import Mathlib.NumberTheory.SumTwoSquares
import Mathlib.NumberTheory.ZetaValues
import Mathlib.FieldTheory.Galois
import Mathlib.Data.Complex.Exponential
import Mathlib.GroupTheory.Perm.Cycle.Type
import Lean

open Lean Meta Elab Command
open scoped IntermediateField Pointwise

set_option linter.setOption false
set_option pp.universes false
set_option maxHeartbeats 0

elab "center_catalog" : command => do
  let env ← getEnv
  for (name, info) in env.constants.toList do
    if let .thmInfo _ := info then
      if let some idx := env.getModuleIdxFor? name then
        let modName := env.header.moduleNames[idx.toNat]!
        if modName.toString.startsWith "Mathlib." && !name.isInternal then
          liftTermElabM do
            let goal ← mkFreshExprMVar info.type
            let display ← ppGoal goal.mvarId!
            IO.println <| "CATALOG " ++ (Json.mkObj [
              ("name", toJson name.toString),
              ("module", toJson modName.toString),
              ("closed", toJson (display.pretty 1000))]).compress

elab "capture_center " target:ident : command => do
  let name := target.getId
  let info ← getConstInfo name
  unless info matches .thmInfo _ do throwError "not a theorem"
  let (_, ax) := ((CollectAxioms.collect name).run (← getEnv)).run {}
  for a in ax.axioms do
    unless a == ``propext || a == ``Classical.choice || a == ``Quot.sound do
      throwError "unexpected axiom {a}"
  liftTermElabM do
    let goal ← mkFreshExprMVar info.type
    let closed ← ppGoal goal.mvarId!
    let render : TermElabM String := do
      let mut display := (← ppExpr info.type).pretty 1000
      if name == `Seminorm.coe_bot then
        display := "∀ {𝕜 : Type u_3} {E : Type u_7} [inst : SeminormedRing 𝕜] [inst_1 : AddCommGroup E] [inst_2 : _root_.Module 𝕜 E], ⇑(⊥ : Seminorm 𝕜 E) = (0 : E → ℝ)"
      if name == `hasSum_fourier_series_L2 then
        display := "∀ {T : ℝ} [hT : Fact (0 < T)] (f : MeasureTheory.Lp ℂ 2 (@AddCircle.haarAddCircle T hT)), HasSum (fun (i : ℤ) => fourierCoeff (T := T) f i • fourierLp (T := T) 2 i) f"
      let stx ← match Parser.runParserCategory (← getEnv) `term display with
        | .ok s => pure s
        | .error err => throwError "typed display parse failed: {err}\n{display}"
      withTheReader Core.Context (fun ctx => {ctx with openDecls := []}) <| Term.withLevelNames info.levelParams do
        let rebuilt ← Term.elabType stx
        Term.synthesizeSyntheticMVarsNoPostponing
        unless ← isDefEq rebuilt info.type do
          throwError "typed display does not reconstruct theorem: {display}"
        let rebuilt ← instantiateMVars rebuilt
        if rebuilt.hasExprMVar then throwError "typed display left metavariables"
      Term.throwErrorIfErrors
      return "⊢ " ++ display
    let saved ← Term.saveState
    let (typed, fallback) ← try
      let display ← withOptions (fun o => (o.setBool `pp.analyze true).setBool `pp.numericTypes true |>.setBool `pp.funBinderTypes true) render
      saved.restore
      pure (display, false)
    catch _ =>
      saved.restore
      let display ← withOptions (fun o =>
        o.setBool `pp.analyze false |>.setBool `pp.explicit true
          |>.setBool `pp.proofs false |>.setBool `pp.universes true
          |>.setBool `pp.fullNames true |>.setBool `pp.notation false
          |>.setBool `pp.fieldNotation false |>.setBool `pp.deepTerms true) render
      saved.restore
      pure (display, true)
    let introduced ← forallTelescope info.type fun xs body => do
      unless ← isDefEq (← mkForallFVars xs body) info.type do
        throwError "introduced telescope changed theorem type"
      let g ← mkFreshExprMVar body
      return (← ppGoal g.mvarId!).pretty 1000
    IO.println <| "CENTER " ++ (Json.mkObj [
      ("name", toJson name.toString),
      ("closed", toJson (closed.pretty 1000)),
      ("introduced", toJson introduced),
      ("typed", toJson typed),
      ("typed_roundtrip_defeq", toJson true),
      ("typed_explicit_fallback", toJson fallback),
      ("typed_annotation_repair", toJson (name == `Seminorm.coe_bot || name == `hasSum_fourier_series_L2)),
      ("axioms", toJson (ax.axioms.map Name.toString)),
      ("type_expr", toJson (reprStr info.type))]).compress


capture_center Real.sin_add
capture_center Complex.exp_add
capture_center Complex.exp_mul_I
capture_center Nat.Prime.sq_add_sq
capture_center GaussianInt.prime_iff_mod_four_eq_three_of_nat_prime
capture_center GaussianInt.sq_add_sq_of_nat_prime_of_not_irreducible
capture_center IntermediateField.adjoin.finrank
capture_center IsGalois.card_aut_eq_finrank
capture_center IsGalois.IntermediateField.AdjoinSimple.card_aut_eq_finrank
capture_center hasSum_zeta_two
capture_center hasSum_fourier_series_of_summable
capture_center hasSum_one_div_nat_pow_mul_cos
capture_center coe_convexAddSubmonoid
capture_center sSupHom.coe_copy
capture_center HasCompactSupport.extend_zero
capture_center AddSubmonoid.LocalizationMap.lift_left_inverse
capture_center Set.vadd_mem_vadd
capture_center HasSum.tsum_eq
capture_center IsNilpotent.zero
capture_center IsBoundedLinearMap.fderivWithin
capture_center ite_eq_iff'
capture_center MeasureTheory.measure_eq_top_iff_of_symmDiff
capture_center ContinuousMap.specializes_coe
capture_center StarAlgHom.coe_codRestrict
capture_center Seminorm.coe_bot
capture_center AddCircle.exists_gcd_eq_one_of_isOfFinAddOrder
capture_center Set.OrdConnected.dual
capture_center Set.ite_inter_inter
capture_center IsModularLattice.inf_sup_inf_assoc
capture_center Part.of_toOption
capture_center OrderAddMonoidHom.toOrderHom_injective
capture_center Asymptotics.IsEquivalent.trans_isTheta
capture_center Embedding.toOpenEmbedding_of_surjective
capture_center IsSMulRegular.isLeftRegular
capture_center ENat.top_pow
capture_center IsMulCentral.right_comm
capture_center IsLowerSet.compl
capture_center OmegaCompletePartialOrder.ContinuousHom.ωSup_bind
capture_center Set.Equicontinuous.closure
capture_center Polynomial.card_support_binomial
capture_center Field.FiniteDimensional.of_finite_intermediateField
capture_center iSup_eq_iSup_of_partialSups_eq_partialSups
capture_center iInf_univ
capture_center TopologicalSpace.Opens.partialHomeomorphSubtypeCoe_target
capture_center HasDerivAt.const_smul
capture_center IntermediateField.algHomEquivAlgHomOfSplits_apply
capture_center Odd.zpow_neg
capture_center Equiv.Perm.sumCongr_one
capture_center Set.liftCover_coe
capture_center finite_of_linearIndependent
capture_center Filter.map_one'
capture_center Relation.equivalence_join_reflTransGen
capture_center MulOpposite.op_inj
capture_center MulChar.ringHomComp_eq_one_iff
capture_center Set.Ioc_union_Ioi_eq_Ioi
capture_center NNRat.commute_cast
capture_center Polynomial.expand_mul
capture_center ofLex_neg
capture_center Finset.card_nbij
capture_center Urysohns.CU.left_U_subset
capture_center iSup_iSup_eq_left
capture_center Subgroup.tendsto_coe_cofinite_of_discrete
capture_center Function.Periodic.exists_mem_Ioc
capture_center isLUB_of_mem_closure
capture_center interior_eq_nhds
capture_center IsSelfAdjoint.all
capture_center Complex.cosh_add
capture_center IsRightRegular.pow
capture_center Ordinal.enumOrd_def'
capture_center MeasurableSpace.measurableSet_enumerateCountable_countableGeneratingSet
capture_center Polynomial.monomial_mul_monomial
capture_center IsUnit.isRegular
capture_center Monotone.map_inf
capture_center ENNReal.le_tsum_condensed
capture_center Submodule.span_attach_biUnion
capture_center Real.continuousAt_arcsin
capture_center Real.cos_add
capture_center Real.cos_sub
capture_center Real.sin_sub
capture_center Real.cos_sub_cos
capture_center Complex.exp_sub
capture_center Complex.exp_eq_exp_iff_exp_sub_eq_one
capture_center Complex.abs_exp_eq_iff_re_eq
capture_center Complex.cpow_def_of_ne_zero
capture_center Nat.sq_add_sq_modEq
capture_center Nat.sq_add_sq_zmodEq
capture_center ZMod.mod_four_ne_three_of_sq_eq_neg_one
capture_center ZMod.exists_sq_eq_neg_one_iff
capture_center GaussianInt.mod_four_eq_three_of_nat_prime_of_prime
capture_center GaussianInt.prime_of_nat_prime_of_mod_four_eq_three
capture_center minpoly.natDegree_le
capture_center IntermediateField.adjoin.finiteDimensional
capture_center minpoly.degree_le
capture_center IntermediateField.isAlgebraic_adjoin_simple
capture_center IsGalois.of_card_aut_eq_finrank
capture_center AlgHom.card
capture_center IntermediateField.finrank_fixedField_eq_card
capture_center IsGalois.card_fixingSubgroup_eq_finrank
capture_center hasSum_L_function_mod_four_eval_three
capture_center hasSum_geometric_two
capture_center hasSum_zeta_four
capture_center Real.sin_pi_div_six
capture_center has_pointwise_sum_fourier_series_of_summable
capture_center hasSum_fourier_series_L2
capture_center fourierCoeff.const_mul
capture_center fourierCoeff_toLp
