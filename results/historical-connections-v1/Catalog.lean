import Mathlib.NumberTheory.SumTwoSquares
import Mathlib.NumberTheory.ZetaValues
import Mathlib.FieldTheory.Galois
import Mathlib.Data.Complex.Exponential
import Mathlib.GroupTheory.Perm.Cycle.Type
import Lean

open Lean Meta Elab Command

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


center_catalog
