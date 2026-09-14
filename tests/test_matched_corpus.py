from pathlib import Path

import pytest

from noema.corpus_pilot import candidate_record
from noema.matched_corpus import choose_regime, collect, freeze, quotas
from noema.proofs import backward_search, forward_search, theorem_population

ROOT = Path(__file__).resolve().parents[1]


def test_replication_cannot_promote_a_failed_calibration_metric():
    def report(metric):
        return {
            "envelopes": [
                dict(
                    metric=metric,
                    d=384,
                    noise=0.02,
                    effect=1.0,
                    family=family,
                    eligible_regimes=[dict(m=32, n=4)],
                )
                for family in ("separated", "gaussian_mixture")
            ]
        }

    energy = report("energy_statistic")
    both = {"envelopes": energy["envelopes"] + report("mmd_squared")["envelopes"]}
    assert choose_regime(energy, both)["metric"] == "energy_statistic"
    with pytest.raises(ValueError, match="no independently"):
        choose_regime(report("mmd_squared"), energy)
    other_family = report("energy_statistic")
    other_family["envelopes"][1]["family"] = "ring_disk"
    with pytest.raises(ValueError, match="no independently"):
        choose_regime(energy, other_family)
    assert quotas({"20": 1, "24": 4}, 4) == {"20": 1, "24": 3}


@pytest.mark.skipif(
    not (ROOT / ".tools/repl/.lake/build/bin/repl").exists(), reason="pinned Lean required"
)
def test_canonical_forward_replay_verified_matched_and_recoverable(tmp_path, monkeypatch):
    theorem = theorem_population(1)[0]
    banks = {
        "backward": backward_search(theorem, seed=1, attempts=512),
        "forward": forward_search(theorem, seed=2, width=64),
    }
    shared = {p.identity() for p in banks["backward"]} & {p.identity() for p in banks["forward"]}
    records = {
        g: [
            candidate_record(theorem, p, g, replay="canonical_backward")
            for p in proofs
            if p.identity() not in shared
        ]
        for g, proofs in banks.items()
    }
    length = next(
        length
        for length in range(10, 70)
        if all(sum(p["L"] == length for p in ps) >= 2 for ps in records.values())
    )
    selected = {g: [p for p in ps if p["L"] == length][:2] for g, ps in records.items()}
    plan = {
        "status": "ready",
        "seed": 91827,
        "population_size": 1,
        "replay": "canonical_backward",
        "theorem_ids": [theorem.theorem_id],
        "within_prover": False,
        "regime": {"m": 2, "n": 2},
        "proofs": [{**p, "theorem_id": theorem.theorem_id} for ps in selected.values() for p in ps],
        "splits": {
            theorem.theorem_id: {
                g: {"a": [p["proof_id"] for p in ps], "unmatched": [p["proof_id"] for p in ps]}
                for g, ps in selected.items()
            }
        },
    }
    output = tmp_path / "corpus"
    manifest = collect(plan, root=ROOT, output=output)
    assert manifest["failures"] == []
    audited = freeze(plan, manifest, output)
    assert audited["selections"][0]["length_depth_balance"]["exactly_matched"]
    (output / "manifest.json").unlink()
    monkeypatch.setattr(
        "noema.matched_corpus.verify_batch", lambda *a, **k: pytest.fail("reverified")
    )
    assert collect(plan, root=ROOT, output=output, resume=True)["completed"] == 4
    manifest["proofs"][0]["initial_state"] = "tampered"
    with pytest.raises(ValueError, match="state extraction"):
        freeze(plan, manifest, output)
