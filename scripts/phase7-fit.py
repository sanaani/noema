#!/usr/bin/env python3
"""phase7-fit.py -- phase 7's Lean fit check, driven from the laptop.

Fixed in results/phase-7-lemma-selection/README.md: part 1 ("Lean fit check",
each primary picker's top 1,000 test pairs, Mathlib f0957a7) and part 3
(WINNER+NOVEL keeps a pair only if it passes, Mathlib 09712d48). The check
itself is results/phase-7-lemma-selection/FitCheck.lean: does A's conclusion
unify with one of B's explicit hypotheses, or B's with one of A's, 5 s per
direction. The same Lean file runs under both pins.

Both pins run on the phase 6 Lean worker, scripts/run-lean-check-aws.sh,
which waits for SSM commands. Part 1's worker is the same template at the
2024 pin (a two-variable change to the launcher; the template was already
parameterised by revision and Lean version):

    NOEMA_PHASE=phase-7-lemma-selection NOEMA_LEAN=2024 scripts/run-lean-check-aws.sh launch
    scripts/phase7-fit.py --env 2024 --run noema-leancheck24-<ts> \
        --pairs <gpu out>/fit-candidates-part1.json \
        --out outputs/phase-7-lemma-selection/fit-part1-2024.jsonl

    NOEMA_PHASE=phase-7-lemma-selection scripts/run-lean-check-aws.sh launch
    scripts/phase7-fit.py --env 2026 --run noema-leancheck-<ts> \
        --pairs <gpu out>/part3-winner-novel.json \
        --out outputs/phase-7-lemma-selection/fit-part3-2026.jsonl

Pairs go in batches (one `lean --run`, one Mathlib import each), several
batches at a time. Each batch's results come back gzip+base64 in the SSM
output; a batch whose output would not fit SSM's 24,000-character limit is
split in half and resent. Results are appended as they arrive, and a rerun
skips pairs already in --out, so an interrupted run resumes. The worker's
`lean --version` is checked against --env before anything is recorded.

Input: JSONL of {"a", "b"}; a JSON list of {"a", "b"} objects or [a, b, ...]
lists; or a JSON object of such lists (fit-candidates-part1.json). Pairs are
deduplicated without regard to order.

    --local <lean bin dir> --modules Init    run on this machine instead (tests)
"""

from __future__ import annotations

import argparse
import base64
import gzip
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTS = ROOT / "outputs/phase-7-lemma-selection"
FIT_LEAN = ROOT / "results/phase-7-lemma-selection/FitCheck.lean"
LEAN_OF_ENV = {"2024": "4.9.0", "2026": "4.35.0-rc2"}
SSM_LIMIT = 24_000

_spec = importlib.util.spec_from_file_location("pc", ROOT / "scripts/pilot-check.py")
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)


def load_pairs(path: Path) -> list[tuple[str, str]]:
    text = path.read_text()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(data, dict):
        data = [x for v in data.values() for x in v]
    out, seen = [], set()
    for x in data:
        a, b = (x["a"], x["b"]) if isinstance(x, dict) else (x[0], x[1])
        key = frozenset((a, b))
        if key not in seen:
            seen.add(key)
            out.append((a, b))
    return out


def ssm_exec(instance: str, commands: list[str], timeout: int) -> str:
    """Run shell commands on the worker; return standard output (first 24,000 chars)."""
    out = subprocess.run(
        ["aws", "ssm", "send-command", "--region", pc.REGION, "--instance-ids", instance,
         "--document-name", "AWS-RunShellScript", "--timeout-seconds", "3600",
         "--parameters", json.dumps({"commands": commands, "executionTimeout": [str(timeout)]}),
         "--query", "Command.CommandId", "--output", "text"],
        check=True, capture_output=True, text=True,
    )  # fmt: skip
    cid = out.stdout.strip()
    while True:
        time.sleep(10)
        r = subprocess.run(
            ["aws", "ssm", "get-command-invocation", "--region", pc.REGION,
             "--command-id", cid, "--instance-id", instance, "--output", "json"],
            capture_output=True, text=True,
        )  # fmt: skip
        if r.returncode != 0:
            continue
        inv = json.loads(r.stdout)
        if inv["Status"] in ("Success", "Failed", "TimedOut", "Cancelled"):
            return inv["StandardOutputContent"]


