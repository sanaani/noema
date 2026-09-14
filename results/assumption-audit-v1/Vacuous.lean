import Lean

-- Exact assumptions of the selected lean_workbook_plus_5257 formal statement.
-- This is a diagnostic proof of inconsistency, not a replacement source proof.
theorem noema_selected_assumptions_inconsistent
    (r₁ r₂ r₃ : Nat) (h₁ : 20 ≤ r₁) (h₂ : 20 ≤ r₂)
    (h₃ : 20 ≤ r₃) (h₄ : r₁ + r₂ + r₃ ≤ 18) : False := by
  omega

#print axioms noema_selected_assumptions_inconsistent
