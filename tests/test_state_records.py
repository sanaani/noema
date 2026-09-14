import importlib.util
from pathlib import Path

import numpy as np

from noema.state_records import assemble_record_object, state_records


def fixture():
    theorem = {"id": "T", "name": "test", "family": "fixture", "proof_ids": ["p"]}
    proof = {
        "id": "p",
        "theorem_id": "T",
        "trace_complete": True,
        "states": [{"text": "⊢ True", "trace_id": "t", "trace_event": i} for i in range(3)],
    }
    records = list(state_records({"proofs": [proof]}))
    lookup = {r["record_id"]: {"encoder_id": "e", "vector": [1.0, 2.0]} for r in records}
    return theorem, proof, records, lookup


def test_equal_inputs_keep_separate_physical_object_rows():
    theorem, proof, records, lookup = fixture()
    obj = assemble_record_object(theorem, [proof], records, lookup, "e")
    assert obj["vectors"].shape == (3, 2)
    assert len(obj["vector_record_ids"]) == 3
    assert len(set(obj["vector_record_ids"])) == 3
    assert np.array_equal(obj["vectors"][0], obj["vectors"][1])
    assert not np.shares_memory(obj["vectors"][0], obj["vectors"][1])


def test_missing_record_vector_cannot_borrow_equal_input_record_vector():
    theorem, proof, records, lookup = fixture()
    del lookup[records[1]["record_id"]]
    obj = assemble_record_object(theorem, [proof], records, lookup, "e")
    assert obj["missing_vectors"] == [records[1]["record_id"]]
    assert obj["record_count"] == 3 and obj["vector_count"] == 2
    assert not obj["inventory_complete"]


def test_encoder_schedules_all_equal_text_records():
    _, proof, records, _ = fixture()
    path = Path(__file__).parents[1] / "scripts/encode-state-object-states.py"
    spec = importlib.util.spec_from_file_location("encode_state_records", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pending = module.gather({"proofs": [proof]})
    assert list(pending) == [r["record_id"] for r in records]
    assert len(pending) == 3
    assert all(r["text"] == "⊢ True" for r in pending.values())
