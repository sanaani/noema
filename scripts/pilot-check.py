#!/usr/bin/env python3
"""pilot-check.py -- check one phase 6 pilot candidate on the Lean worker.

Fixed in results/phase-6-conjecture-placement/README.md, part 4. A candidate
is a hit only if

    1. it compiles with no `sorry` and no axioms beyond propext,
       Classical.choice and Quot.sound;
    2. its proof term cites both endpoints (the constants of its value, no
       transitive closure -- Deps2026.lean's rule);
    3. `exact?` does not close its statement within 60 s (plus import time).

The candidate is a JSON file: {"opens": [..], "statement": "theorem
noema_pilot_candidate ...", "proof": "..."}; the file is `statement :=
proof`. Every check is appended to pilot/checks.jsonl and printed.

    scripts/pilot-check.py --run <worker run> --pair 7 --attempt 2 cand.json
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import re
import subprocess
import tarfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "results/phase-6-conjecture-placement/pilot"
OUTS = ROOT / "outputs/phase-6-conjecture-placement"
REGION = "us-east-2"
NAME = "noema_pilot_candidate"
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
FORBIDDEN = re.compile(
    r"\b(sorry|admit|axiom|native_decide|implemented_by|extern|unsafe|import|"
    r"set_option\s+debug|decreasing_by\s+sorry)\b|#exit|@\[csimp\]"
)
OPEN_LINE = re.compile(r"^open(\s+scoped)?(\s+[\w.']+)+$")


def reject(msg: str) -> dict:
    return {"valid": False, "reason": msg, "hit": False}


def files_for(c: dict, a: str, b: str) -> dict[str, str]:
    opens = "\n".join(c.get("opens", []))
    # Elab.async off: with parallel elaboration a theorem's value may not be in
    # the environment yet when the #eval below reads it.
    main = f"""import Mathlib
set_option Elab.async false
{opens}

{c["statement"]} :=
{c["proof"]}

open Lean Meta in
#eval show MetaM Unit from do
  let some (.thmInfo t) := (← getEnv).find? `{NAME} | IO.println "NOEMA-DEPS missing"
  let cs := t.value.getUsedConstants
  IO.println s!"NOEMA-DEPS a={{cs.contains "{a}".toName}} b={{cs.contains "{b}".toName}}"

#print axioms {NAME}
"""
    exact = f"""import Mathlib
{opens}

{c["statement"]} := by exact?
"""
    return {"main.lean": main, "exact.lean": exact}


def ssm_run(instance: str, tag: str, files: dict[str, str]) -> str:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    blob = base64.b64encode(buf.getvalue()).decode()
    d = f"/opt/checks/{tag}"
    cmd = [f"rm -rf {d} && mkdir -p {d}", f"echo {blob} | base64 -d | tar xz -C {d}",
           f"/opt/check.sh {d}"]  # fmt: skip
    out = subprocess.run(
        ["aws", "ssm", "send-command", "--region", REGION, "--instance-ids", instance,
         "--document-name", "AWS-RunShellScript", "--timeout-seconds", "900",
         "--parameters", json.dumps({"commands": cmd, "executionTimeout": ["900"]}),
         "--query", "Command.CommandId", "--output", "text"],
        check=True, capture_output=True, text=True,
    )  # fmt: skip
    cid = out.stdout.strip()
    while True:
        time.sleep(5)
        r = subprocess.run(
            ["aws", "ssm", "get-command-invocation", "--region", REGION,
             "--command-id", cid, "--instance-id", instance, "--output", "json"],
            capture_output=True, text=True,
        )  # fmt: skip
        if r.returncode != 0:
            continue
        inv = json.loads(r.stdout)
        if inv["Status"] in ("Success", "Failed", "TimedOut", "Cancelled"):
            return inv["StandardOutputContent"]


def parse(stdout: str) -> dict[str, tuple[int, str]]:
    out = {}
    for part in stdout.split("=== FILE ")[1:]:
        head, _, body = part.partition("\n")
        name, _, rc = head.partition(" RC ")
        out[name.strip()] = (int(rc.strip() or -1), body)
    return out


def has_error(rc: int, body: str) -> bool:
    return rc != 0 or bool(re.search(r"^\S+:\d+:\d+: error", body, re.M))


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
    if not args.smoke and used >= 12:
        print(json.dumps({"valid": False, "reason": "budget spent: 12 checks for this pair"}))
        return 1
    c = json.loads(args.candidate.read_text())
    text = " ".join([*c.get("opens", []), c.get("statement", ""), c.get("proof", "")])
    if not c.get("statement", "").lstrip().startswith(f"theorem {NAME}"):
        res = reject(f"statement must start with `theorem {NAME}`")
    elif FORBIDDEN.search(text):
        res = reject(f"forbidden token: {FORBIDDEN.search(text).group(0)}")
    elif any(not OPEN_LINE.match(o.strip()) for o in c.get("opens", [])):
        res = reject("opens must be plain `open ...` lines")
    else:
        instance = (OUTS / args.run / "instance-id").read_text().strip()
        tag = f"p{args.pair}-a{args.attempt}-{uuid.uuid4().hex[:8]}"
        got = parse(ssm_run(instance, tag, files_for(c, pair["a"], pair["b"])))
        rc, body = got.get("main.lean", (-1, "no output"))
        compiled = not has_error(rc, body)
        m = re.search(r"NOEMA-DEPS a=(\w+) b=(\w+)", body)
        cites = bool(m) and m.group(1) == "true" and m.group(2) == "true"
        ax = re.search(r"depends on axioms: \[([^\]]*)\]", body)
        axioms = {x.strip() for x in ax.group(1).split(",")} if ax else set()
        clean = compiled and axioms <= ALLOWED_AXIOMS and "sorryAx" not in body
        exact_closed = None
        if compiled:
            erc, ebody = got.get("exact.lean", (-1, "no output"))
            exact_closed = not has_error(erc, ebody)
        res = {
            "valid": True, "compiled": compiled, "axioms_ok": clean,
            "axioms": sorted(axioms), "cites_a": bool(m) and m.group(1) == "true",
            "cites_b": bool(m) and m.group(2) == "true", "exact_closes": exact_closed,
            "hit": bool(clean and cites and exact_closed is False),
            "lean_output": body[-4000:],
        }  # fmt: skip
    record = {"pair": args.pair, "attempt": args.attempt, "time": time.time(),
              "candidate": c, "result": res}  # fmt: skip
    if not args.smoke:
        with open(PILOT / "checks.jsonl", "a") as f:
            f.write(json.dumps(record) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
