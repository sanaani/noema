#!/usr/bin/env python3
"""phase7-check.py -- check one phase 7 part 3 candidate on the Lean worker.

Fixed in results/phase-7-lemma-selection/README.md, part 3. Phase 6's checker
(scripts/pilot-check.py, imported, not copied) with the hit rule extended. A
candidate is a hit only if

    1. it compiles with no `sorry` and no axioms beyond propext,
       Classical.choice and Quot.sound (`choice`, as Lean prints it under
       `open Classical`, is Classical.choice -- phase 6's fix);
    2. its proof term cites both endpoints (the constants of its value, no
       transitive closure);
    3. `exact?` does not close its statement within 60 s (plus import time);
    4. its conclusion, after every binder is introduced, is not an `And` or an
       `Iff` at the head. Checked on the elaborated type: all binders opened
       with forallTelescopeReducing at reducible transparency, the body put in
       whnfR, and its head constant compared with And and Iff;
    5. `aesop` does not close its statement within 60 s (plus import time).
       Run with maxHeartbeats 0, so the 60 s wall clock is the only limit.

Rule 3's file is byte for byte phase 6's. Rules 3 and 5 are only run on a
candidate that compiles. The worker is scripts/run-lean-check-aws.sh launched
with NOEMA_PHASE=phase-7-lemma-selection (Mathlib 09712d48); its /opt/check.sh
gives files named *exact* and *aesop* the 60 s budget.

The candidate is a JSON file: {"opens": [..], "statement": "theorem
noema_pilot_candidate ...", "proof": "..."}; the file is `statement :=
proof`. Every check is appended to pilot/checks.jsonl and printed. Twelve
checks per pair (three candidates, three repairs each), as phase 6.

    scripts/phase7-check.py --run <worker run> --pair 7 --attempt 2 cand.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "results/phase-7-lemma-selection/pilot"
OUTS = ROOT / "outputs/phase-7-lemma-selection"
BUDGET = 12

_spec = importlib.util.spec_from_file_location("pc", ROOT / "scripts/pilot-check.py")
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)

NAME = pc.NAME
ALLOWED_AXIOMS = pc.ALLOWED_AXIOMS
# Under `open Classical`, `#print axioms` shows Classical.choice as `choice`.
# User axioms cannot exist: the token `axiom` is forbidden.
AXIOM_ALIASES = {"choice": "Classical.choice"}


def files_for(c: dict, a: str, b: str) -> dict[str, str]:
    files = pc.files_for(c, a, b)  # main.lean and exact.lean, phase 6's text
    opens = "\n".join(c.get("opens", []))
    # Rule 4, appended to main.lean after phase 6's dependency #eval.
    files["main.lean"] = files["main.lean"].replace(
        f"#print axioms {NAME}\n",
        f"""open Lean Meta in
#eval show MetaM Unit from do
  let some (.thmInfo t) := (← getEnv).find? `{NAME} | IO.println "NOEMA-HEAD missing"
  let hd ← withReducible <| forallTelescopeReducing t.type fun _ body => do
    let body ← whnfR (← instantiateMVars body)
    return body.getAppFn.constName?
  let conj := hd == some ``And || hd == some ``Iff
  IO.println s!"NOEMA-HEAD conj={{conj}} head={{hd}}"

#print axioms {NAME}
""",
    )
    assert "NOEMA-HEAD" in files["main.lean"]
    files["aesop.lean"] = f"""import Mathlib
{opens}

set_option maxHeartbeats 0 in
{c["statement"]} := by aesop
"""
    return files


def judge(got: dict[str, tuple[int, str]]) -> dict:
    rc, body = got.get("main.lean", (-1, "no output"))
    compiled = not pc.has_error(rc, body)
    m = re.search(r"NOEMA-DEPS a=(\w+) b=(\w+)", body)
    cites_a = bool(m) and m.group(1) == "true"
    cites_b = bool(m) and m.group(2) == "true"
    ax = re.search(r"depends on axioms: \[([^\]]*)\]", body)
    printed = {x.strip() for x in ax.group(1).split(",") if x.strip()} if ax else set()
    axioms = {AXIOM_ALIASES.get(x, x) for x in printed}
    clean = compiled and axioms <= ALLOWED_AXIOMS and "sorryAx" not in body
    h = re.search(r"NOEMA-HEAD conj=(\w+) head=(.*)", body)
    conj = None if not h else h.group(1) == "true"
    exact_closed = aesop_closed = None
    if compiled:
        erc, ebody = got.get("exact.lean", (-1, "no output"))
        exact_closed = not pc.has_error(erc, ebody)
        arc, abody = got.get("aesop.lean", (-1, "no output"))
        aesop_closed = not pc.has_error(arc, abody)
    hit = bool(
        clean and cites_a and cites_b and exact_closed is False
        and conj is False and aesop_closed is False
    )  # fmt: skip
    return {
        "valid": True, "compiled": compiled, "axioms_ok": clean,
        "axioms": sorted(printed), "cites_a": cites_a, "cites_b": cites_b,
        "exact_closes": exact_closed, "conclusion_and_or_iff": conj,
        "conclusion_head": h.group(2).strip() if h else None,
        "aesop_closes": aesop_closed, "hit": hit, "lean_output": body[-4000:],
    }  # fmt: skip


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--pair", type=int, required=True)
    ap.add_argument("--attempt", type=int, required=True)
    ap.add_argument("--smoke", action="store_true", help="test the checker; do not log")
    ap.add_argument("candidate", type=Path)
    args = ap.parse_args()

    pairs = {p["pair"]: p for p in map(json.loads, open(PILOT / "pairs.jsonl"))}
    pair = pairs[args.pair]
    log = PILOT / "checks.jsonl"
    used = 0
    if log.exists():
        used = sum(1 for line in open(log) if json.loads(line)["pair"] == args.pair)
    if not args.smoke and used >= BUDGET:
        print(
            json.dumps({"valid": False, "reason": f"budget spent: {BUDGET} checks for this pair"})
        )
        return 1
    c = json.loads(args.candidate.read_text())
    text = " ".join([*c.get("opens", []), c.get("statement", ""), c.get("proof", "")])
    if not c.get("statement", "").lstrip().startswith(f"theorem {NAME}"):
        res = pc.reject(f"statement must start with `theorem {NAME}`")
    elif pc.FORBIDDEN.search(text):
        res = pc.reject(f"forbidden token: {pc.FORBIDDEN.search(text).group(0)}")
    elif any(not pc.OPEN_LINE.match(o.strip()) for o in c.get("opens", [])):
        res = pc.reject("opens must be plain `open ...` lines")
    else:
        instance = (OUTS / args.run / "instance-id").read_text().strip()
        tag = f"p7-p{args.pair}-a{args.attempt}-{uuid.uuid4().hex[:8]}"
        res = judge(pc.parse(pc.ssm_run(instance, tag, files_for(c, pair["a"], pair["b"]))))
    record = {"pair": args.pair, "attempt": args.attempt, "time": time.time(),
              "candidate": c, "result": res}  # fmt: skip
    if not args.smoke:
        with open(log, "a") as f:
            f.write(json.dumps(record) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
