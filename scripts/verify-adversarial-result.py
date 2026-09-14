#!/usr/bin/env python3
"""Check context interventions from archived states/vectors, without model weights."""

import gzip
import json
import tarfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.spatial.distance import cdist

from noema.adversarial import context_mask
from noema.corpus import digest, validate_response
from noema.encoders import content_view, truth_table
from noema.formal_experiment import ranking


def main():
    canonical = Path("results/canonical-v3")
    archive = Path("results/adversarial-v1")
    report = json.loads(gzip.decompress((archive / "report.json.gz").read_bytes()))
    with tarfile.open(canonical / "corpus.tar.gz", "r:gz") as bundle:
        raw = bundle.extractfile("manifest.json").read().decode()
        manifest = json.loads(raw)
    assert digest(json.dumps(manifest, sort_keys=True)) == report["corpus_sha256"]
    freeze = json.loads(gzip.decompress((canonical / "analysis-freeze.json.gz").read_bytes()))
    selected = next(s for s in freeze["selections"] if s["direction"] == "cross")
    ids = selected["theorem_ids"]
    proofs = {(p["theorem_id"], p["proof_id"]): p for p in manifest["proofs"]}
    contexts = [
        content_view(
            proofs[t, selected["splits"][t]["anchor"]["proof_ids"][0]]["initial_state"], "context"
        )
        for t in ids
    ]
    assert [np.flatnonzero(context_mask(c)).tolist() for c in contexts] == [[255]] * 12
    goals = defaultdict(set)
    for proof in manifest["proofs"]:
        initial = content_view(proof["initial_state"], "context")
        for s in proof["states"]:
            assert content_view(s["content"], "context") == initial
            goals[proof["theorem_id"]].add(content_view(s["content"], "goal"))
    summary = json.loads((archive / "summary.json").read_text())
    assert {k: len(v) for k, v in goals.items()} == summary["distinct_goal_counts"]
    assert len(set().union(*goals.values())) == summary["distinct_goals_total"]
    assert (
        int(truth_table("(p4 ∧ p5) ∧ (p6 ∧ p7)").sum())
        == summary["common_conclusion_satisfying_valuations"]
    )
    samples = []
    for side in ("anchor", "gallery"):
        rows = []
        for t in ids:
            texts = []
            for record in selected["splits"][t][side]["states"]:
                proof = proofs[t, record["proof_id"]]
                s = next(s for s in proof["states"] if s["step"] == record["step"])
                texts.append(content_view(s["content"], "goal"))
            rows.append(texts)
        samples.append(rows)
    checked = 0
    for name, arms in report["encoders"].items():
        with np.load(archive / f"{name}-embeddings.npz", allow_pickle=False) as saved:
            lookup = dict(zip(saved["texts"].tolist(), saved["vectors"], strict=True))
        for arm, expected in arms.items():
            sides = []
            for si, sample in enumerate(samples):
                clouds = []
                for ti, sampled_goals in enumerate(sample):
                    ci = (
                        0
                        if arm == "common_context"
                        else (ti + 1) % 12
                        if arm == "rotated_gallery_context" and si == 1
                        else ti
                    )
                    ctx = contexts[ci]
                    texts = [
                        ctx
                        if arm == "context_only"
                        else goal
                        if arm == "goal_only"
                        else ctx + "\n⊢ " + ("p0" if arm == "common_goal" else goal)
                        for goal in sampled_goals
                    ]
                    clouds.append(np.array([lookup[text] for text in texts]))
                sides.append(clouds)
            centers = [np.array([c.mean(axis=0) for c in side]) for side in sides]
            distances = cdist(*centers)
            assert distances.tolist() == expected["distances"]
            assert ranking(distances) == expected["ranking"]
            if arm == "rotated_gallery_context":
                assert (
                    ranking(distances[:, np.roll(np.arange(12), 1)])
                    == expected["donor_alignment_ranking"]
                )
            within = float(
                np.mean(
                    [
                        np.mean(np.sum((c - center) ** 2, axis=1))
                        for side, cs in zip(sides, centers, strict=True)
                        for c, center in zip(side, cs, strict=True)
                    ]
                )
            )
            pooled = np.vstack(centers)
            between = float(np.mean(np.sum((pooled - pooled.mean(axis=0)) ** 2, axis=1)))
            assert within == expected["within_cloud_variance"]
            assert between == expected["between_centroid_variance"]
            checked += 1
    for certificate in report["equivalence_verification"]:
        source = archive / "proofs" / f"{certificate['theorem']}.lean"
        assert digest(source.read_text()) == certificate["source_sha256"]
        validate_response(certificate["verifier"])
    print(
        json.dumps(
            {
                "all_intervention_fields_exact": True,
                "interventions": checked,
                "context_and_goal_census": "passed",
                "certificate_source_and_record_checks": 12,
                "note": "cached-vector reproduction and recorded Lean response audit; "
                "no new kernel run",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
