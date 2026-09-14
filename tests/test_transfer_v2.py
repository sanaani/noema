import json

import numpy as np
import pytest

from noema.encoders import SyntaxEncoder
from noema.transfer_v2 import (
    audit_matching,
    cached_vectors,
    matched_assignments,
    resampled_plans,
    run_geometry,
)


@pytest.fixture(scope="module")
def small_plan():
    return matched_assignments("development", 2)


def test_exact_matching_and_disjoint_programs(small_plan):
    assert small_plan == matched_assignments("development", 2)
    audit = audit_matching(small_plan)
    assert audit["distinct_endpoint_pairs"] == 6
    assert audit["cross_triplet_program_overlap"] == 0
    duplicate = {**small_plan, "blocks": [small_plan["blocks"][0]] * 2}
    with pytest.raises(ValueError, match="strategies reused"):
        audit_matching(duplicate)
    for count in (0, 1, 3, -2):
        with pytest.raises(ValueError, match="even"):
            matched_assignments("development", count)


def test_proof_resampling_preserves_membership_and_all_matching(small_plan):
    samples = list(resampled_plans(small_plan, repeats=3))
    assert samples == list(resampled_plans(small_plan, repeats=3))
    assert any(s != small_plan for s in samples)
    for plan in samples:
        audit_matching(plan)
        for block in plan["blocks"]:
            for member in block["members"]:
                assert len(set(member["sampled_programs"])) == 4
                assert set(member["sampled_programs"]) <= set(member["programs"])


def test_encoding_checkpoint_survives_failure_and_resumes_only_missing(tmp_path, monkeypatch):
    requested = []

    class FailingEncoder:
        manifest = {"dimension": 8}

        def encode(self, texts):
            requested.extend(texts)
            if len(requested) > 20:
                raise RuntimeError("simulated reboot")
            return SyntaxEncoder(8).encode(texts)

    monkeypatch.setattr("noema.transfer_v2.encoder_factory", lambda name: FailingEncoder())
    texts = [f"⊢ f x{i} x0 = x0" for i in range(25)]
    with pytest.raises(RuntimeError, match="reboot"):
        cached_vectors("syntax", texts, tmp_path)
    with np.load(tmp_path / "syntax-embeddings.npz", allow_pickle=False) as saved:
        assert len(saved["texts"]) == 20
    resumed = []

    class WorkingEncoder:
        manifest = {"dimension": 8}

        def encode(self, texts):
            resumed.extend(texts)
            return SyntaxEncoder(8).encode(texts)

    monkeypatch.setattr("noema.transfer_v2.encoder_factory", lambda name: WorkingEncoder())
    result = cached_vectors("syntax", texts, tmp_path)
    assert len(resumed) == 5
    np.testing.assert_array_equal(
        np.array([result[t] for t in texts]), SyntaxEncoder(8).encode(texts)
    )


def test_geometry_cannot_bypass_upstream_gate(tmp_path, small_plan):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(small_plan))
    (tmp_path / "headroom-report.json").write_text(json.dumps({"headroom_pass": False}))
    power = tmp_path / "power.json"
    power.write_text(json.dumps({"qualified_n": 512}))
    with pytest.raises(ValueError, match="upstream"):
        run_geometry(plan, tmp_path, power, tmp_path / "geometry")
    assert not (tmp_path / "geometry").exists()
