/-
Emit the source location of each requested declaration, from Lean itself.

  lake env lean --run DeclRanges.lean modules.txt names.txt > ranges.jsonl

`modules.txt` and `names.txt` are newline-separated. Only the listed modules are
imported, so this works against a partial Mathlib build. Writes one JSON object
per line:

  {"name":..., "module":..., "start":[line,col], "end":[line,col]}

Names that are absent from the environment, or that carry no declaration range,
are reported with a "missing" field so failures are explicit rather than silently
dropped.

This is the rigorous alternative to grepping the sources for `theorem <name>`:
ranges come from the environment, so macros, generated declarations and
unconventional syntax are located correctly.
-/
import Lean

open Lean

def escape (s : String) : String := Id.run do
  let mut out := ""
  for c in s.data do
    out := out ++ (match c with
      | '"' => "\\\""
      | '\\' => "\\\\"
      | '\n' => "\\n"
      | c => String.singleton c)
  return out

def readLines (p : System.FilePath) : IO (Array String) := do
  let text ← IO.FS.readFile p
  return text.splitOn "\n" |>.map String.trim |>.filter (!·.isEmpty) |>.toArray

def main (args : List String) : IO Unit := do
  match args with
  | [modsPath, namesPath] =>
    let mods ← readLines modsPath
    let names ← readLines namesPath
    let imports := mods.map fun m => { module := m.toName : Import }
    initSearchPath (← findSysroot)
    let env ← importModules imports {} (trustLevel := 1024)
    for nm in names do
      let name := nm.toName
      if !env.contains name then
        IO.println s!"\{\"name\":\"{escape nm}\",\"missing\":\"unknown\"}"
      else
        let modName :=
          match env.getModuleIdxFor? name with
          | some idx => (env.header.moduleNames[idx.toNat]!).toString
          | none => ""
        match declRangeExt.find? env name with
        | some r =>
          let d := r.range
          IO.println <|
            "{\"name\":\"" ++ escape nm ++ "\",\"module\":\"" ++ escape modName ++
            "\",\"start\":[" ++ toString d.pos.line ++ "," ++ toString d.pos.column ++
            "],\"end\":[" ++ toString d.endPos.line ++ "," ++ toString d.endPos.column ++ "]}"
        | none =>
          IO.println
            s!"\{\"name\":\"{escape nm}\",\"module\":\"{escape modName}\",\"missing\":\"no-range\"}"
  | _ => IO.eprintln "usage: DeclRanges.lean modules.txt names.txt"
