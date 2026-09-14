import numpy as np
import pytest

from noema.corpus import digest
from noema.encoders import SyntaxEncoder, content_view
from noema.matched_experiment import evaluate, gate
from noema.metrics import energy


def test_frozen_state_selection_and_energy_reference():
    proofs, theorems, splits = [], [], {}
    for index in range(2):
        theorem = f"fixture_{index}"
        initial = f"p0 p1 p2 : Prop\nh0 : p0\nh1 : p1\nh2 : p{index} → p2\n⊢ p2"
        theorems.append(
            {
                "theorem_id": theorem,
                "facts": [0, 1],
                "rules": [{"name": "h2", "antecedent": index, "consequent": 2}],
            }
        )
        splits[theorem] = {}
        for side in ("anchor", "gallery"):
            ids, frozen_states = [], []
            for k in range(2):
                pid = f"{theorem}-{side}-{k}"
                states = []
                for step, goal in ((1, index), (3, 2)):
                    content = initial.rsplit("⊢", 1)[0] + f"⊢ p{goal}"
                    state = {"step": step, "content": content, "content_sha256": digest(content)}
                    states.append(state)
                    frozen_states.append(
                        {"proof_id": pid, "step": step, "content_sha256": state["content_sha256"]}
                    )
                proofs.append(
                    {
                        "theorem_id": theorem,
                        "proof_id": pid,
                        "states": states,
                        "initial_state": initial,
                        "canonical_tree": {"rule": "h2", "children": []},
                        "tactics": [{"tactic": "apply h2"}] * 5,
                    }
                )
                ids.append(pid)
            splits[theorem][side] = {"proof_ids": ids, "states": frozen_states}
    manifest = {"proofs": proofs, "theorems": theorems}
    selection = {
        "theorem_ids": list(splits),
        "splits": splits,
        "view": "full",
        "direction": "cross",
        "primary": True,
    }
    cache = {}
    result = evaluate(
        SyntaxEncoder(), cache, manifest, selection, {"metric": "energy_statistic", "m": 2, "n": 2}
    )
    clouds = [
        np.array(
            [
                cache[content_view(s["content"])]
                for p in proofs
                if p["theorem_id"] == theorem and "anchor" in p["proof_id"]
                for s in p["states"]
            ]
        )
        for theorem in splits
    ]
    np.testing.assert_allclose(
        result["distances"], [[energy(x, y) for y in clouds] for x in clouds], atol=1e-12
    )
    splits["fixture_0"]["anchor"]["states"][0]["content_sha256"] = "tampered"
    with pytest.raises(ValueError, match="frozen state hash"):
        evaluate(
            SyntaxEncoder(),
            cache,
            manifest,
            selection,
            {"metric": "energy_statistic", "m": 2, "n": 2},
        )


def test_high_reproducibility_does_not_bypass_information_or_collapse_gate():
    row = {
        "encoder": "minilm",
        "direction": "cross",
        "q_value": 0.01,
        "cloud_ranking": {"pairwise_win_rate": 1.0},
        "gain_over_centroid": 0.0,
        "uncertainty": {"statistics": {"gain_over_centroid": {"percentile_95": [0, 0]}}},
        "anchor_representation": {"per_cloud_unique": [5]},
        "gallery_representation": {"per_cloud_unique": [5]},
    }
    assert gate([row])["matched_text_reproducibility"]
    assert not gate([row])["advance"]
    row["gain_over_centroid"] = 0.1
    row["uncertainty"]["statistics"]["gain_over_centroid"]["percentile_95"] = [0.01, 0.15]
    assert gate([row])["advance"]
    row["gallery_representation"]["per_cloud_unique"] = [1]
    assert not gate([row])["advance"]
