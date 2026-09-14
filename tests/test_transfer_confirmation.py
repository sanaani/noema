import gzip
import json

import numpy as np
import pytest

from noema.transfer_confirmation import (
    CONTROLS,
    audit_all_proofs,
    exact_paired_power,
    paired_summary,
)


def test_exact_power_matches_small_enumerable_case():
    # With five discordant pairs, only five cloud wins reject at alpha .05.
    assert exact_paired_power(5, 0.2, 1.0) == pytest.approx(0.6**5)
    assert exact_paired_power(5, 0.0, 1.0) == pytest.approx(1 / 32)
    assert exact_paired_power(1, 1.0, 1.0) == 0
    assert exact_paired_power(100, 0.0, 0.0) == 0
    for q in (0.05, 0.10, 0.20, 0.35):
        assert exact_paired_power(512, 0.0, q) <= 0.05
    with pytest.raises(ValueError):
        exact_paired_power(512, 0.2, 0.1)


def test_small_positive_gain_can_pass_but_all_controls_are_required():
    cloud = np.zeros(1000, dtype=int)
    cloud[:20] = 1
    baseline = np.zeros(1000, dtype=int)
    baseline[:10] = 1
    clouds = {"reprover": {"outcomes": cloud.tolist()}}
    controls = {name: {"outcomes": baseline.tolist()} for name in CONTROLS}
    report = paired_summary(clouds, controls, repeats=100)
    assert report["primary_pass"]
    assert report["minimum_effect_requirement"] is None
    for comparison in report["comparisons"].values():
        assert comparison["gain"] == 0.01
        assert comparison["exact_one_sided_p"] == 1 / 1024
    controls["reprover_centroid"] = clouds["reprover"]
    assert not paired_summary(clouds, controls, repeats=100)["primary_pass"]
    del controls["reprover_centroid"]
    with pytest.raises(ValueError, match="nine"):
        paired_summary(clouds, controls)


def test_proof_checkpoint_skips_completed_blocks_after_interruption(tmp_path, monkeypatch):
    calls = []

    def fixture(plan, root, target, *, all_blocks):
        index = plan["blocks"][0]["id"]
        calls.append(index)
        if calls == [0, 1]:
            raise RuntimeError("simulated reboot")
        (target / "lean-audit.json.gz").write_bytes(gzip.compress(json.dumps([{}]).encode()))
        return {"verified_proofs": 12, "matched_intermediate_states": 60}

    monkeypatch.setattr("noema.transfer_confirmation.audit_fixture", fixture)
    plan = {"blocks": [{"id": i} for i in range(3)]}
    with pytest.raises(RuntimeError, match="reboot"):
        audit_all_proofs(plan, tmp_path)
    totals = audit_all_proofs(plan, tmp_path)
    assert calls == [0, 1, 1, 2]
    assert totals == {"verified_proofs": 36, "matched_intermediate_states": 180}
    plan["blocks"][0]["id"] = 42
    with pytest.raises(ValueError, match="checkpoint changed"):
        audit_all_proofs(plan, tmp_path)
