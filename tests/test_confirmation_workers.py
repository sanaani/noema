import gzip
import hashlib
import json
import runpy
import sys
from pathlib import Path

from noema.corpus import digest
from noema.transfer_confirmation import PROTOCOL, confirmation_hashes


def test_disjoint_proof_workers_preserve_global_indices_and_resume(tmp_path, monkeypatch):
    plan = {"blocks": [{"id": i} for i in range(4)]}
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    run = tmp_path / "run"
    (run / "lean").mkdir(parents=True)
    freeze = {
        "plan_sha256": digest(plan_path.read_text()),
        "source_hashes": confirmation_hashes(),
        "protocol_sha256": digest(PROTOCOL.read_text()),
    }
    (run / "run-freeze.json").write_text(json.dumps(freeze))
    calls = []

    def fixture(small_plan, stage):
        block = small_plan["blocks"][0]
        calls.append(block["id"])
        target = stage / "block-0000"
        target.mkdir(parents=True)
        raw = gzip.compress(json.dumps([{"block": 0, "evidence": block["id"]}]).encode())
        (target / "lean-audit.json.gz").write_bytes(raw)
        (target / "summary.json").write_text(
            json.dumps(
                {
                    "block_sha256": digest(json.dumps(block, sort_keys=True)),
                    "audit_sha256": hashlib.sha256(raw).hexdigest(),
                    "verified_proofs": 12,
                    "matched_intermediate_states": 60,
                }
            )
        )

    monkeypatch.setattr("noema.transfer_confirmation.audit_all_proofs", fixture)
    script = Path(__file__).resolve().parents[1] / "scripts/confirmation-acquisition-worker.py"
    for shard in (0, 1, 0, 1):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                str(script),
                "proofs",
                "--plan",
                str(plan_path),
                "--run",
                str(run),
                "--shard",
                str(shard),
            ],
        )
        runpy.run_path(str(script), run_name="__main__")
    assert calls == [0, 2, 1, 3]
    for index in range(4):
        target = run / "lean" / f"block-{index:04d}"
        raw = (target / "lean-audit.json.gz").read_bytes()
        assert json.loads(gzip.decompress(raw)) == [{"block": index, "evidence": index}]
        summary = json.loads((target / "summary.json").read_text())
        assert summary["audit_sha256"] == hashlib.sha256(raw).hexdigest()
