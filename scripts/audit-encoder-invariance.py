"""Run or reproduce the Lean-certified presentation invariance screen."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import numpy as np

from noema.encoder_invariance import ARMS, analyze
from noema.encoders import SyntaxEncoder
from noema.reprover import ReProverEncoder, byte_ids

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "results/encoder-invariance-v1"


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def read_lean(source, log):
    """Reject partial Lean output, missing proofs, malformed or unpaired arms."""
    checkpoints = re.findall(r'^  observe "([^"]+)"$', source, flags=re.M)
    proof_names = re.findall(r"^audit_fixture (\w+)$", source, flags=re.M)
    if len(checkpoints) != len(set(checkpoints)) or len(proof_names) != 16:
        raise ValueError("invalid fixture inventory")
    states, proofs = [], []
    negative = 0
    for line in log.splitlines():
        if line.startswith("STATE "):
            states.append(json.loads(line[6:]))
        elif line.startswith("PROOF "):
            proofs.append(json.loads(line[6:]))
        elif line == "NEGATIVE_CONTROL rejected":
            negative += 1
        elif line.strip():
            raise ValueError(f"unexpected Lean output: {line}")
    if negative != 1 or sorted(p["name"] for p in proofs) != sorted(proof_names):
        raise ValueError("missing proof/negative-control evidence")
    if any(set(p["axioms"]) - {"propext", "Classical.choice", "Quot.sound"} for p in proofs):
        raise ValueError("unapproved proof axioms")
    lookup = {(r["checkpoint"], r["arm"]): r for r in states}
    expected = {(c, arm) for c in checkpoints for arm in ARMS}
    if set(lookup) != expected or len(lookup) != len(states):
        raise ValueError("missing or duplicate checkpoint/arm")
    for c in checkpoints:
        original = lookup[c, "original"]
        for arm in ARMS:
            row = lookup[c, arm]
            if row["goal_count"] != original["goal_count"]:
                raise ValueError("pending goals changed")
            if len(row["goals"]) != row["goal_count"]:
                raise ValueError("missing goal certificates")
            for a, b in zip(original["goals"], row["goals"], strict=True):
                if not b["defeq"] or a["original_closed_expr"] != b["original_closed_expr"]:
                    raise ValueError("invalid paired defeq evidence")
            if (row["text"] == "no goals") != (row["goal_count"] == 0):
                raise ValueError("empty-state mismatch")
    for proof in proof_names:
        name, p = proof.rsplit("_", 1)
        prefix = f"{name}/{p}/"
        cs = [c for c in checkpoints if c.startswith(prefix)]
        if [int(c.rsplit("/", 1)[1]) for c in cs] != list(range(len(cs))):
            raise ValueError("checkpoint order is not contiguous")
        if any(lookup[c, "original"]["goal_count"] == 0 for c in cs[:-1]):
            raise ValueError("premature terminal checkpoint")
        if lookup[cs[-1], "original"]["goal_count"] != 0:
            raise ValueError("proof did not terminate")
        for arm in ARMS:
            if lookup[f"{name}/{p}/0", arm]["text"] != lookup[f"{name}/0/0", arm]["text"]:
                raise ValueError("proofs do not share the same initial State")
    # Canonical order follows source, independent of elaboration worker scheduling.
    states = [lookup[c, arm] for c in checkpoints for arm in ARMS]
    return states, proofs


def analyze_saved(out):
    states, proofs = read_lean(
        (out / "Fixtures.lean").read_text(), (out / "lean-output.log").read_text()
    )
    records = [r for r in states if r["goal_count"]]
    if json.loads((out / "inputs.json").read_text()) != records:
        raise ValueError("saved inputs differ from verified Lean output")
    x = np.load(out / "vectors.npy", allow_pickle=False)
    repeats = np.load(out / "repeats.npy", allow_pickle=False)
    result = analyze(records, x, repeats)
    result["verified_proofs"] = len(proofs)
    result["archived_empty_occurrences"] = sum(
        r["arm"] == "original" and not r["goal_count"] for r in states
    )
    syntax = SyntaxEncoder().encode([r["text"] for r in records])
    original = [i for i, r in enumerate(records) if r["arm"] == "original"]
    control = analyze(records, syntax, syntax[original])
    return result, control


def run(out):
    if (out / "analysis.json").exists():
        raise ValueError("completed output exists; use verify or a new --output")
    out.mkdir(parents=True, exist_ok=True)
    if out.resolve() != DEFAULT:
        for name in ("Fixtures.lean", "protocol.md"):
            (out / name).write_bytes((DEFAULT / name).read_bytes())
    lean = ROOT / ".tools/lean-4.33.1-linux/bin/lean"
    checked = subprocess.run(
        [str(lean), str(out / "Fixtures.lean")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    (out / "lean-output.log").write_text(checked.stdout + checked.stderr)
    checked.check_returncode()
    states, _ = read_lean((out / "Fixtures.lean").read_text(), checked.stdout + checked.stderr)
    records = [r for r in states if r["goal_count"]]
    # Validate the entire inventory before spending time on any encoding.
    for row in records:
        byte_ids(row["text"])
    write(out / "inputs.json", records)
    encoder = ReProverEncoder(ROOT / ".tools/reprover")
    encoder.manifest.update(
        {
            "lean_version": subprocess.check_output([str(lean), "--version"], text=True).strip(),
            "device": "cpu",
            "numpy": np.__version__,
            "fixture_sha256": sha(out / "Fixtures.lean"),
            "protocol_sha256": sha(out / "protocol.md"),
            "lean_output_sha256": sha(out / "lean-output.log"),
            "script_sha256": sha(Path(__file__)),
            "analysis_code_sha256": sha(ROOT / "src/noema/encoder_invariance.py"),
        }
    )
    write(out / "encoder.json", encoder.manifest)
    vectors = []
    for i, row in enumerate(records):
        vectors.append(encoder.encode([row["text"]])[0])
        if i % 20 == 0:
            print(f"encoded {i + 1}/{len(records)}", flush=True)
    np.save(out / "vectors.npy", vectors, allow_pickle=False)
    originals = [r["text"] for r in records if r["arm"] == "original"]
    np.save(out / "repeats.npy", encoder.encode(originals), allow_pickle=False)
    result, control = analyze_saved(out)
    write(out / "analysis.json", result)
    write(out / "syntax-control.json", control)
    files = [
        "Fixtures.lean",
        "protocol.md",
        "lean-output.log",
        "inputs.json",
        "encoder.json",
        "vectors.npy",
        "repeats.npy",
        "analysis.json",
        "syntax-control.json",
    ]
    (out / "SHA256SUMS").write_text("".join(f"{sha(out / f)}  {f}\n" for f in files))
    print(json.dumps({"status": result["status"], "occurrences": result["occurrences"]}))


def verify(out):
    for line in (out / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split()
        if sha(out / name) != digest:
            raise ValueError(f"checksum mismatch: {name}")
    result, control = analyze_saved(out)
    for name, value in (("analysis.json", result), ("syntax-control.json", control)):
        if json.loads((out / name).read_text()) != value:
            raise ValueError(f"analysis does not reproduce: {name}")
    print("All artifact hashes, Lean row associations and numerical analyses reproduce.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["run", "verify"])
    parser.add_argument("--output", type=Path, default=DEFAULT)
    args = parser.parse_args()
    {"run": run, "verify": verify}[args.stage](args.output)
