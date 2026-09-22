import Mathlib

open scoped EuclideanGeometry Real RealInnerProductSpace

namespace NoemaBridge

open FiniteDimensional

variable {V : Type*} [NormedAddCommGroup V] [InnerProductSpace ℝ V]
variable [Fact (finrank ℝ V = 2)] (o : Orientation ℝ V (Fin 2))

/-- Machine-proposed bridge: the right-triangle oriented angle that equals
`arctan r⁻¹` can never be an odd multiple of `π / 2` (as a circle angle),
because `arctan` never attains such values (`Real.arctan_ne_mul_pi_div_two`).
Composes `Orientation.oangle_add_left_smul_rotation_pi_div_two` with the
arctan range fact across two distant library areas. -/
theorem oangle_add_left_smul_rotation_ne_odd_mul_pi_div_two {x : V} (hx : x ≠ 0)
    (r : ℝ) (k : ℤ) :
    o.oangle (x + r • o.rotation (π / 2 : ℝ) x) (r • o.rotation (π / 2 : ℝ) x)
      ≠ ((2 * k + 1) * π / 2 : ℝ) := by
  rw [o.oangle_add_left_smul_rotation_pi_div_two hx r]
  intro h
  obtain ⟨n, hn⟩ := Real.Angle.angle_eq_iff_two_pi_dvd_sub.mp h
  exact Real.arctan_ne_mul_pi_div_two (k + 2 * n) (by push_cast; linear_combination hn)

/-- Subtracting-vectors variant, via
`Orientation.oangle_sub_right_smul_rotation_pi_div_two`. -/
theorem oangle_sub_right_smul_rotation_ne_odd_mul_pi_div_two {x : V} (hx : x ≠ 0)
    (r : ℝ) (k : ℤ) :
    o.oangle (r • o.rotation (π / 2 : ℝ) x) (r • o.rotation (π / 2 : ℝ) x - x)
      ≠ ((2 * k + 1) * π / 2 : ℝ) := by
  rw [o.oangle_sub_right_smul_rotation_pi_div_two hx r]
  intro h
  obtain ⟨n, hn⟩ := Real.Angle.angle_eq_iff_two_pi_dvd_sub.mp h
  exact Real.arctan_ne_mul_pi_div_two (k + 2 * n) (by push_cast; linear_combination hn)

#print axioms oangle_add_left_smul_rotation_ne_odd_mul_pi_div_two
#print axioms oangle_sub_right_smul_rotation_ne_odd_mul_pi_div_two

end NoemaBridge
