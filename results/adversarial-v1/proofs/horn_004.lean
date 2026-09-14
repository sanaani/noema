import Lean
set_option linter.unusedVariables false
theorem specimen (p0 p1 p2 p3 p4 p5 p6 p7 : Prop) :
((p0) ∧ (p1) ∧ (p1 → p2) ∧ (p0 → p2) ∧ ((p0 ∧ p1) → p2) ∧ ((p0 ∧ p2) → p3) ∧ (p1 → p3) ∧ ((p0 ∧ p1) → p3) ∧ (p0 → p4) ∧ ((p0 ∧ p2) → p4) ∧ ((p0 ∧ p3) → p4) ∧ (p4 → p5) ∧ (p1 → p5) ∧ ((p0 ∧ p2) → p5) ∧ (p4 → p6) ∧ ((p0 ∧ p1) → p6) ∧ ((p3 ∧ p4) → p6) ∧ (p6 → p7) ∧ ((p0 ∧ p3) → p7) ∧ ((p0 ∧ p4) → p7)) ↔ ((p0) ∧ (p1) ∧ (p2) ∧ (p3) ∧ (p4) ∧ (p5) ∧ (p6) ∧ (p7)) := by
  constructor
  · intro h
    rcases h with ⟨h0, h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11, h12, h13, h14, h15, h16, h17, h18, h19⟩
    exact ⟨h0, ⟨h1, ⟨(h4 ⟨h0, h1⟩), ⟨(h7 ⟨h0, h1⟩), ⟨(h10 ⟨h0, (h7 ⟨h0, h1⟩)⟩), ⟨(h12 h1), ⟨(h16 ⟨(h6 h1), (h9 ⟨h0, (h2 h1)⟩)⟩), (h18 ⟨h0, (h6 h1)⟩)⟩⟩⟩⟩⟩⟩⟩
  · intro h
    rcases h with ⟨v0, v1, v2, v3, v4, v5, v6, v7⟩
    exact ⟨v0, v1, (fun _ => v2), (fun _ => v2), (fun _ => v2), (fun _ => v3), (fun _ => v3), (fun _ => v3), (fun _ => v4), (fun _ => v4), (fun _ => v4), (fun _ => v5), (fun _ => v5), (fun _ => v5), (fun _ => v6), (fun _ => v6), (fun _ => v6), (fun _ => v7), (fun _ => v7), (fun _ => v7)⟩
#print axioms specimen
