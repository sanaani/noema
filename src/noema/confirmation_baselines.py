"""Prospectively specified supplemental proof and trajectory controls."""

import argparse
import json
import re
from pathlib import Path

import numpy as np

from noema.associahedron import lean_source
from noema.corpus import digest
from noema.report import provenance
from noema.strategy_transfer import member_texts, score_distances, tuple_tree, unpack_record
from noema.transfer_confirmation import confirmation_hashes
from noema.transfer_v2 import ROOT, atomic_json

SUPPLEMENT = ROOT / "docs/confirmation-baseline-supplement-v1.md"
COMPONENTS = ("refine", "Eq.trans", "Eq.symm", "congrArg", "hf", "hg", "rfl")


def tactic_histogram(member):
    record = unpack_record(member)
    counts = np.zeros(len(COMPONENTS))
    for program in member["sampled_programs"]:
        source = lean_source(record, tuple_tree(program), record["operator"], record["names"])
        body = source.split(":= by\n", 1)[1].split("#print axioms", 1)[0]
        counts += [
            len(re.findall(rf"\b{re.escape(component)}\b", body)) for component in COMPONENTS
        ]
    return counts / np.linalg.norm(counts)


def supplemental_scores(plan, caches):
    scores = {}
    for name, cache in caches.items():
        for mode in ("single_proof_mean", "position_means"):
            distances = []
            for block in plan["blocks"]:
                representations = []
                for member in block["members"]:
                    _, texts = member_texts(member)
                    points = np.array([cache[t] for t in texts])
                    vector = (
                        points[:2].mean(axis=0)
                        if mode == "single_proof_mean"
                        else points.reshape(4, 2, -1).mean(axis=0).reshape(-1) / np.sqrt(2)
                    )
                    representations.append(vector)
                distances.append(
                    [float(np.linalg.norm(representations[0] - c)) for c in representations[1:]]
                )
            scores[f"{name}_{mode}"] = score_distances(distances, plan)
    trajectories, tactics = [], []
    for block in plan["blocks"]:
        programs = [set(tuple_tree(m["sampled_programs"])) for m in block["members"]]
        trajectories.append([1 - len(programs[0] & c) / len(programs[0] | c) for c in programs[1:]])
        histograms = [tactic_histogram(m) for m in block["members"]]
        tactics.append([float(np.linalg.norm(histograms[0] - h)) for h in histograms[1:]])
    scores["sampled_complete_trajectories"] = score_distances(trajectories, plan)
    scores["tactic_component_histogram"] = score_distances(tactics, plan)
    return scores


def supplemental_gains(cloud_outcomes, scores):
    cloud = np.asarray(cloud_outcomes, dtype=int)
    indices = np.random.default_rng(914202617).integers(len(cloud), size=(10000, len(cloud)))
    result = {}
    for name, score in scores.items():
        delta = cloud - np.asarray(score["outcomes"], dtype=int)
        result[name] = {
            "gain": float(np.mean(delta)),
            "bootstrap_95": np.quantile(np.mean(delta[indices], axis=1), (0.025, 0.975)).tolist(),
        }
    return result


def supplemental_hashes():
    return {**confirmation_hashes(), "confirmation_baselines": digest(Path(__file__).read_text())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    plan = json.loads(args.plan.read_text())
    primary = json.loads((args.run / "report.json").read_text())
    assert primary["freeze"]["plan_sha256"] == digest(args.plan.read_text())
    caches = {}
    for name in ("syntax", "minilm", "reprover"):
        with np.load(args.run / f"vectors/{name}-embeddings.npz", allow_pickle=False) as saved:
            caches[name] = dict(zip(saved["texts"].tolist(), saved["vectors"], strict=True))
    scores = supplemental_scores(plan, caches)
    report = {
        "provenance": provenance(),
        "source_hashes": supplemental_hashes(),
        "supplement_sha256": digest(SUPPLEMENT.read_text()),
        "plan_sha256": digest(args.plan.read_text()),
        "primary_report_sha256": digest((args.run / "report.json").read_text()),
        "scores": scores,
        "gains": supplemental_gains(primary["clouds"]["reprover"]["outcomes"], scores),
        "interpretation": "descriptive original-plan baseline audit; no additional primary gate",
    }
    atomic_json(args.output, report)


if __name__ == "__main__":
    main()
