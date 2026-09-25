/-
Print each requested declaration's statement, from the 2026 environment.

  lake env lean --run Statements2026.lean modules.txt names.txt out.jsonl

Phase 1's `InitialGoals.lean` ported to Lean `v4.35.0-rc2` / Mathlib `09712d48`.
The rendering is unchanged: binders become hypothesis lines and the body is
printed after `⊢`, so a statement has the shape of a proof state, which is
the text the phase 4 encoder was trained on. One JSON object per line:
{"name":..., "goal":"..."} or {"name":..., "missing":...}.

Two things differ, neither of which changes what is printed:

* `importModules (loadExts := true)` after `enableInitializersExecution`, so
  delaborators and notation registered by imported modules are live; without
  it the printer falls back to raw applications.
* Output goes to a file handle named on the command line, not stdout, for the
  reason `Deps2026.lean` gives.
-/
import Lean

open Lean Meta PrettyPrinter

def escape (s : String) : String := Id.run do
  let mut out := ""
  for c in s.toList do
    out := out ++ (match c with
      | '"' => "\\\""
      | '\\' => "\\\\"
      | '\n' => "\\n"
      | '\r' => ""
      | '\t' => "  "
      | c => String.singleton c)
  return out

def readLines (p : System.FilePath) : IO (Array String) := do
  let text ← IO.FS.readFile p
  -- Inputs are written by our own scripts: one name per line, no padding.
  return text.splitOn "\n" |>.filter (· ≠ "") |>.toArray

def runMeta {α : Type} (env : Environment) (x : MetaM α) : IO α := do
  let (a, _) ← (x.run' : CoreM α).toIO
    { fileName := "<statements-2026>", fileMap := default, maxHeartbeats := 0 }
    { env := env }
  return a

unsafe def main (args : List String) : IO Unit := do
  match args with
  | [modsPath, namesPath, outPath] =>
    let mods ← readLines modsPath
    let names ← readLines namesPath
    initSearchPath (← findSysroot)
    enableInitializersExecution
    let env ← importModules (mods.map fun m => { module := m.toName : Import }) {}
                (trustLevel := 1024) (loadExts := true)
    let h ← IO.FS.Handle.mk outPath IO.FS.Mode.write
    let mut done := 0
    for nm in names do
      let name := nm.toName
      match env.find? name with
      | none => h.putStrLn s!"\{\"name\":\"{escape nm}\",\"missing\":\"unknown\"}"
      | some info =>
        try
          let txt ← runMeta env <| forallTelescope info.type fun xs body => do
            let mut lines : Array String := #[]
            for x in xs do
              let ld ← x.fvarId!.getDecl
              let t ← PrettyPrinter.ppExpr ld.type
              let base := ld.userName.eraseMacroScopes
              let disp := if ld.userName.hasMacroScopes then base.toString ++ "✝" else base.toString
              lines := lines.push s!"{disp} : {t.pretty}"
            let b ← PrettyPrinter.ppExpr body
            return String.intercalate "\n" (lines.toList ++ ["⊢ " ++ b.pretty])
          h.putStrLn <| "{\"name\":\"" ++ escape nm ++ "\",\"goal\":\"" ++ escape txt ++ "\"}"
        catch e =>
          h.putStrLn <| "{\"name\":\"" ++ escape nm ++ "\",\"missing\":\"pp-failed\",\"error\":\"" ++
            escape (toString e) ++ "\"}"
      done := done + 1
      if done % 1000 == 0 then
        IO.eprintln s!"PROGRESS {done}/{names.size}"
        h.flush
    h.flush
    IO.eprintln s!"DONE {done}"
  | _ => IO.eprintln "usage: Statements2026.lean modules.txt names.txt out.jsonl"
