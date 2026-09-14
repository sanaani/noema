from pathlib import Path

import pytest

from noema.associahedron import (
    apply_step,
    lean_source,
    neighbors,
    population,
    replay,
    transfer,
    trees,
)
from noema.corpus import validate_response, verify_batch
from noema.reprover import byte_ids


def test_rotation_graph_and_shortest_transfer_oracle():
    assert [len(trees(n)) for n in range(2, 8)] == [1, 2, 5, 14, 42, 132]
    for tree in trees(5):
        for adjacent, (path, direction) in neighbors(tree):
            assert apply_step(adjacent, (path, -direction)) == tree
    records = population(7)
    a = records[0]
    for b in records[1:30]:
        successes = 0
        for program in a["programs"]:
            try:
                successes += replay(b["source"], program) == b["target"]
            except ValueError:
                pass
        assert transfer(a, b)[0] == successes / len(a["programs"])
    assert all(len(p) == 5 and replay(a["source"], p) == a["target"] for p in a["programs"])


def test_byt5_utf8_and_no_hidden_truncation():
    assert byte_ids("α") == [209, 180, 1]
    assert byte_ids("a") == [100, 1]
    for invalid in ("", " ", "<pad>", "a" * 1024):
        with pytest.raises(ValueError):
            byte_ids(invalid)


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    not (ROOT / ".tools/repl/.lake/build/bin/repl").exists(), reason="Lean required"
)
def test_associativity_proof_and_wrong_endpoint_rejection():
    record = population(7)[0]
    program = sorted(record["programs"])[0]
    good = lean_source(record, program, "g", [f"x{i}" for i in reversed(range(7))])
    bad = lean_source({**record, "target": record["source"]}, program)
    responses = verify_batch([good, bad], root=ROOT)
    assert len(validate_response(responses[0])) >= 6
    with pytest.raises(ValueError, match="Lean rejected"):
        validate_response(responses[1])
