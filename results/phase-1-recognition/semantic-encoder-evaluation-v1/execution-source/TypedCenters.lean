import Noema.StateEncoding
import Mathlib.NumberTheory.SumTwoSquares
import Mathlib.NumberTheory.ZetaValues
import Mathlib.FieldTheory.Galois
import Mathlib.Data.Complex.Exponential
import Mathlib.GroupTheory.Perm.Cycle.Type
import Lean
open Lean Meta Elab Command Noema
open scoped IntermediateField Pointwise
set_option linter.setOption false
set_option maxHeartbeats 0

elab "typed_center " target:ident : command => liftTermElabM do
  let name := target.getId
  let info ← getConstInfo name
  unless info matches .thmInfo _ do throwError "not a theorem"
  let closedGoal ← mkFreshExprMVar info.type
  let closed ← capture [closedGoal.mvarId!]
  let introduced ← forallTelescope info.type fun _ body => do
    let goal ← mkFreshExprMVar body
    capture [goal.mvarId!]
  IO.println <| "CENTER " ++ (Json.mkObj [
    ("name", toJson name.toString),
    ("closed_shape", toJson closed.shape), ("closed_payload", closed.payload),
    ("introduced_shape", toJson introduced.shape), ("introduced_payload", introduced.payload)]).compress

typed_center Real.sin_add
typed_center Complex.exp_add
typed_center Complex.exp_mul_I
typed_center Nat.Prime.sq_add_sq
typed_center GaussianInt.prime_iff_mod_four_eq_three_of_nat_prime
typed_center GaussianInt.sq_add_sq_of_nat_prime_of_not_irreducible
typed_center IntermediateField.adjoin.finrank
typed_center IsGalois.card_aut_eq_finrank
typed_center IsGalois.IntermediateField.AdjoinSimple.card_aut_eq_finrank
typed_center hasSum_zeta_two
typed_center hasSum_fourier_series_of_summable
typed_center hasSum_one_div_nat_pow_mul_cos
typed_center coe_convexAddSubmonoid
typed_center sSupHom.coe_copy
typed_center HasCompactSupport.extend_zero
typed_center AddSubmonoid.LocalizationMap.lift_left_inverse
typed_center Set.vadd_mem_vadd
typed_center HasSum.tsum_eq
typed_center IsNilpotent.zero
typed_center IsBoundedLinearMap.fderivWithin
typed_center ite_eq_iff'
typed_center MeasureTheory.measure_eq_top_iff_of_symmDiff
typed_center ContinuousMap.specializes_coe
typed_center StarAlgHom.coe_codRestrict
typed_center Seminorm.coe_bot
typed_center AddCircle.exists_gcd_eq_one_of_isOfFinAddOrder
typed_center Set.OrdConnected.dual
typed_center Set.ite_inter_inter
typed_center IsModularLattice.inf_sup_inf_assoc
typed_center Part.of_toOption
typed_center OrderAddMonoidHom.toOrderHom_injective
typed_center Asymptotics.IsEquivalent.trans_isTheta
typed_center Embedding.toOpenEmbedding_of_surjective
typed_center IsSMulRegular.isLeftRegular
typed_center ENat.top_pow
typed_center IsMulCentral.right_comm
typed_center IsLowerSet.compl
typed_center OmegaCompletePartialOrder.ContinuousHom.ωSup_bind
typed_center Set.Equicontinuous.closure
typed_center Polynomial.card_support_binomial
typed_center Field.FiniteDimensional.of_finite_intermediateField
typed_center iSup_eq_iSup_of_partialSups_eq_partialSups
typed_center iInf_univ
typed_center TopologicalSpace.Opens.partialHomeomorphSubtypeCoe_target
typed_center HasDerivAt.const_smul
typed_center IntermediateField.algHomEquivAlgHomOfSplits_apply
typed_center Odd.zpow_neg
typed_center Equiv.Perm.sumCongr_one
typed_center Set.liftCover_coe
typed_center finite_of_linearIndependent
typed_center Filter.map_one'
typed_center Relation.equivalence_join_reflTransGen
typed_center MulOpposite.op_inj
typed_center MulChar.ringHomComp_eq_one_iff
typed_center Set.Ioc_union_Ioi_eq_Ioi
typed_center NNRat.commute_cast
typed_center Polynomial.expand_mul
typed_center ofLex_neg
typed_center Finset.card_nbij
typed_center Urysohns.CU.left_U_subset
typed_center iSup_iSup_eq_left
typed_center Subgroup.tendsto_coe_cofinite_of_discrete
typed_center Function.Periodic.exists_mem_Ioc
typed_center isLUB_of_mem_closure
typed_center interior_eq_nhds
typed_center IsSelfAdjoint.all
typed_center Complex.cosh_add
typed_center IsRightRegular.pow
typed_center Ordinal.enumOrd_def'
typed_center MeasurableSpace.measurableSet_enumerateCountable_countableGeneratingSet
typed_center Polynomial.monomial_mul_monomial
typed_center IsUnit.isRegular
typed_center Monotone.map_inf
typed_center ENNReal.le_tsum_condensed
typed_center Submodule.span_attach_biUnion
typed_center Real.continuousAt_arcsin
typed_center Real.cos_add
typed_center Real.cos_sub
typed_center Real.sin_sub
typed_center Real.cos_sub_cos
typed_center Complex.exp_sub
typed_center Complex.exp_eq_exp_iff_exp_sub_eq_one
typed_center Complex.abs_exp_eq_iff_re_eq
typed_center Complex.cpow_def_of_ne_zero
typed_center Nat.sq_add_sq_modEq
typed_center Nat.sq_add_sq_zmodEq
typed_center ZMod.mod_four_ne_three_of_sq_eq_neg_one
typed_center ZMod.exists_sq_eq_neg_one_iff
typed_center GaussianInt.mod_four_eq_three_of_nat_prime_of_prime
typed_center GaussianInt.prime_of_nat_prime_of_mod_four_eq_three
typed_center minpoly.natDegree_le
typed_center IntermediateField.adjoin.finiteDimensional
typed_center minpoly.degree_le
typed_center IntermediateField.isAlgebraic_adjoin_simple
typed_center IsGalois.of_card_aut_eq_finrank
typed_center AlgHom.card
typed_center IntermediateField.finrank_fixedField_eq_card
typed_center IsGalois.card_fixingSubgroup_eq_finrank
typed_center hasSum_L_function_mod_four_eval_three
typed_center hasSum_geometric_two
typed_center hasSum_zeta_four
typed_center Real.sin_pi_div_six
typed_center has_pointwise_sum_fourier_series_of_summable
typed_center hasSum_fourier_series_L2
typed_center fourierCoeff.const_mul
typed_center fourierCoeff_toLp