def task_blob(pairs: list[tuple[str, str]]) -> str:
    files = {
        "FitCheck.lean": FIT_LEAN.read_text(),
        "pairs.jsonl": "".join(json.dumps({"a": a, "b": b}) + "\n" for a, b in pairs),
        "modules.txt": "Mathlib\n",
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return base64.b64encode(buf.getvalue()).decode()


def remote_batch(instance: str, pairs, ms: int) -> tuple[str, list[dict] | None, str]:
    """(lean version, results or None if the output was cut off, stderr tail)."""
    d = f"/opt/fit/{uuid.uuid4().hex[:12]}"
    limit = len(pairs) * 2 * (ms // 1000 + 2) + 900
    cmds = [
        f"rm -rf {d} && mkdir -p {d}",
        f"echo {task_blob(pairs)} | base64 -d | tar xz -C {d}",
        "export PATH=$(ls -d /opt/work/lean-*-linux/bin | head -1):$PATH",
        "cd /opt/work/mathlib",
        "echo NOEMA-LEAN $(lean --version | head -1)",
        f"timeout {limit} lake env lean --run {d}/FitCheck.lean {d}/modules.txt "
        f"{d}/pairs.jsonl {d}/out.jsonl {ms} 2> {d}/err.txt; echo NOEMA-RC $?",
        f"tail -c 1500 {d}/err.txt",
        f"echo NOEMA-OUT-BEGIN; gzip -c {d}/out.jsonl | base64 -w0; echo; echo NOEMA-OUT-END",
    ]  # fmt: skip
    return decode(ssm_exec(instance, cmds, limit + 120))


def local_batch(bindir: Path, modules: str, pairs, ms: int) -> tuple[str, list[dict] | None, str]:
    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        (dp / "modules.txt").write_text(modules.replace(",", "\n") + "\n")
        (dp / "pairs.jsonl").write_text(
            "".join(json.dumps({"a": a, "b": b}) + "\n" for a, b in pairs)
        )
        env = {"PATH": f"{bindir}:/usr/bin:/bin"}
        ver = subprocess.run(
            [bindir / "lean", "--version"], capture_output=True, text=True, env=env
        )
        r = subprocess.run(
            [bindir / "lean", "--run", FIT_LEAN, dp / "modules.txt", dp / "pairs.jsonl",
             dp / "out.jsonl", str(ms)], capture_output=True, text=True, env=env,
        )  # fmt: skip
        out = dp / "out.jsonl"
        rows = [json.loads(x) for x in out.read_text().splitlines()] if out.exists() else []
        return ver.stdout.splitlines()[0], rows, r.stderr[-1500:]


def decode(stdout: str) -> tuple[str, list[dict] | None, str]:
    ver = next(
        (ln[len("NOEMA-LEAN ") :] for ln in stdout.splitlines() if ln.startswith("NOEMA-LEAN ")), ""
    )
    if "NOEMA-OUT-END" not in stdout:
        return ver, None, stdout[-1500:]
    blob = stdout.split("NOEMA-OUT-BEGIN", 1)[1].split("NOEMA-OUT-END", 1)[0].strip()
    text = gzip.decompress(base64.b64decode(blob)).decode() if blob else ""
    err = stdout.split("NOEMA-OUT-BEGIN", 1)[0]
    return ver, [json.loads(x) for x in text.splitlines() if x.strip()], err[-1500:]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--env", choices=sorted(LEAN_OF_ENV), required=True)
    ap.add_argument("--run", help="worker run name under outputs/phase-7-lemma-selection/")
    ap.add_argument("--local", type=Path, help="Lean toolchain bin dir: run here, not on AWS")
    ap.add_argument("--modules", default="Mathlib", help="with --local: comma-separated imports")
    ap.add_argument("--pairs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--ms", type=int, default=5000, help="wall-clock budget per direction")
    ap.add_argument("--batch", type=int, default=100)
    ap.add_argument("--parallel", type=int, default=4)
    args = ap.parse_args()
    if (args.run is None) == (args.local is None):
        ap.error("give exactly one of --run and --local")

    pairs = load_pairs(args.pairs)
    done = set()
    if args.out.exists():
        done = {frozenset((r["a"], r["b"])) for r in map(json.loads, open(args.out))}
    todo = [p for p in pairs if frozenset(p) not in done]
    print(f"{len(pairs):,} pairs, {len(pairs) - len(todo):,} already in {args.out}", flush=True)
    if not todo:
        return 0
    if args.run:
        instance = (OUTS / args.run / "instance-id").read_text().strip()

        def run(b):
            return remote_batch(instance, b, args.ms)
    else:

        def run(b):
            return local_batch(args.local, args.modules, b, args.ms)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    want = LEAN_OF_ENV[args.env]
    queue = [todo[k : k + args.batch] for k in range(0, len(todo), args.batch)]
    fits = n = 0
    with ThreadPoolExecutor(args.parallel) as ex, open(args.out, "a") as f:
        while queue:
            wave, queue = queue[: args.parallel], queue[args.parallel :]
            for batch, (ver, rows, err) in zip(wave, ex.map(run, wave), strict=True):
                if want not in ver:
                    sys.exit(f"worker runs `{ver}`, --env {args.env} needs Lean {want}")
                if rows is None or len(rows) != len(batch):
                    if len(batch) == 1:
                        sys.exit(f"pair {batch[0]} produced no result:\n{err}")
                    half = len(batch) // 2
                    print(f"batch of {len(batch)} incomplete; resending in halves", flush=True)
                    queue[:0] = [batch[:half], batch[half:]]
                    continue
                for r in rows:
                    r["env"] = args.env
                    f.write(json.dumps(r) + "\n")
                f.flush()
                n += len(rows)
                fits += sum(bool(r["fit"]) for r in rows)
                errs = sum(r["error"] is not None for r in rows)
                print(f"{n:,}/{len(todo):,} checked, {fits:,} fit, {errs} errors in last batch",
                      flush=True)  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
