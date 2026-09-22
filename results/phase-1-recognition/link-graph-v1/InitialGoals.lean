/-
Print each requested declaration's initial goal, from the environment.

  lake env lean --run InitialGoals.lean modules.txt names.txt > goals.jsonl

Emits one JSON object per line: {"name":..., "goal":"⊢ <pretty-printed type>"}.

Why: term-mode proofs (`theorem foo : P := le_antisymm ..`) run no tactics, so a
tactic replay captures zero states and the theorem ends up with no object at all.
Its initial goal still exists — it is the statement — and that is exactly the kind
of text the ReProver retriever encodes. Taking it from the environment rather than
from a `sorry` rewrite means the proof source is never altered.

Any state built from this output must be marked synthetic: it is the initial goal
only, not an observed proof state.
-/
import Lean

open Lean Meta PrettyPrinter

def escape (s : String) : String := Id.run do
  let mut out := ""
  for c in s.data do
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
  return text.splitOn "\n" |>.map String.trim |>.filter (!·.isEmpty) |>.toArray

def runMeta {α : Type} (env : Environment) (x : MetaM α) : IO α := do
  let (a, _) ← (x.run' : CoreM α).toIO { fileName := "<initial-goals>", fileMap := default }
                  { env := env }
  return a

def main (args : List String) : IO Unit := do
  match args with
  | [modsPath, namesPath] =>
    let mods ← readLines modsPath
    let names ← readLines namesPath
    initSearchPath (← findSysroot)
    let env ← importModules (mods.map fun m => { module := m.toName : Import }) {}
                (trustLevel := 1024)
    for nm in names do
      let name := nm.toName
      match env.find? name with
      | none => IO.println s!"\{\"name\":\"{escape nm}\",\"missing\":\"unknown\"}"
      | some info =>
        try
          -- Render as a goal *in context*: binders become hypothesis lines, so the
          -- text matches the shape of an observed proof state rather than a closed ∀.
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
          IO.println <|
            "{\"name\":\"" ++ escape nm ++ "\",\"goal\":\"" ++ escape txt ++ "\"}"
        catch e =>
          IO.println <|
            "{\"name\":\"" ++ escape nm ++ "\",\"missing\":\"pp-failed\",\"error\":\"" ++
            escape (toString e) ++ "\"}"
  | _ => IO.eprintln "usage: InitialGoals.lean modules.txt names.txt"
