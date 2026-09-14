"""Prespecified context interventions on the already observed Horn population."""

import argparse
import gzip
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.spatial.distance import cdist

from noema.corpus import digest, validate_response, verify_batch
from noema.encoders import MiniLMEncoder, SyntaxEncoder, TruthEncoder, content_view, truth_table
from noema.formal_experiment import encode_lookup, ranking
from noema.proofs import backward_search, formula_text, theorem_population
from noema.report import provenance


def conjunction(items):
    return " ∧ ".join(f"({s})" for s in items)


def equivalence_source(theorem):
    atoms = [f"p{i}" for i in range(8)]
    premises = [f"p{i}" for i in theorem.facts] + [
        f"{formula_text(r.antecedent)} → p{r.consequent}" for r in theorem.rules
    ]
    goal = 7
    for atom in range(6, -1, -1):
        goal = (atom, goal)
    tree = backward_search(replace(theorem, goal=goal), seed=7619, attempts=1)[0]
    left_names = ", ".join(f"h{i}" for i in range(len(premises)))
    right_names = ", ".join(f"v{i}" for i in range(8))
    terms = [f"v{i}" for i in theorem.facts] + [
        f"(fun _ => v{r.consequent})" for r in theorem.rules
    ]
    return (
        "import Lean\nset_option linter.unusedVariables false\n"
        f"theorem specimen ({' '.join(atoms)} : Prop) :\n"
        f"({conjunction(premises)}) ↔ ({conjunction(atoms)}) := by\n"
        f"  constructor\n  · intro h\n    rcases h with ⟨{left_names}⟩\n"
        f"    exact {tree.term()}\n  · intro h\n    rcases h with ⟨{right_names}⟩\n"
        f"    exact ⟨{', '.join(terms)}⟩\n#print axioms specimen\n"
    )


def context_mask(context):
    result = np.ones(256, dtype=bool)
    for formula in context.splitlines():
        result &= truth_table(formula)
    return result


def run(root, output):
    output.mkdir(parents=True, exist_ok=False)
    source_dir = root / "outputs/canonical-corpus-v3"
    manifest = json.loads((source_dir / "manifest.json").read_text())
    artifact = root / "results/canonical-v3"
    frozen = json.loads(gzip.decompress((artifact / "analysis-freeze.json.gz").read_bytes()))
    cross = next(s for s in frozen["selections"] if s["direction"] == "cross")
    ids = cross["theorem_ids"]
    lookup = {(p["theorem_id"], p["proof_id"]): p for p in manifest["proofs"]}
    contexts = [
        content_view(
            lookup[t, cross["splits"][t]["anchor"]["proof_ids"][0]]["initial_state"], "context"
        )
        for t in ids
    ]
    context_violations = sum(
        content_view(s["content"], "context") != content_view(p["initial_state"], "context")
        for p in manifest["proofs"]
        for s in p["states"]
    )
    masks = [context_mask(c) for c in contexts]
    result = {
        "provenance": provenance(),
        "scope": "diagnostic, no new significance claims or pair mining",
        "source_sha256": digest(Path(__file__).read_text()),
        "theorem_ids": ids,
        "corpus_sha256": frozen["corpus_sha256"],
        "context_change_occurrences": context_violations,
        "context_truth_valuations": [np.flatnonzero(mask).tolist() for mask in masks],
        "distinct_context_texts": len(set(contexts)),
        "encoders": {},
    }
    theorems = {t.theorem_id: t for t in theorem_population(24, seed=132671)}
    sources = [equivalence_source(theorems[t]) for t in ids]
    responses = verify_batch(sources, root=root)
    (output / "proofs").mkdir()
    result["equivalence_verification"] = []
    for theorem, source, response in zip(ids, sources, responses, strict=True):
        validate_response(response)
        (output / "proofs" / f"{theorem}.lean").write_text(source)
        result["equivalence_verification"].append(
            {"theorem": theorem, "source_sha256": digest(source), "verifier": response}
        )
    samples = []
    for side in ("anchor", "gallery"):
        side_samples = []
        for t in ids:
            states = []
            for record in cross["splits"][t][side]["states"]:
                proof = lookup[t, record["proof_id"]]
                state = next(s for s in proof["states"] if s["step"] == record["step"])
                states.append(content_view(state["content"], "goal"))
            side_samples.append(states)
        samples.append(side_samples)
    encoders = {
        "syntax": SyntaxEncoder(),
        "truth": TruthEncoder(),
        "minilm": MiniLMEncoder(root / ".tools/minilm"),
    }
    for name, encoder in encoders.items():
        with np.load(artifact / f"{name}-embeddings.npz", allow_pickle=False) as saved:
            cache = dict(zip(saved["texts"].tolist(), saved["vectors"], strict=True))
        interventions = {}
        for arm in (
            "original",
            "context_only",
            "common_goal",
            "rotated_gallery_context",
            "common_context",
            "goal_only",
        ):
            sides = []
            for side, side_samples in enumerate(samples):
                clouds = []
                for index, goals in enumerate(side_samples):
                    context = contexts[
                        0
                        if arm == "common_context"
                        else (index + 1) % len(ids)
                        if side == 1 and arm == "rotated_gallery_context"
                        else index
                    ]
                    texts = [
                        context
                        if arm == "context_only"
                        else goal
                        if arm == "goal_only"
                        else context + "\n⊢ " + ("p0" if arm == "common_goal" else goal)
                        for goal in goals
                    ]
                    if name == "truth" and arm == "context_only":
                        cache[context] = 2 * context_mask(context).astype(float) / 48
                    else:
                        encode_lookup(encoder, texts, cache)
                    clouds.append(np.array([cache[text] for text in texts]))
                sides.append(clouds)
            centers = [np.array([cloud.mean(axis=0) for cloud in side]) for side in sides]
            distance = cdist(*centers)
            pooled = np.vstack(centers)
            within = np.mean(
                [
                    np.mean(np.sum((cloud - center) ** 2, axis=1))
                    for side, centroid in zip(sides, centers, strict=True)
                    for cloud, center in zip(side, centroid, strict=True)
                ]
            )
            between = float(np.mean(np.sum((pooled - pooled.mean(axis=0)) ** 2, axis=1)))
            row = {
                "ranking": ranking(distance),
                "distances": distance.tolist(),
                "within_cloud_variance": float(within),
                "between_centroid_variance": between,
            }
            if arm == "rotated_gallery_context":
                row["donor_alignment_ranking"] = ranking(
                    distance[:, np.roll(np.arange(len(ids)), 1)]
                )
            interventions[arm] = row
            print(name, arm, row["ranking"]["pairwise_win_rate"], flush=True)
        result["encoders"][name] = interventions
        np.savez_compressed(
            output / f"{name}-embeddings.npz",
            texts=np.array(list(cache)),
            vectors=np.array(list(cache.values())),
        )
    (output / "report.json").write_text(json.dumps(result, allow_nan=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run(Path.cwd(), args.output)
