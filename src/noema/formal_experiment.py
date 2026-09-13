"""Controlled proof-cloud feasibility experiments with whole-theorem nulls."""

import argparse
import importlib.metadata
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.spatial.distance import cdist

from noema.corpus import digest
from noema.diagnostics import (
    cluster_intervals,
    control_distances,
    edge_auc,
    encoder_audit,
    proof_edges,
    stricter_groups,
    trajectory_vector,
)
from noema.encoders import MiniLMEncoder, SyntaxEncoder, TruthEncoder, content_view
from noema.metrics import mmd_squared
from noema.report import provenance
from noema.statistics import benjamini_hochberg

SEED = 316842


def ordered(items, *, key: str, salt: str, seed: int = SEED):
    return sorted(items, key=lambda item: digest(f"{seed}:{salt}:{item[key]}"))


def proof_groups(manifest: dict[str, Any]) -> dict:
    groups = defaultdict(lambda: defaultdict(list))
    identities = defaultdict(set)
    for proof in manifest["proofs"]:
        if proof["duplicate_sequence"] or len(proof["states"]) < 4:
            continue
        theorem = proof["theorem_id"]
        identity = proof["proof_id"]
        if identity in identities[theorem]:
            raise ValueError("duplicate or cross-generator shared proof identity reached analysis")
        identities[theorem].add(identity)
        groups[theorem][proof["generator"]].append(proof)
    return groups


def select_groups(
    groups: dict, direction: str, *, seed: int = SEED
) -> tuple[list[str], list, list]:
    theorem_ids, anchors, galleries = [], [], []
    for theorem in sorted(groups):
        if direction == "cross":
            a = ordered(groups[theorem]["backward"], key="proof_id", salt=theorem, seed=seed)
            b = ordered(groups[theorem]["forward"], key="proof_id", salt=theorem, seed=seed)
            if min(len(a), len(b)) < 32:
                continue
        else:
            proofs = ordered(groups[theorem][direction], key="proof_id", salt=theorem, seed=seed)
            if len(proofs) < 64:
                continue
            a, b = proofs[:32], proofs[32:]
        theorem_ids.append(theorem)
        anchors.append(a[:32])
        galleries.append(b[:32])
    return theorem_ids, anchors, galleries


def sampled_states(proofs: list, *, seed: int = SEED) -> list[dict]:
    texts = []
    for proof in proofs:
        candidates = sorted(proof["states"], key=lambda s: (s["content_sha256"], s["step"]))
        rng = np.random.default_rng(int(digest(f"{seed}:{proof['proof_id']}")[:16], 16))
        for index in rng.choice(len(candidates), 4, replace=False):
            texts.append({"proof_id": proof["proof_id"], **candidates[index]})
    return texts


def sampled_texts(proofs: list, view: str, *, seed: int = SEED) -> list[str]:
    return [content_view(s["content"], view) for s in sampled_states(proofs, seed=seed)]


def ranking(distance: np.ndarray) -> dict[str, Any]:
    n = len(distance)
    if distance.shape != (n, n) or n < 2 or not np.isfinite(distance).all():
        raise ValueError("ranking requires a finite square comparison matrix with n>=2")
    scores, top1, ranks = [], [], []
    for index, row in enumerate(distance):
        own = row[index]
        tolerance = 1e-10 * max(1.0, float(np.abs(row).max()))
        equal = np.abs(row - own) <= tolerance
        better = row < own - tolerance
        worse = row > own + tolerance
        scores.append(float((worse.sum() + (equal.sum() - 1) / 2) / (n - 1)))
        top1.append(0.0 if better.any() else 1 / int(equal.sum()))
        ranks.append(float(1 + better.sum() + (equal.sum() - 1) / 2))
    return {
        "pairwise_win_rate": float(np.mean(scores)),
        "top1_accuracy": float(np.mean(top1)),
        "mean_rank": float(np.mean(ranks)),
        "per_theorem_win_rate": scores,
    }


def theorem_permutation_test(
    distance: np.ndarray, *, seed: int = SEED, permutations: int = 9999
) -> float:
    if permutations < 1:
        raise ValueError("permutations must be positive")
    n = len(distance)
    ranking(distance)  # validate before inference
    observed = float(np.diag(distance).mean())
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(permutations):
        score = distance[np.arange(n), rng.permutation(n)].mean()
        count += score <= observed + 1e-12
    return (count + 1) / (permutations + 1)


