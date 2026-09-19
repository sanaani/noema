import Mathlib.Analysis.InnerProductSpace.Basic
import Mathlib.RingTheory.RootsOfUnity.Basic

open Finset ComplexConjugate

variable {V : Type*} [NormedAddCommGroup V] [InnerProductSpace ℂ V]
local notation "⟪" x ", " y "⟫" => @inner ℂ V _ x y

/-- An `n`-th root of unity has `conj r = r⁻¹`. -/
lemma conj_eq_inv_of_pow_eq_one {r : ℂ} {n : ℕ} (hn : n ≠ 0) (h : r ^ n = 1) : conj r = r⁻¹ := by
  have h1 : ‖r‖ = 1 := by
    have : ‖r‖ ^ n = 1 := by rw [← norm_pow, h, norm_one]
    exact (pow_eq_one_iff_of_nonneg (norm_nonneg r) hn).mp this
  have h2 : Complex.normSq r = 1 := by
    rw [Complex.normSq_eq_abs, ← Complex.norm_eq_abs, h1, one_pow]
  rw [Complex.inv_def, h2]; simp

/-- Sum of powers of a nontrivial `n`-th root of unity vanishes. -/
lemma sum_pow_eq_zero {r : ℂ} {n : ℕ} (h : r ^ n = 1) (h1 : r ≠ 1) : ∑ k ∈ range n, r ^ k = 0 := by
  rw [geom_sum_eq h1, h, sub_self, zero_div]

/-- **Bridge lemma: polarization over `μₙ`.** For `n ≥ 3` any primitive `n`-th root of unity
recovers the sesquilinear form `⟪T x, y⟫` from its diagonal. `inner_map_polarization'` is `n = 4, ζ = I`. -/
theorem inner_map_polarization_roots (T : V →ₗ[ℂ] V) (x y : V) {ζ : ℂ} {n : ℕ}
    (hζ : IsPrimitiveRoot ζ n) (hn : 2 < n) :
    ⟪T x, y⟫ = (∑ k ∈ range n, ζ⁻¹ ^ k * ⟪T (x + ζ ^ k • y), x + ζ ^ k • y⟫) / n := by
  have hn0 : n ≠ 0 := by omega
  have hc : ∀ k : ℕ, conj (ζ ^ k) = ζ⁻¹ ^ k := fun k => by
    rw [map_pow, conj_eq_inv_of_pow_eq_one hn0 hζ.pow_eq_one]
  have hz : ζ ≠ 0 := hζ.ne_zero hn0
  -- expand each diagonal term
  have hexp : ∀ k : ℕ, ζ⁻¹ ^ k * ⟪T (x + ζ ^ k • y), x + ζ ^ k • y⟫ =
      ζ⁻¹ ^ k * ⟪T x, x⟫ + ⟪T x, y⟫ + (ζ⁻¹ ^ 2) ^ k * ⟪T y, x⟫ + ζ⁻¹ ^ k * ⟪T y, y⟫ := fun k => by
    simp only [map_add, LinearMap.map_smul, inner_add_left, inner_add_right, inner_smul_left,
      inner_smul_right, hc]
    have : ζ⁻¹ ^ k * ζ ^ k = 1 := by rw [← mul_pow, inv_mul_cancel hz, one_pow]
    rw [← pow_mul, mul_comm 2 k, pow_mul]
    linear_combination (⟪T x, y⟫ + ζ⁻¹ ^ k * ⟪T y, y⟫) * this
  simp_rw [hexp, sum_add_distrib, ← sum_mul, sum_const, card_range, nsmul_eq_mul]
  have s1 : ∑ k ∈ range n, ζ⁻¹ ^ k = 0 := hζ.inv.geom_sum_eq_zero (by omega)
  have s2 : ∑ k ∈ range n, (ζ⁻¹ ^ 2) ^ k = 0 :=
    sum_pow_eq_zero (by rw [← pow_mul, mul_comm, pow_mul, hζ.inv.pow_eq_one, one_pow])
      (hζ.inv.pow_ne_one_of_pos_of_lt two_pos hn)
  rw [s1, s2, zero_mul, zero_mul, zero_mul, zero_add, add_zero, add_zero]
  rw [mul_div_cancel_left₀ _ (Nat.cast_ne_zero.mpr hn0)]

