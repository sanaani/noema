import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from noema.state_objects import assemble_object, hull_relation, state_id
from noema.state_replay import request, responses, target_axioms, validate_replay_identity


def test_astral_math_symbols_and_large_states_survive_repl_transport():
    source = "theorem test (𝕜 : Type) : True := by trivial\n-- " + "𝓧α" * 4000
    payload = request(source, [[0, len(source.encode())]])
    assert "\\ud835" not in payload  # Older Lean's broken surrogate path is not exercised.
    assert json.loads(payload)["cmd"].encode() == source.encode()
    assert payload.endswith("\n\n")


def test_multiline_and_multiple_repl_responses_with_unicode():
    raw = '{\n  "env": 0\n}\n\n{\n"tactics": [{"goals": "𝕜 : Type\\n⊢ True"}]\n}\n\n'
    decoded = responses(raw)
    assert len(decoded) == 2
    assert decoded[1]["tactics"][0]["goals"] == "𝕜 : Type\n⊢ True"
    with pytest.raises(ValueError):
        responses("[]")


def test_provenance_cannot_override_proof_or_vector_identity():
    theorem = {"id": "T", "proof_ids": ["p"]}
    proofs = [
        {
            "id": "p",
            "theorem_id": "T",
            "trace_complete": True,
            "states": [{"text": "A", "state_id": "forged", "proof_id": "wrong"}],
        }
    ]
    obj = assemble_object(
        theorem, proofs, {state_id("A"): {"encoder_id": "e", "vector": [1.0]}}, "e"
    )
    assert obj["occurrences"][0]["proof_id"] == "p"
    assert obj["state_ids"] == obj["vector_state_ids"] == [state_id("A")]


def test_missing_vectors_keep_an_explicit_matrix_row_mapping():
    theorem = {"id": "T", "proof_ids": ["p"]}
    proofs = [
        {
            "id": "p",
            "theorem_id": "T",
            "trace_complete": True,
            "states": [{"text": "A"}, {"text": "B"}],
        }
    ]
    obj = assemble_object(
        theorem, proofs, {state_id("B"): {"encoder_id": "e", "vector": [1.0]}}, "e"
    )
    assert obj["vector_state_ids"] == [state_id("B")]
    assert obj["missing_embeddings"] == [state_id("A")]
    assert not obj["inventory_complete"]


def test_solver_feasibility_tolerance_does_not_turn_a_gap_into_contact():
    result = hull_relation(np.array([[0.0]]), np.array([[5e-10]]))
    assert result["relation"] != "intersect"


def test_mathlib_observer_retains_all_selected_tactics_and_term_boundaries():
    path = Path(__file__).parents[1] / "scripts/replay-state-object-mathlib.py"
    spec = importlib.util.spec_from_file_location("mathlib_replay", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = "theorem a : True := by\n  trivial\ntheorem b : True := True.intro\n"
    record = {"source": "leandojo-test", "raw_record": {"start": [1, 1], "end": [2, 10]}}

    def node(line, col, endline, endcol, tactic):
        return {
            "pos": {"line": line, "column": col},
            "endPos": {"line": endline, "column": endcol},
            "tactic": tactic,
        }

    nodes = [
        node(1, 20, 2, 9, "by trivial"),
        node(2, 2, 2, 9, "trivial"),
        node(3, 20, 3, 30, module.TERM),
    ]
    kept, _ = module.selected_nodes(record, source, nodes)
    assert len(kept) == 2
    record["raw_record"] = {"start": [3, 1], "end": [3, 31]}
    kept, granularity = module.selected_nodes(record, source, nodes)
    assert len(kept) == 1 and "proof-term" in granularity


def test_axiom_report_must_belong_to_exact_target_and_use_declared_basis():
    unrelated = [{"data": "'Other.target' does not depend on any axioms"}]
    assert not target_axioms(unrelated, "target")["accepted"]
    messages = unrelated + [{"data": "'target' depends on axioms: [propext, Quot.sound]"}]
    assert target_axioms(messages, "target")["accepted"]
    for axiom in ("sorryAx", "unproved_claim"):
        check = target_axioms([{"data": f"'target' depends on axioms: [{axiom}]"}], "target")
        assert not check["accepted"]
        assert check["outside_foundational_basis"] == [axiom]
    assert target_axioms([{"data": "'target' does not depend on any axioms"}], "target")["accepted"]


@pytest.mark.parametrize(
    "field", ["proof_id", "theorem_id", "body_sha256", "environment", "source_artifact"]
)
def test_replay_identity_rejects_changed_checkpoint(field):
    import hashlib

    record = {
        "id": "p",
        "theorem_id": "mathlib:T",
        "body": "proof",
        "source_artifact": {"filename": "f.lean", "sha256": "whole-file-sha"},
    }
    checkpoint = {
        "proof_id": "p",
        "theorem_id": "mathlib:T",
        "body_sha256": hashlib.sha256(b"proof").hexdigest(),
        "environment": "lean-a",
        "source_artifact": record["source_artifact"],
    }
    validate_replay_identity(record, checkpoint, "lean-a")
    checkpoint[field] = "changed"
    with pytest.raises(ValueError, match=field):
        validate_replay_identity(record, checkpoint, "lean-a")


def test_mathlib_worker_validates_existing_checkpoint_before_returning(tmp_path):
    import hashlib
    from types import SimpleNamespace

    from noema.state_replay import VALIDATION_POLICY

    spec = importlib.util.spec_from_file_location(
        "mathlib_cache_test", Path(__file__).parents[1] / "scripts/replay-state-object-mathlib.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = b"theorem T : True := True.intro\n"
    (tmp_path / "f.lean").write_bytes(source)
    record = {
        "id": "p",
        "theorem_id": "mathlib:T",
        "body": source.decode(),
        "source_artifact": {"filename": "f.lean", "sha256": hashlib.sha256(source).hexdigest()},
    }
    checkpoint = {
        "proof_id": "p",
        "theorem_id": "mathlib:T",
        "body_sha256": hashlib.sha256(source).hexdigest(),
        "source_artifact": record["source_artifact"],
        "environment": "lean-a",
        "validation_policy": VALIDATION_POLICY,
        "status": "complete",
    }
    path = tmp_path / "p.json"
    path.write_text(json.dumps(checkpoint))
    args = SimpleNamespace(proof_sources=tmp_path, output=tmp_path, environment_id="lean-a")
    assert module.run_file([record], args) == ["complete"]
    args.environment_id = "lean-b"
    with pytest.raises(ValueError, match="environment"):
        module.run_file([record], args)
    args.environment_id = "lean-a"
    checkpoint.pop("validation_policy")
    path.write_text(json.dumps(checkpoint))
    with pytest.raises(ValueError, match="predates"):
        module.run_file([record], args)