def distance_matrix(a: list[np.ndarray], b: list[np.ndarray]) -> np.ndarray:
    return np.asarray([[mmd_squared(x, y) for y in b] for x in a])


def encode_lookup(encoder, texts: list[str], cache: dict[str, np.ndarray]):
    pending = sorted(set(texts) - cache.keys())
    for start in range(0, len(pending), 100):
        batch = pending[start : start + 100]
        vectors = encoder.encode(batch)
        if vectors.ndim != 2 or not np.isfinite(vectors).all():
            raise ValueError("encoder produced malformed or nonfinite vectors")
        cache.update(zip(batch, vectors, strict=True))
        if start % 500 == 0:
            print(f"Encoded {start + len(batch)}/{len(pending)} new unique states", flush=True)


def design(manifest):
    groups = proof_groups(manifest)
    selections = []
    settings = [("primary", direction, SEED) for direction in ("cross", "backward", "forward")]
    settings += [("primary", "cross", seed) for seed in (316843, 316844)]
    settings += [(policy, "cross", SEED) for policy in ("premise_set", "tactic_histogram")]
    for policy, direction, seed in settings:
        population = groups if policy == "primary" else stricter_groups(groups, policy)
        ids, anchors, galleries = select_groups(population, direction, seed=seed)
        selections.append(
            {
                "policy": policy,
                "direction": direction,
                "seed": seed,
                "theorem_ids": ids,
                "eligibility": {
                    t: {g: len(p) for g, p in v.items()} for t, v in population.items()
                },
                "splits": {
                    theorem: {
                        side: {
                            "proof_ids": [p["proof_id"] for p in proofs],
                            "states": [
                                {k: s[k] for k in ("proof_id", "step", "content_sha256")}
                                for s in sampled_states(proofs, seed=seed)
                            ],
                        }
                        for side, proofs in (("anchor", a), ("gallery", b))
                    }
                    for theorem, a, b in zip(ids, anchors, galleries, strict=True)
                },
            }
        )
    return {"corpus_sha256": digest(json.dumps(manifest, sort_keys=True)), "selections": selections}


def evaluate(encoder, cache, manifest, selection):
    ids = selection["theorem_ids"]
    lookup = {(p["theorem_id"], p["proof_id"]): p for p in manifest["proofs"]}
    anchors, galleries = [
        [[lookup[t, pid] for pid in selection["splits"][t][side]["proof_ids"]] for t in ids]
        for side in ("anchor", "gallery")
    ]
    view, seed = selection["view"], selection["seed"]
    anchor_texts = [sampled_texts(p, view, seed=seed) for p in anchors]
    gallery_texts = [sampled_texts(p, view, seed=seed) for p in galleries]
    statements = [content_view(p[0]["initial_state"], view) for p in anchors]
    # The trajectory baseline uses the same first proof as the single-proof baseline,
    # with its retained order available only to this external baseline.
    trajectories = [
        [content_view(s["content"], view) for s in p[0]["states"]] for p in anchors + galleries
    ]
    all_texts = [t for cloud in anchor_texts + gallery_texts + trajectories for t in cloud]
    encode_lookup(encoder, all_texts + statements, cache)
    a, b = [
        [np.array([cache[t] for t in cloud]) for cloud in texts]
        for texts in (anchor_texts, gallery_texts)
    ]
    distance = distance_matrix(a, b)
    centroid = cdist(np.array([x.mean(axis=0) for x in a]), np.array([x.mean(axis=0) for x in b]))
    single = distance_matrix([x[:4] for x in a], [x[:4] for x in b])
    statement_vectors = np.array([cache[t] for t in statements])
    statement_distances = cdist(statement_vectors, statement_vectors)
    trajectory_vectors = np.array(
        [trajectory_vector(np.array([cache[t] for t in cloud])) for cloud in trajectories]
    )
    theorems = {t["theorem_id"]: t for t in manifest["theorems"]}
    controls = control_distances([theorems[t] for t in ids], anchors, galleries)
    controls["trajectory"] = cdist(trajectory_vectors[: len(ids)], trajectory_vectors[len(ids) :])
    cloud_rank, centroid_rank = ranking(distance), ranking(centroid)
    return {
        **{k: selection[k] for k in ("policy", "direction", "seed", "theorem_ids", "view")},
        "cloud_size": 128,
        "proofs_per_cloud": 32,
        "dimension": a[0].shape[1],
        "cloud_ranking": cloud_rank,
        "centroid_ranking": centroid_rank,
        "single_proof_ranking": ranking(single),
        "statement_ranking": ranking(statement_distances),
        "gain_over_centroid": cloud_rank["pairwise_win_rate"] - centroid_rank["pairwise_win_rate"],
        "mmd_squared": distance.tolist(),
        "centroid_distances": centroid.tolist(),
        "single_proof_mmd_squared": single.tolist(),
        "statement_distances": statement_distances.tolist(),
        "controls": {
            k: {"ranking": ranking(v), "distances": v.tolist()} for k, v in controls.items()
        },
        "uncertainty": cluster_intervals(distance, centroid),
        "mean_unique_vectors_per_anchor": float(np.mean([len(np.unique(x, axis=0)) for x in a])),
        "mean_unique_vectors_per_gallery": float(np.mean([len(np.unique(x, axis=0)) for x in b])),
        "anchor_representation": encoder_audit(a),
        "gallery_representation": encoder_audit(b),
    }


