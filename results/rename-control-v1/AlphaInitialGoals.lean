/-
Initial goals for term-mode theorems, in both arms.

  lake env lean --run AlphaInitialGoals.lean modules.txt names.txt > goals.jsonl

Emits {"name":..., "goal":..., "goalAlpha":..., "alphaCertified":..., ...} per
line. The `goal` field is produced by the unchanged code path of
`results/link-graph-v1/InitialGoals.lean` and must reproduce
`target-initial-goals.jsonl` byte for byte; `goalAlpha` is the same goal with
every binder and hypothesis renamed positionally.

425 of the 1,797 theorems in the state-bridge corpus are term-mode and carry a
synthetic initial goal instead of observed states. Leaving those unrenamed
would hand a quarter of the corpus identical centroids in both arms, diluting
the control in the one direction that matters — toward preserving signal.

The hypothesis/binder naming matches `REPL/Alpha.lean` exactly (`x{index}` for
local declarations, `v{depth}` for bound variables), because both kinds of
state live in the same corpus and are compared to each other.
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

/-- Rewrite binder names and nothing else. Mirrors `REPL.Alpha.rename`; named to avoid `Lean.Meta.rename`. -/
partial def alphaRename (e : Expr) (depth : Nat := 0) : Expr :=
  let n := Name.mkSimple s!"v{depth}"
  match e with
  | .forallE _ a b bi => .forallE n (alphaRename a depth) (alphaRename b (depth + 1)) bi
  | .lam _ a b bi => .lam n (alphaRename a depth) (alphaRename b (depth + 1)) bi
  | .letE _ t v b nd =>
    .letE n (alphaRename t depth) (alphaRename v depth) (alphaRename b (depth + 1)) nd
  | .app f a => .app (alphaRename f depth) (alphaRename a depth)
  | .mdata m b => .mdata m (alphaRename b depth)
  | .proj t i b => .proj t i (alphaRename b depth)
  | _ => e

/-- Mirrors `REPL.Alpha.eraseBinderNames`. -/
partial def eraseBinderNames : Expr → Expr
  | .forallE _ a b bi => .forallE .anonymous (eraseBinderNames a) (eraseBinderNames b) bi
  | .lam _ a b bi => .lam .anonymous (eraseBinderNames a) (eraseBinderNames b) bi
  | .letE _ t v b nd =>
    .letE .anonymous (eraseBinderNames t) (eraseBinderNames v) (eraseBinderNames b) nd
  | .app f a => .app (eraseBinderNames f) (eraseBinderNames a)
  | .mdata m b => .mdata m (eraseBinderNames b)
  | .proj t i b => .proj t i (eraseBinderNames b)
  | e => e

/-- Render one telescoped goal: one hypothesis line per binder, then the body.
Unchanged from `InitialGoals.lean` so the original arm stays byte-identical. -/
def renderGoal (xs : Array Expr) (body : Expr) : MetaM String := do
  let mut lines : Array String := #[]
  for x in xs do
    let ld ← x.fvarId!.getDecl
    let t ← PrettyPrinter.ppExpr ld.type
    let base := ld.userName.eraseMacroScopes
    let disp := if ld.userName.hasMacroScopes then base.toString ++ "✝" else base.toString
    lines := lines.push s!"{disp} : {t.pretty}"
  let b ← PrettyPrinter.ppExpr body
  return String.intercalate "\n" (lines.toList ++ ["⊢ " ++ b.pretty])

/-- The renamed arm, refused unless the two obligations agree once binder names
are blanked. A declaration type is always metavariable-free, so `isDefEq` is
also required here; the structural check still runs first and does the work. -/
def renderAlpha (xs : Array Expr) (body : Expr) : MetaM (Option String) := do
  let closed ← mkForallFVars xs body (usedLetOnly := false)
  let mut lctx ← getLCtx
  for x in xs do
    lctx := lctx.modifyLocalDecl x.fvarId! fun d =>
      (d.setUserName (Name.mkSimple s!"x{d.index}")).setType (alphaRename d.type)
  let body' := alphaRename body
  withLCtx lctx (← getLocalInstances) do
    let transformed ← mkForallFVars xs body' (usedLetOnly := false)
    unless eraseBinderNames closed == eraseBinderNames transformed do return none
    unless ← withoutModifyingState (isDefEq closed transformed) do return none
    return some (← renderGoal xs body')

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
          let (txt, alpha) ← runMeta env <| forallTelescope info.type fun xs body => do
            return (← renderGoal xs body, ← renderAlpha xs body)
          IO.println <|
            "{\"name\":\"" ++ escape nm ++ "\",\"goal\":\"" ++ escape txt ++
            "\",\"goalAlpha\":\"" ++ escape (alpha.getD "") ++
            "\",\"alphaCertified\":" ++ (if alpha.isSome then "true" else "false") ++ "}"
        catch e =>
          IO.println <|
            "{\"name\":\"" ++ escape nm ++ "\",\"missing\":\"pp-failed\",\"error\":\"" ++
            escape (toString e) ++ "\"}"
  | _ => IO.eprintln "usage: AlphaInitialGoals.lean modules.txt names.txt"