lemma isPrimitiveRoot_I : IsPrimitiveRoot Complex.I 4 := by
  refine IsPrimitiveRoot.mk_of_lt _ (by norm_num) (by
    rw [show (4:ℕ) = 2 * 2 from rfl, pow_mul, Complex.I_sq]; norm_num) ?_
  intro l hl0 hl4 h
  interval_cases l <;> simp [pow_succ, Complex.ext_iff] at h

/-- `inner_map_polarization'` is the `n = 4, ζ = I` instance (after unrolling the sum). -/
example (T : V →ₗ[ℂ] V) (x y : V) :
    ⟪T x, y⟫ = (⟪T (x + y), x + y⟫ - ⟪T (x - y), x - y⟫ -
      Complex.I * ⟪T (x + Complex.I • y), x + Complex.I • y⟫ +
      Complex.I * ⟪T (x - Complex.I • y), x - Complex.I • y⟫) / 4 := by
  have h := inner_map_polarization_roots T x y isPrimitiveRoot_I (by norm_num)
  rw [h]
  simp only [sum_range_succ, sum_range_zero, Complex.inv_I, Nat.cast_ofNat]
  congr 1
  simp only [pow_zero, one_mul, one_smul, zero_add, pow_one, neg_mul, neg_smul, ← sub_eq_add_neg,
    pow_succ, pow_zero, one_mul, Complex.I_mul_I, neg_one_mul, neg_neg, neg_smul, one_smul, mul_neg]
  ring

/-- `n = 2` (ζ = -1): only the *symmetric* part survives. -/
theorem inner_map_polarization_two (T : V →ₗ[ℂ] V) (x y : V) :
    ⟪T (x + y), x + y⟫ - ⟪T (x - y), x - y⟫ = 2 * (⟪T x, y⟫ + ⟪T y, x⟫) := by
  simp only [map_add, map_sub, inner_add_left, inner_add_right, inner_sub_left, inner_sub_right]
  ring

/-- Specialized to `V = ℂ`, `T = id`, `x = 1`, `y = z`, the `n = 2` case *is* `Complex.re`:
this is the only point where A's proof (via `re_eq_add_conj`) meets the bridge. -/
theorem re_eq_polarization (z : ℂ) :
    (z.re : ℂ) = (Complex.normSq (1 + z) - Complex.normSq (1 - z) : ℂ) / 4 := by
  have h := inner_map_polarization_two (V := ℂ) LinearMap.id 1 z
  simp only [LinearMap.id_apply, RCLike.inner_apply, ← Complex.mul_conj', Complex.conj_conj] at h
  rw [Complex.re_eq_add_conj, ← Complex.mul_conj, ← Complex.mul_conj]
  simp only [map_one, one_mul, mul_one, map_add, map_sub] at h ⊢
  linear_combination -h / 4

/-- A's actual step, abstracted: after `jacobiTheta₂'_conj`, sinKernel_def only needs
"conj-fixed ⇒ re equals itself". Direct route (what Mathlib does): 1 line. -/
example (w : ℂ) (hw : conj w = w) : (w.re : ℂ) = w := by
  rw [Complex.re_eq_add_conj, hw, half_add_self]

/-- Bridge route: going through polarization is strictly longer and still needs the same
conj-fixedness fact — the theta content is untouched. -/
example (w : ℂ) (hw : conj w = w) : (w.re : ℂ) = w := by
  rw [re_eq_polarization, ← Complex.mul_conj, ← Complex.mul_conj, map_add, map_sub, map_one, hw]
  ring

#print axioms inner_map_polarization_roots
#print axioms re_eq_polarization
