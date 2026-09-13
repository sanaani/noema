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
from noema.encoders import MiniLMEncoder, SyntaxEncoder, TruthEncoder, content_view
from noema.metrics import mmd_squared
from noema.report import provenance
from noema.statistics import benjamini_hochberg

SEED = 316842


def ordered(items, *, key: str, salt: str):
    return sorted(items, key=lambda item: digest(f"{SEED}:{salt}:{item[key]}"))


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


def select_groups(groups: dict, direction: str) -> tuple[list[str], list, list]:
    theorem_ids, anchors, galleries = [], [], []
    for theorem in sorted(groups):
        if direction == "cross":
            a = ordered(groups[theorem]["backward"], key="proof_id", salt=theorem)
            b = ordered(groups[theorem]["forward"], key="proof_id", salt=theorem)
            if min(len(a), len(b)) < 32:
                continue
        else:
            proofs = ordered(groups[theorem][direction], key="proof_id", salt=theorem)
            if len(proofs) < 64:
                continue
            a, b = proofs[:32], proofs[32:]
        theorem_ids.append(theorem)
        anchors.append(a[:32])
        galleries.append(b[:32])
    return theorem_ids, anchors, galleries


def sampled_texts(proofs: list, view: str) -> list[str]:
    texts = []
    for proof in proofs:
        candidates = sorted(proof["states"], key=lambda s: (s["content_sha256"], s["step"]))
        rng = np.random.default_rng(int(digest(f"{SEED}:{proof['proof_id']}")[:16], 16))
        for index in rng.choice(len(candidates), 4, replace=False):
            texts.append(content_view(candidates[index]["content"], view))
    return texts


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


def run(manifest: dict[str, Any], *, root: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    groups = proof_groups(manifest)
    encoders = {
        "syntax": SyntaxEncoder(),
        "truth": TruthEncoder(),
        "minilm": MiniLMEncoder(root / ".tools/minilm"),
    }
    result: dict[str, Any] = {
        "schema_version": 1,
        "seed": SEED,
        "provenance": provenance(),
        "corpus_sha256": digest(json.dumps(manifest, sort_keys=True)),
        "encoder_manifest": encoders["minilm"].manifest,
        "encoder_dependencies": {
            k: importlib.metadata.version(k) for k in ("onnxruntime", "tokenizers")
        },
        "eligibility": {t: {g: len(p) for g, p in v.items()} for t, v in groups.items()},
        "comparisons": [],
        "skipped": [],
    }
    for name, encoder in encoders.items():
        cache = {}
        for view in ("full", "goal"):
            for direction in ("cross", "backward", "forward"):
                theorem_ids, anchor_proofs, gallery_proofs = select_groups(groups, direction)
                if len(theorem_ids) < 12:
                    result["skipped"].append(
                        {
                            "encoder": name,
                            "view": view,
                            "direction": direction,
                            "theorems": len(theorem_ids),
                            "reason": "fewer than 12 eligible theorems",
                        }
                    )
                    continue
                anchor_texts = [sampled_texts(proofs, view) for proofs in anchor_proofs]
                gallery_texts = [sampled_texts(proofs, view) for proofs in gallery_proofs]
                statement_texts = [content_view(p[0]["initial_state"], view) for p in anchor_proofs]
                all_texts = [text for cloud in anchor_texts + gallery_texts for text in cloud]
                encode_lookup(encoder, all_texts + statement_texts, cache)
                a = [np.asarray([cache[text] for text in texts]) for texts in anchor_texts]
                b = [np.asarray([cache[text] for text in texts]) for texts in gallery_texts]
                distance = distance_matrix(a, b)
                centroid = cdist(
                    np.array([x.mean(axis=0) for x in a]), np.array([x.mean(axis=0) for x in b])
                )
                single = distance_matrix([x[:4] for x in a], [x[:4] for x in b])
                statements = np.array([cache[t] for t in statement_texts])
                statement_distances = cdist(statements, statements)
                cloud_ranking = ranking(distance)
                centroid_ranking = ranking(centroid)
                entry = {
                    "encoder": name,
                    "view": view,
                    "direction": direction,
                    "theorem_ids": theorem_ids,
                    "cloud_size": 128,
                    "proofs_per_cloud": 32,
                    "dimension": a[0].shape[1],
                    "cloud_ranking": cloud_ranking,
                    "centroid_ranking": centroid_ranking,
                    "single_proof_ranking": ranking(single),
                    "statement_ranking": ranking(statement_distances),
                    "gain_over_centroid": cloud_ranking["pairwise_win_rate"]
                    - centroid_ranking["pairwise_win_rate"],
                    "p_value": theorem_permutation_test(distance),
                    "mmd_squared": distance.tolist(),
                    "centroid_distances": centroid.tolist(),
                    "single_proof_mmd_squared": single.tolist(),
                    "statement_distances": statement_distances.tolist(),
                    "mean_unique_vectors_per_anchor": float(
                        np.mean([len(np.unique(x, axis=0)) for x in a])
                    ),
                    "mean_unique_vectors_per_gallery": float(
                        np.mean([len(np.unique(x, axis=0)) for x in b])
                    ),
                    "splits": {
                        t: {
                            "anchor": [p["proof_id"] for p in ap],
                            "gallery": [p["proof_id"] for p in bp],
                        }
                        for t, ap, bp in zip(
                            theorem_ids, anchor_proofs, gallery_proofs, strict=True
                        )
                    },
                }
                result["comparisons"].append(entry)
                print(
                    f"{name}/{view}/{direction}: {len(theorem_ids)} theorems, "
                    f"cloud win rate {cloud_ranking['pairwise_win_rate']:.3f}",
                    flush=True,
                )
                (output / "checkpoint.json").write_text(json.dumps(result))
    for row, q in zip(
        result["comparisons"],
        benjamini_hochberg([r["p_value"] for r in result["comparisons"]]),
        strict=True,
    ):
        row["q_value"] = q
    result["bh_family_size"] = len(result["comparisons"])
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
        if any(r["mean_unique_vectors_per_gallery"] <= 1 for r in primary.values()):
            reasons.append("a primary gallery representation collapses")
    result["gate"] = {
        "status": "failed" if reasons else "feasibility_pass",
        "reasons": reasons,
        "intersection_search": "not_authorized_by_evidence",
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
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run controlled formal feasibility analysis")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.corpus.read_text())
    run(manifest, root=Path(__file__).resolve().parents[2], output=args.output)


if __name__ == "__main__":
    main()
