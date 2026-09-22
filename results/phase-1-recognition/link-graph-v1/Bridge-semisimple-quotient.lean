import Mathlib.LinearAlgebra.Semisimple

/-!
# Bridge lemma for triple (A, B, C)

A : `RingHom.isSemisimpleRing_of_surjective`      (RingTheory/SimpleModule.lean)
B : `Module.isTorsionBySet_span_singleton_iff`    (Algebra/Module/Torsion.lean)
C : `Module.End.isSemisimple_of_squarefree_aeval_eq_zero`  (LinearAlgebra/Semisimple.lean)

A and B share no rare citation. The bridge scan proposed C, whose proof visits
both neighbourhoods. Reading C's proof shows the link is a statement it proves
inline as an anonymous `have` and never names:

    K[X] ⧸ (p) is a semisimple ring, for p squarefree.

That is the ring-semisimplicity fact A is about, applied to the torsion quotient
B is about. Below it is extracted, named, and proved.
-/

open Polynomial

variable {K : Type*} [Field K]

/-- For a squarefree polynomial `p`, the quotient `K[X] ⧸ (p)` is a semisimple ring.

This is the statement hidden inside the proof of
`Module.End.isSemisimple_of_squarefree_aeval_eq_zero`. -/
theorem isSemisimpleRing_quotient_span_singleton_of_squarefree
    {p : K[X]} (hp : Squarefree p) :
    IsSemisimpleRing (K[X] ⧸ Ideal.span {p}) := by
  have : IsReduced (K[X] ⧸ Ideal.span {p}) :=
    (Ideal.isRadical_iff_quotient_reduced _).mp
      (isRadical_iff_span_singleton.mp hp.isRadical)
  have : FiniteDimensional K (K[X] ⧸ Ideal.span {p}) :=
    (AdjoinRoot.powerBasis hp.ne_zero).finite
  have : IsArtinianRing (K[X] ⧸ Ideal.span {p}) := .of_finite K _
  exact IsArtinianRing.isSemisimpleRing_of_isReduced _

/-- Sanity check: the extracted lemma really does discharge the step C needed,
so C can be rebuilt on top of the named bridge. -/
example {M : Type*} [AddCommGroup M] [Module K M] {f : Module.End K M} {p : K[X]}
    (hp : Squarefree p) (hpf : aeval f p = 0) : f.IsSemisimple := by
  rw [← RingHom.mem_ker, ← Module.AEval.annihilator_eq_ker_aeval (M := M),
      Module.mem_annihilator, ← Module.IsTorsionBy,
      ← Module.isTorsionBySet_singleton_iff,
      Module.isTorsionBySet_iff_is_torsion_by_span] at hpf
  letI : Module (K[X] ⧸ Ideal.span {p}) (Module.AEval' f) := Module.IsTorsionBySet.module hpf
  haveI := isSemisimpleRing_quotient_span_singleton_of_squarefree hp
  let e : Module.AEval' f →ₛₗ[Ideal.Quotient.mk (Ideal.span {p})] Module.AEval' f :=
    { AddMonoidHom.id _ with map_smul' := fun _ _ ↦ rfl }
  exact (e.isSemisimpleModule_iff_of_bijective Function.bijective_id).mpr inferInstance

#print axioms isSemisimpleRing_quotient_span_singleton_of_squarefree