def fidelity(encoder, cache, groups, view):
    records, skipped = [], []
    for theorem, generators in sorted(groups.items()):
        for generator, proofs in sorted(generators.items()):
            if not proofs:
                continue
            proof = ordered(proofs, key="proof_id", salt=theorem)[0]
            try:
                edges = proof_edges(proof)
            except ValueError as error:
                skipped.append(
                    {"theorem_id": theorem, "generator": generator, "reason": str(error)}
                )
                continue
            texts = [content_view(s["content"], view) for s in proof["states"]]
            encode_lookup(encoder, texts, cache)
            records.append(
                {
                    "theorem_id": theorem,
                    "generator": generator,
                    "proof_id": proof["proof_id"],
                    **edge_auc(
                        np.array([cache[t] for t in texts]),
                        [s["step"] for s in proof["states"]],
                        edges,
                    ),
                }
            )
    summary = {}
    for generator in ("backward", "forward"):
        aucs = [r["auc"] for r in records if r["generator"] == generator and r["auc"] is not None]
        summary[generator] = {
            "theorems": len(aucs),
            "mean_auc": float(np.mean(aucs)) if aucs else None,
        }
    return {
        "summary": summary,
        "records": records,
        "skipped": skipped,
        "scope": "generated operational dependency graph; undirected within-proof edge ranking",
    }


def save_checkpoint(output, result, name, cache):
    temporary = output / f"{name}-embeddings.tmp"
    with temporary.open("wb") as stream:
        np.savez_compressed(
            stream, texts=np.array(list(cache)), vectors=np.array(list(cache.values()))
        )
    temporary.replace(output / f"{name}-embeddings.npz")
    temporary = output / "checkpoint.tmp"
    temporary.write_text(json.dumps(result, allow_nan=False))
    temporary.replace(output / "checkpoint.json")


