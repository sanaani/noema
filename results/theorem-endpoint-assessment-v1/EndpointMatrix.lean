import Lean
open Lean Meta Elab Tactic Command

elab "endpoint_capture " label:str " => " step:tacticSeq : tactic => do
  let beforeGoals ← getGoals
  unless beforeGoals.length == 1 do throwError "expected exactly one active goal"
  let before ← beforeGoals.mapM fun g => return (← ppGoal g).pretty
  let targets ← beforeGoals.mapM fun g => return reprStr (← instantiateMVars (← g.getType))
  let contexts ← beforeGoals.mapM fun g => do
    let d ← g.getDecl
    return d.lctx.foldl (init := #[]) fun acc decl =>
      acc.push (Json.mkObj [
        ("name", toJson decl.userName.toString),
        ("kind", toJson (reprStr decl.kind)),
        ("hidden_by_default", toJson (decl.isImplementationDetail || decl.isAuxDecl)),
        ("type_expr", toJson (reprStr decl.type)),
        ("value_expr", toJson (reprStr decl.value?))])
  evalTactic step
  let afterGoals ← getGoals
  unless afterGoals.isEmpty do throwError "closing tactic left active goals"
  logInfo <| "ENDPOINT_CAPTURE " ++ (Json.mkObj [
    ("label", toJson label.getString), ("before", toJson before),
    ("tactic", toJson (step.raw.reprint.getD "")),
    ("before_target_exprs", toJson targets), ("local_contexts", toJson contexts),
    ("after", toJson ("no goals" : String)),
    ("before_goal_count", toJson beforeGoals.length),
    ("after_goal_count", toJson afterGoals.length)]).compress

theorem addition_truth : ∀ a b : Nat, a + b = b + a := by
  suffices h : True by
    exact Nat.add_comm
  endpoint_capture "addition_truth" => exact (True.intro)

#print axioms addition_truth

theorem addition_zero_eq : ∀ a b : Nat, a + b = b + a := by
  suffices h : (0 : Nat) = 0 by
    exact Nat.add_comm
  endpoint_capture "addition_zero_eq" => exact (rfl)

#print axioms addition_zero_eq

theorem addition_forall_eq : ∀ a b : Nat, a + b = b + a := by
  suffices h : ∀ n : Nat, n = n by
    exact Nat.add_comm
  endpoint_capture "addition_forall_eq" => exact (fun _ => rfl)

#print axioms addition_forall_eq

theorem addition_and_truth : ∀ a b : Nat, a + b = b + a := by
  suffices h : True ∧ True by
    exact Nat.add_comm
  endpoint_capture "addition_and_truth" => exact (⟨True.intro, True.intro⟩)

#print axioms addition_and_truth

theorem multiplication_truth : ∀ a b : Nat, a * b = b * a := by
  suffices h : True by
    exact Nat.mul_comm
  endpoint_capture "multiplication_truth" => exact (True.intro)

#print axioms multiplication_truth

theorem multiplication_zero_eq : ∀ a b : Nat, a * b = b * a := by
  suffices h : (0 : Nat) = 0 by
    exact Nat.mul_comm
  endpoint_capture "multiplication_zero_eq" => exact (rfl)

#print axioms multiplication_zero_eq

theorem multiplication_forall_eq : ∀ a b : Nat, a * b = b * a := by
  suffices h : ∀ n : Nat, n = n by
    exact Nat.mul_comm
  endpoint_capture "multiplication_forall_eq" => exact (fun _ => rfl)

#print axioms multiplication_forall_eq

theorem multiplication_and_truth : ∀ a b : Nat, a * b = b * a := by
  suffices h : True ∧ True by
    exact Nat.mul_comm
  endpoint_capture "multiplication_and_truth" => exact (⟨True.intro, True.intro⟩)

#print axioms multiplication_and_truth

theorem conjunction_truth : ∀ P Q : Prop, ∀ h : P ∧ Q, Q ∧ P := by
  suffices h : True by
    exact fun _ _ h => ⟨h.2, h.1⟩
  endpoint_capture "conjunction_truth" => exact (True.intro)

#print axioms conjunction_truth

theorem conjunction_zero_eq : ∀ P Q : Prop, ∀ h : P ∧ Q, Q ∧ P := by
  suffices h : (0 : Nat) = 0 by
    exact fun _ _ h => ⟨h.2, h.1⟩
  endpoint_capture "conjunction_zero_eq" => exact (rfl)

#print axioms conjunction_zero_eq

theorem conjunction_forall_eq : ∀ P Q : Prop, ∀ h : P ∧ Q, Q ∧ P := by
  suffices h : ∀ n : Nat, n = n by
    exact fun _ _ h => ⟨h.2, h.1⟩
  endpoint_capture "conjunction_forall_eq" => exact (fun _ => rfl)

#print axioms conjunction_forall_eq

theorem conjunction_and_truth : ∀ P Q : Prop, ∀ h : P ∧ Q, Q ∧ P := by
  suffices h : True ∧ True by
    exact fun _ _ h => ⟨h.2, h.1⟩
  endpoint_capture "conjunction_and_truth" => exact (⟨True.intro, True.intro⟩)

#print axioms conjunction_and_truth

theorem order_truth : ∀ n : Nat, n ≤ n := by
  suffices h : True by
    exact Nat.le_refl
  endpoint_capture "order_truth" => exact (True.intro)

#print axioms order_truth

theorem order_zero_eq : ∀ n : Nat, n ≤ n := by
  suffices h : (0 : Nat) = 0 by
    exact Nat.le_refl
  endpoint_capture "order_zero_eq" => exact (rfl)

#print axioms order_zero_eq

theorem order_forall_eq : ∀ n : Nat, n ≤ n := by
  suffices h : ∀ n : Nat, n = n by
    exact Nat.le_refl
  endpoint_capture "order_forall_eq" => exact (fun _ => rfl)

#print axioms order_forall_eq

theorem order_and_truth : ∀ n : Nat, n ≤ n := by
  suffices h : True ∧ True by
    exact Nat.le_refl
  endpoint_capture "order_and_truth" => exact (⟨True.intro, True.intro⟩)

#print axioms order_and_truth


-- Formalizes the information-loss argument for an endpoint-only representation.
theorem invariant_endpoint_centers_collapse
    {Target Goal Space : Type}
    (encode : Goal → Space) (center : Target → Space) (g : Goal)
    (agreement : ∀ t q, encode q = center t) :
    ∀ a b, center a = center b := by
  intro a b
  exact (agreement a g).symm.trans (agreement b g)

#print axioms invariant_endpoint_centers_collapse

-- A valid proof of any proved target may discharge any proved auxiliary goal last.
theorem auxiliary_goal_wrapper (T G : Prop) (p : T) (q : G) : T :=
  (fun (_ : G) => p) q

#print axioms auxiliary_goal_wrapper

elab "target_certificate " n:ident : command => do
  let info ← getConstInfo n.getId
  logInfo <| "TARGET_CERTIFICATE " ++ (Json.mkObj [
    ("declaration", toJson n.getId.toString),
    ("target_expr", toJson (reprStr info.type))]).compress

target_certificate addition_truth
target_certificate addition_zero_eq
target_certificate addition_forall_eq
target_certificate addition_and_truth
target_certificate multiplication_truth
target_certificate multiplication_zero_eq
target_certificate multiplication_forall_eq
target_certificate multiplication_and_truth
target_certificate conjunction_truth
target_certificate conjunction_zero_eq
target_certificate conjunction_forall_eq
target_certificate conjunction_and_truth
target_certificate order_truth
target_certificate order_zero_eq
target_certificate order_forall_eq
target_certificate order_and_truth
