import Mathlib.Data.Real.Sqrt
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

set_option autoImplicit false

-- Diagnostic proofs of False from the source assumptions. They are not
-- replacements for the original source proofs or active theorem samples.
theorem noema_5257 (r₁ r₂ r₃ : ℕ) (h₁ : 20 ≤ r₁) (h₂ : 20 ≤ r₂)
    (h₃ : 20 ≤ r₃) (h₄ : r₁ + r₂ + r₃ ≤ 18) : False := by omega

theorem noema_63727 (x y z k : ℝ) (hx : 0 < x) (hy : 0 < y) (hz : 0 < z)
    (hk1 : k ≥ (Real.sqrt 5 - 1) / 4)
    (hk2 : k ≤ -3 / 4 + Real.sqrt 5 / 4) : False := by linarith

theorem noema_product_squares (a b c : ℝ) (ha : 0 < a) (hb : 0 < b)
    (hc : 0 < c) (habc : a * b * c = 1) (h : a^2 + b^2 + c^2 = 1) : False := by
  have ha1 : a ≤ 1 := by nlinarith [sq_nonneg b, sq_nonneg c]
  have hb1 : b ≤ 1 := by nlinarith [sq_nonneg a, sq_nonneg c]
  have hab : a * b ≤ 1 := by
    nlinarith [mul_nonneg (sub_nonneg.mpr ha1) (le_of_lt hb)]
  have hc1 : 1 ≤ c := by
    nlinarith [mul_nonneg (sub_nonneg.mpr hab) (le_of_lt hc)]
  nlinarith [sq_pos_of_pos ha, sq_nonneg b, sq_nonneg (c - 1)]

theorem noema_44565 (a b c : ℝ) (ha : 0 < a) (hb : 0 < b) (hc : 0 < c)
    (habc : a * b * c = 1) (h : a^2 + b^2 + c^2 = 1) : False :=
  noema_product_squares a b c ha hb hc habc h

theorem noema_19088 (a b c : ℝ) (ha : 0 < a) (hb : 0 < b) (hc : 0 < c)
    (habc : a * b * c = 1) (h : a^2 + b^2 + c^2 = 1) : False :=
  noema_product_squares a b c ha hb hc habc h

theorem noema_68017 (a b c : ℝ) (ha : 0 < a) (hb : 0 < b) (hc : 0 < c)
    (habc : a * b * c = 1) (h : a^2 * b^2 + b^2 * c^2 + c^2 * a^2 = 1) : False := by
  apply noema_product_squares (a*b) (b*c) (c*a)
    (mul_pos ha hb) (mul_pos hb hc) (mul_pos hc ha)
  · calc
      (a*b)*(b*c)*(c*a) = (a*b*c)^2 := by ring
      _ = 1 := by rw [habc]; norm_num
  · simpa only [mul_pow] using h

theorem noema_9657 (a : ℝ) (h : a^3 = a + 1) (h' : a^6 ≤ 4*a) : False := by
  have h6 : a^6 = (a+1)^2 := by nlinarith [sq_nonneg (a^3 - (a+1))]
  have ha : a = 1 := by nlinarith [sq_nonneg (a-1)]
  norm_num [ha] at h

#print axioms noema_5257
#print axioms noema_63727
#print axioms noema_44565
#print axioms noema_19088
#print axioms noema_68017
#print axioms noema_9657