def run(
    manifest: dict[str, Any], *, root: Path, output: Path, freeze: Path, resume: bool = False
) -> dict[str, Any]:
    frozen = json.loads(freeze.read_text())
    actual = design(manifest)
    if actual != frozen:
        raise ValueError("corpus or splits do not match the pre-embedding freeze")
    if resume:
        if (output / "report.json").exists():
            raise ValueError("completed analysis cannot be resumed or overwritten")
    else:
        output.mkdir(parents=True, exist_ok=False)
    groups = proof_groups(manifest)
    encoders = {
        "syntax": SyntaxEncoder(),
        "truth": TruthEncoder(),
        "minilm": MiniLMEncoder(root / ".tools/minilm"),
    }
    result: dict[str, Any] = {
        "schema_version": 2,
        "seed": SEED,
        "provenance": provenance(),
        "corpus_sha256": actual["corpus_sha256"],
        "split_freeze_sha256": digest(freeze.read_text()),
        "encoder_manifest": encoders["minilm"].manifest,
        "encoder_dependencies": {
            k: importlib.metadata.version(k) for k in ("onnxruntime", "tokenizers")
        },
        "eligibility": {t: {g: len(p) for g, p in v.items()} for t, v in groups.items()},
        "comparisons": [],
        "sensitivities": [],
        "skipped": [],
        "fidelity": [],
        "analysis_source_sha256": {
            name: digest((Path(__file__).parent / name).read_text())
            for name in (
                "formal_experiment.py",
                "diagnostics.py",
                "encoders.py",
                "metrics.py",
                "clouds.py",
                "statistics.py",
            )
        },
    }
    if resume:
        previous = json.loads((output / "checkpoint.json").read_text())
        for key in (
            "corpus_sha256",
            "split_freeze_sha256",
            "encoder_manifest",
            "encoder_dependencies",
            "analysis_source_sha256",
        ):
            if previous[key] != result[key]:
                raise ValueError(f"analysis resume mismatch: {key}")
        result = previous
        result.setdefault("resumptions", []).append(provenance())
    for name, encoder in encoders.items():
        cache = {}
        if resume and (output / f"{name}-embeddings.npz").exists():
            with np.load(output / f"{name}-embeddings.npz", allow_pickle=False) as saved:
                if not np.isfinite(saved["vectors"]).all():
                    raise ValueError("nonfinite embedding cache")
                cache.update(zip(saved["texts"].tolist(), saved["vectors"], strict=True))
        for view in ("full", "goal"):
            for selection in actual["selections"]:
                signature = {
                    "encoder": name,
                    "view": view,
                    **{k: selection[k] for k in ("policy", "direction", "seed")},
                }
                if any(
                    all(row[k] == v for k, v in signature.items())
                    for row in result["comparisons"] + result["sensitivities"] + result["skipped"]
                ):
                    continue
                primary = selection["policy"] == "primary" and selection["seed"] == SEED
                if len(selection["theorem_ids"]) < 12:
                    result["skipped"].append(
                        {
                            "encoder": name,
                            "view": view,
                            **{k: selection[k] for k in ("policy", "direction", "seed")},
                            "theorems": len(selection["theorem_ids"]),
                            "reason": "fewer than 12 eligible theorems",
                        }
                    )
                    continue
                entry = evaluate(encoder, cache, manifest, {**selection, "view": view})
                entry["encoder"] = name
                if primary:
                    entry["p_value"] = theorem_permutation_test(np.array(entry["mmd_squared"]))
                result["comparisons" if primary else "sensitivities"].append(entry)
                print(
                    f"{name}/{view}/{selection['direction']}/{selection['policy']}/"
                    f"{selection['seed']}: "
                    f"{len(selection['theorem_ids'])} theorems, "
                    f"cloud win rate {entry['cloud_ranking']['pairwise_win_rate']:.3f}",
                    flush=True,
                )
                save_checkpoint(output, result, name, cache)
            if not any(r["encoder"] == name and r["view"] == view for r in result["fidelity"]):
                result["fidelity"].append(
                    {"encoder": name, "view": view, **fidelity(encoder, cache, groups, view)}
                )
            save_checkpoint(output, result, name, cache)
    for row, q in zip(
        result["comparisons"],
        benjamini_hochberg([r["p_value"] for r in result["comparisons"]]),
        strict=True,
    ):
        row["q_value"] = q
    result["bh_family_size"] = len(result["comparisons"])
    result["bh_family"] = [
        f"{r['encoder']}/{r['view']}/{r['direction']}" for r in result["comparisons"]
    ]
    primary = {
        r["view"]: r
        for r in result["comparisons"]
        if r["encoder"] == "minilm" and r["direction"] == "cross"
    }
    reasons = []
    if set(primary) != {"full", "goal"}:
        reasons.append("insufficient eligible corpus")
    else:
        if any(r["q_value"] > 0.05 for r in primary.values()):
            reasons.append("cross-generator association does not survive all required controls")
        if primary["goal"]["gain_over_centroid"] < 0.05:
            reasons.append("cloud geometry does not add the required information beyond centroids")
        if any(
            r[f"mean_unique_vectors_per_{side}"] <= 1
            for r in primary.values()
            for side in ("anchor", "gallery")
        ):
            reasons.append("a primary representation collapses")
    result["gate"] = {
        "status": "failed" if reasons else "feasibility_pass",
        "reasons": reasons,
        "intersection_search": "ineligible_single_domain_population",
        "scope": "generated Horn logic with a general-text encoder only",
    }
    (output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    (output / "report.md").write_text(markdown(result))
    return result


def markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Controlled formal proof-cloud feasibility study",
        "",
        f"Gate: **{result['gate']['status']}**.",
        "",
        *[f"- {reason}" for reason in result["gate"]["reasons"]],
        "",
        "This is a generated propositional population, not a survey of mathematics. "
        "The text encoder is pretrained on general text. No cross-domain H3/H4 claim follows.",
        "",
        "All reported clouds use 32 distinct proofs × 4 states = 128 occurrences. "
        "Inference permutes whole theorem labels, keeping proof/state blocks intact.",
        "",
        "| Encoder | View | Split | Theorems | Cloud win | Centroid win | Single proof | "
        "Statement | q |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["comparisons"]:
        values = [
            row[k]["pairwise_win_rate"]
            for k in (
                "cloud_ranking",
                "centroid_ranking",
                "single_proof_ranking",
                "statement_ranking",
            )
        ]
        numbers = " | ".join(f"{v:.3f}" for v in values)
        lines.append(
            f"| {row['encoder']} | {row['view']} | {row['direction']} | "
            f"{len(row['theorem_ids'])} | {numbers} | {row['q_value']:.4g} |"
        )
    lines.extend(
        [
            "",
            "Win rates count tied matches as half; chance is 0.5. "
            "The initial-state baseline includes the complete premise context. "
            "Goal-only views remove that context from every state.",
            "",
            f"BH family: {result['bh_family_size']} tests. "
            f"Skipped comparisons: {len(result['skipped'])}; details are in JSON.",
            "",
            "The result does not justify interpreting cross-theorem overlaps as "
            "mathematical discoveries. Full matrices, split identities, and "
            "representation collapse diagnostics are retained in the JSON report.",
            "",
        ]
    )
    lines.extend(
        [
            "## Theorem-level uncertainty",
            "",
            "Exploratory 95% paired theorem-cluster percentile intervals, conditional on "
            "the observed proof samples. Both matrix axes are resampled jointly. "
            "These intervals are not simultaneous or population-wide guarantees.",
            "",
            "| Encoder | View | Split | Cloud win (95% CI) | Gain over centroid (95% CI) |",
            "|---|---|---|---|---|",
        ]
    )
    for row in result["comparisons"]:
        statistics = row["uncertainty"]["statistics"]
        cells = []
        for key in ("pairwise_win_rate", "gain_over_centroid"):
            value = statistics[key]
            low, high = value["percentile_95"]
            cells.append(f"{value['estimate']:.3f} ({low:.3f}, {high:.3f})")
        lines.append(
            f"| {row['encoder']} | {row['view']} | {row['direction']} | " + " | ".join(cells) + " |"
        )
    lines.extend(
        [
            "",
            "## Sampling and diversity sensitivity",
            "",
            "Descriptive repeats; no additional p-values or threshold changes.",
            "",
            "| Encoder | View | Policy | Seed | Cloud win | Centroid win |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for row in result["sensitivities"]:
        lines.append(
            f"| {row['encoder']} | {row['view']} | {row['policy']} | {row['seed']} | "
            f"{row['cloud_ranking']['pairwise_win_rate']:.3f} | "
            f"{row['centroid_ranking']['pairwise_win_rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Operational graph fidelity",
            "",
            "Edge-versus-nonedge distance AUC within one proof per theorem/generator; "
            "chance is 0.5. The backward tree and forward derived-fact graph differ. "
            "These are external validation targets, not encoder inputs.",
            "",
            "| Encoder | View | Generator | Theorems | Mean AUC |",
            "|---|---|---|---:|---:|",
        ]
    )
    for row in result["fidelity"]:
        for generator, summary in row["summary"].items():
            auc = summary["mean_auc"]
            value = f"{auc:.3f}" if auc is not None else "unavailable"
            lines.append(
                f"| {row['encoder']} | {row['view']} | {generator} | "
                f"{summary['theorems']} | {value} |"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run controlled formal feasibility analysis")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.corpus.read_text())
    try:
        run(
            manifest,
            root=Path(__file__).resolve().parents[2],
            output=args.output,
            freeze=args.freeze,
            resume=args.resume,
        )
    except Exception:
        if args.output.exists() and not (args.output / "report.json").exists():
            (args.output / "FAILED").write_text(
                "Analysis interrupted or failed; see terminal log.\n"
            )
        raise


if __name__ == "__main__":
    main()
