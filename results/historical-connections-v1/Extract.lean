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

center_catalog
