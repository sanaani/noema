"""Reproduce the separate Lean 4.9 compatibility and Mathlib capture checks."""

import json
import os
import subprocess
from pathlib import Path

from noema.comparison_encoders import save_json, sha
from noema.paths import result_path
from noema.state_consistency import build_registry, digest

ROOT = Path(__file__).resolve().parents[1]
OUT = result_path("state-consistency-v1/lean49")
LEAN = ROOT / ".tools/lean-4.9.0-linux/bin/lean"
MATH = ROOT / "outputs/eligibility-v1/mathlib"


def main():
    original = (ROOT / "lean/Noema/StateEncoding.lean").read_text()
    source = OUT / "Noema/StateEncoding.lean"
    assert source.read_text() == original.replace(
        "sharedLocals.idxOf? fvar", "sharedLocals.findIdx? (· == fvar)"
    )
    assert sha(LEAN) == "c2059c8da4034467e5f391cfd07b81c4a7b32a7e04ff7e50c7c385993cd77010"
    build = ROOT / "outputs/state-consistency-lean49"
    (build / "Noema").mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(LEAN), "-o", str(build / "Noema/StateEncoding.olean"), str(source)], check=True
    )
    libraries = [
        MATH / ".lake/build/lib",
        *sorted((MATH / ".lake/packages").glob("*/.lake/build/lib")),
    ]
    modules = {}
    for directory in [LEAN.parent.parent / "lib/lean", *libraries]:
        for path in sorted(directory.rglob("*.olean")):
            modules[str(path.relative_to(ROOT))] = sha(path)
    save_json(OUT / "environment-modules.json", modules)
    environment = {
        "lean_version": subprocess.check_output([str(LEAN), "--version"], text=True).strip(),
        "lean_binary_sha256": sha(LEAN),
        "capture_policy_sha256": sha(source),
        "modules_sha256": digest(modules),
        "mathlib_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=MATH, text=True
        ).strip(),
        "scope": "compatibility evidence only; no vectors shared with Lean 4.33 registry",
    }
    summary = {}
    for name, filename, prefix in [
        ("suite", "Suite.lean", "lean"),
        ("mathlib", "MathlibSmoke.lean", "mathlib"),
    ]:
        result = subprocess.run(
            [str(LEAN), str(OUT / filename)],
            env={**os.environ, "LEAN_PATH": ":".join(map(str, [build, *libraries]))},
            capture_output=True,
            text=True,
            timeout=240,
        )
        (OUT / f"{prefix}-output.log").write_text(result.stdout + result.stderr)
        result.check_returncode()
        lines = result.stdout.splitlines()
        allowed = ("STATE ", "PAIR ", "PROOF ", "REJECTED ", "MATHLIB ")
        assert all(not line.strip() or line.startswith(allowed) for line in lines)
        records = [json.loads(line[6:]) for line in lines if line.startswith("STATE ")]
        pairs = [json.loads(line[5:]) for line in lines if line.startswith("PAIR ")]
        registry = build_registry(
            records, pairs, {**environment, "acquisition_source_sha256": sha(OUT / filename)}
        )
        save_json(OUT / f"{name}-registry.json", registry)
        if name == "suite":
            assert pairs == json.loads((OUT.parent / "pairs.json").read_text())
            assert len([line for line in lines if line.startswith("PROOF ")]) == 16
            assert len([line for line in lines if line.startswith("REJECTED ")]) == 3
        else:
            checks = [json.loads(line[8:]) for line in lines if line.startswith("MATHLIB ")]
            assert len(checks) == 5 and len(registry["classes"]) == 5
            assert all(c["rename_equal"] and c["wrapper_equal"] for c in checks)
            save_json(OUT / "mathlib-checks.json", checks)
        summary[name] = {
            "occurrences": len(records),
            "checked_pairs": len(pairs),
            "classes": len(registry["classes"]),
            "registry_id": registry["registry_id"],
        }
    save_json(OUT / "compatibility.json", {"environment": environment, "results": summary})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
