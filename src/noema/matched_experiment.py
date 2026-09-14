"""Frozen length/depth matched theorem-cloud analysis with energy distance."""

import argparse
import copy
import importlib.metadata
import json
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.spatial.distance import cdist

from noema.corpus import digest
from noema.diagnostics import (
    cluster_intervals,
    control_distances,
    encoder_audit,
    stricter_groups,
    trajectory_vector,
)
from noema.encoders import MiniLMEncoder, SyntaxEncoder, TruthEncoder, content_view
from noema.formal_experiment import (
    encode_lookup,
    proof_groups,
    ranking,
    save_checkpoint,
    theorem_permutation_test,
)
from noema.matched_corpus import freeze, quotas
from noema.matching import depth_matched_states, maximum_common_support
from noema.metrics import energy, mmd_squared
from noema.report import provenance
from noema.statistics import benjamini_hochberg

SEED = 416842


def design(plan, manifest, directory):
    frozen = freeze(plan, manifest, directory)
    selections = [{**s, "view": "full"} for s in frozen["selections"]]
    cross = next(s for s in selections if s["direction"] == "cross")
    selections.append(
        {**copy.deepcopy(cross), "direction": "goal_diagnostic", "primary": False, "view": "goal"}
    )
    if plan["within_prover"]:
        within = {
            s["direction"]: s for s in selections if s["direction"] in ("backward", "forward")
        }
        alternate = copy.deepcopy(cross)
        alternate.update(direction="cross_alternative", primary=False)
        for theorem in cross["theorem_ids"]:
            alternate["splits"][theorem] = {
                "anchor": within["backward"]["splits"][theorem]["gallery"],
                "gallery": within["forward"]["splits"][theorem]["gallery"],
            }
        selections.append(alternate)
    diversity = {}
    for policy in ("premise_set", "tactic_histogram"):
        groups = stricter_groups(proof_groups(manifest), policy)
        rows = [
            {
                "theorem_id": t,
                "counts": {
                    g: {
                        str(k): v
                        for k, v in Counter(len(p["tactics"]) for p in groups[t][g]).items()
                    }
                    for g in ("backward", "forward")
                },
            }
            for t in plan["theorem_ids"]
        ]
        support = maximum_common_support(rows, minimum_theorems=12)
        diversity[policy] = support
        if support["maximum_proofs_per_generator"] < plan["regime"]["m"]:
            diversity[policy]["status"] = "insufficient matched proofs; no threshold reduction"
            continue
        allocation = quotas(support["length_allocation"], plan["regime"]["m"])
        selection = {
            "direction": f"diversity_{policy}",
            "primary": False,
            "view": "full",
            "theorem_ids": support["theorem_ids"],
            "splits": {},
        }
        for theorem in support["theorem_ids"]:
            sides = {}
            for side, generator in (("anchor", "backward"), ("gallery", "forward")):
                proofs = []
                for length, count in allocation.items():
                    pool = sorted(
                        (p for p in groups[theorem][generator] if len(p["tactics"]) == int(length)),
                        key=lambda p: p["proof_id"],
                    )
                    proofs.extend(pool[:count])
                sides[side] = {
                    "proof_ids": [p["proof_id"] for p in proofs],
                    "states": [
                        {
                            "proof_id": p["proof_id"],
                            "step": s["step"],
                            "content_sha256": s["content_sha256"],
                        }
                        for p in proofs
                        for s in depth_matched_states(p, n=plan["regime"]["n"])
                    ],
                }
            selection["splits"][theorem] = sides
        selections.append(selection)
        diversity[policy]["status"] = "eligible matched sensitivity"
    return {
        **frozen,
        "selections": selections,
        "diversity": diversity,
        "seed": SEED,
        "analysis_source_sha256": digest(Path(__file__).read_text()),
    }


def evaluate(encoder, cache, manifest, selection, regime):
    ids, view = selection["theorem_ids"], selection["view"]
    lookup = {(p["theorem_id"], p["proof_id"]): p for p in manifest["proofs"]}
    anchors, galleries = [
        [[lookup[t, pid] for pid in selection["splits"][t][side]["proof_ids"]] for t in ids]
        for side in ("anchor", "gallery")
    ]
    texts = []
    for side in ("anchor", "gallery"):
        for theorem in ids:
            cloud = []
            for state in selection["splits"][theorem][side]["states"]:
                proof = lookup[theorem, state["proof_id"]]
                actual = next(s for s in proof["states"] if s["step"] == state["step"])
                if actual["content_sha256"] != state["content_sha256"]:
                    raise ValueError("frozen state hash mismatch")
                cloud.append(content_view(actual["content"], view))
            texts.append(cloud)
    statements = [content_view(ps[0]["initial_state"], view) for ps in anchors]
    trajectories = [
        [content_view(s["content"], view) for s in ps[0]["states"]] for ps in anchors + galleries
    ]
    encode_lookup(encoder, [t for cloud in texts + trajectories for t in cloud] + statements, cache)
    vectors = [np.array([cache[t] for t in cloud]) for cloud in texts]
    a, b = vectors[: len(ids)], vectors[len(ids) :]
    if any(len(x) != regime["m"] * regime["n"] for x in vectors):
        raise ValueError("wrong cloud size")
    metric = energy if regime["metric"] == "energy_statistic" else mmd_squared
    distance = np.array([[metric(x, y) for y in b] for x in a])
    centroid = cdist(np.array([x.mean(axis=0) for x in a]), np.array([x.mean(axis=0) for x in b]))
    single = np.array([[metric(x[: regime["n"]], y[: regime["n"]]) for y in b] for x in a])
    statement_vectors = np.array([cache[t] for t in statements])
    statement = cdist(statement_vectors, statement_vectors)
    trajectory_vectors = np.array(
        [trajectory_vector(np.array([cache[t] for t in cloud])) for cloud in trajectories]
    )
    theorems = {t["theorem_id"]: t for t in manifest["theorems"]}
    controls = control_distances([theorems[t] for t in ids], anchors, galleries)
    controls["trajectory"] = cdist(trajectory_vectors[: len(ids)], trajectory_vectors[len(ids) :])
    cloud_rank, centroid_rank = ranking(distance), ranking(centroid)
    return {
        **{k: selection[k] for k in ("direction", "primary", "view", "theorem_ids")},
        "metric": regime["metric"],
        "proofs_per_cloud": regime["m"],
        "states_per_proof": regime["n"],
        "cloud_size": regime["m"] * regime["n"],
        "dimension": a[0].shape[1],
        "cloud_ranking": cloud_rank,
        "centroid_ranking": centroid_rank,
        "single_proof_ranking": ranking(single),
        "statement_ranking": ranking(statement),
        "gain_over_centroid": cloud_rank["pairwise_win_rate"] - centroid_rank["pairwise_win_rate"],
        "distances": distance.tolist(),
        "centroid_distances": centroid.tolist(),
        "single_proof_distances": single.tolist(),
        "statement_distances": statement.tolist(),
        "controls": {
            k: {"ranking": ranking(v), "distances": v.tolist()} for k, v in controls.items()
        },
        "p_value": theorem_permutation_test(distance, seed=SEED),
        "uncertainty": cluster_intervals(distance, centroid, seed=SEED),
        "anchor_representation": {
            **encoder_audit(a),
            "per_cloud_unique": [len(np.unique(x, axis=0)) for x in a],
        },
        "gallery_representation": {
            **encoder_audit(b),
            "per_cloud_unique": [len(np.unique(x, axis=0)) for x in b],
        },
    }


def gate(comparisons):
    text = next(r for r in comparisons if r["encoder"] == "minilm" and r["direction"] == "cross")
    h1 = text["q_value"] <= 0.05 and text["cloud_ranking"]["pairwise_win_rate"] >= 0.65
    gain = (
        text["gain_over_centroid"] >= 0.05
        and text["uncertainty"]["statistics"]["gain_over_centroid"]["percentile_95"][0] > 0
    )
    noncollapsed = all(
        count > 1
        for side in ("anchor", "gallery")
        for count in text[f"{side}_representation"]["per_cloud_unique"]
    )
    return {
        "matched_text_reproducibility": h1,
        "added_information_over_centroid": gain,
        "noncollapsed": noncollapsed,
        "advance": h1 and gain and noncollapsed,
        "interpretation": "eligible for additional control/cross-training gates"
        if h1 and gain and noncollapsed
        else "stop conditional discovery: matched reproducibility or added-information gate failed",
    }


def run(manifest, frozen, *, root, output, resume=False):
    if frozen["corpus_sha256"] != digest(json.dumps(manifest, sort_keys=True)):
        raise ValueError("corpus differs from pre-embedding freeze")
    if frozen["analysis_source_sha256"] != digest(Path(__file__).read_text()):
        raise ValueError("analysis differs from pre-embedding source freeze")
    encoders = {
        "syntax": SyntaxEncoder(),
        "truth": TruthEncoder(),
        "minilm": MiniLMEncoder(root / ".tools/minilm"),
    }
    contract = {
        "corpus_sha256": frozen["corpus_sha256"],
        "freeze_sha256": digest(json.dumps(frozen, sort_keys=True)),
        "model": encoders["minilm"].manifest,
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "scipy", "onnxruntime", "tokenizers")
        },
        "sources": {
            name: digest((Path(__file__).parent / name).read_text())
            for name in (
                "matched_experiment.py",
                "metrics.py",
                "clouds.py",
                "encoders.py",
                "diagnostics.py",
                "formal_experiment.py",
                "statistics.py",
            )
        },
    }
    if resume:
        if (output / "report.json").exists():
            raise ValueError("completed analysis cannot be overwritten")
        result = json.loads((output / "checkpoint.json").read_text())
        if result["contract"] != contract:
            raise ValueError("resume contract mismatch")
    else:
        output.mkdir(parents=True, exist_ok=False)
        result = {
            "contract": contract,
            "provenance": provenance(),
            "regime": frozen["regime"],
            "comparisons": [],
            "diversity": frozen["diversity"],
            "primary_family_size": 0,
        }
    for name, encoder in encoders.items():
        cache = {}
        if resume and (output / f"{name}-embeddings.npz").exists():
            with np.load(output / f"{name}-embeddings.npz", allow_pickle=False) as saved:
                cache.update(zip(saved["texts"].tolist(), saved["vectors"], strict=True))
        for selection in frozen["selections"]:
            if any(
                r["encoder"] == name and r["direction"] == selection["direction"]
                for r in result["comparisons"]
            ):
                continue
            row = {
                "encoder": name,
                **evaluate(encoder, cache, manifest, selection, frozen["regime"]),
            }
            result["comparisons"].append(row)
            save_checkpoint(output, result, name, cache)
            print(
                f"{name}/{row['direction']}: "
                f"win={row['cloud_ranking']['pairwise_win_rate']:.4f}, "
                f"centroid={row['centroid_ranking']['pairwise_win_rate']:.4f}",
                flush=True,
            )
    primary = [r for r in result["comparisons"] if r["primary"]]
    for row, q in zip(primary, benjamini_hochberg([r["p_value"] for r in primary]), strict=True):
        row["q_value"] = q
    result["primary_family_size"] = len(primary)
    result["gate"] = gate(result["comparisons"])
    (output / "report.md").write_text(markdown(result))
    temporary = output / "report.tmp"
    temporary.write_text(json.dumps(result, allow_nan=False))
    temporary.replace(output / "report.json")
    return result


def markdown(result):
    lines = [
        "# Canonical replay: matched theorem-cloud experiment",
        "",
        "Two discovery algorithms, one replay convention; fresh restricted Horn population.",
        "",
        f"Regime: {result['regime']}. "
        f"Primary tests: {result['primary_family_size']} (one BH family).",
        "",
        "| Encoder | Comparison | Cloud win | Centroid win | Gain | p | Primary q |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in result["comparisons"]:
        lines.append(
            f"| {row['encoder']} | {row['direction']} | "
            f"{row['cloud_ranking']['pairwise_win_rate']:.4f} | "
            f"{row['centroid_ranking']['pairwise_win_rate']:.4f} | "
            f"{row['gain_over_centroid']:.4f} | {row['p_value']:.4g} | "
            f"{row.get('q_value', 'secondary')} |"
        )
    lines += [
        "",
        f"Gate: {result['gate']}",
        "",
        "Primary comparisons have exactly identical length/raw-depth histograms across all groups.",
        "Unmatched uses the unrestricted candidate bank at the same proof/state count. Goal-only",
        "and alternative proof splits are diagnostics. Secondary p-values are descriptive, not",
        "additional confirmatory discoveries. Full baseline matrices, paired theorem-bootstrap",
        "intervals, diversity coverage and representation audits are retained in JSON.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "run"))
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    manifest = json.loads((args.corpus / "manifest.json").read_text())
    if args.action == "freeze":
        result = design(json.loads(args.plan.read_text()), manifest, args.corpus)
        with args.output.open("x") as handle:
            json.dump(result, handle)
    else:
        run(
            manifest,
            json.loads(args.freeze.read_text()),
            root=Path.cwd(),
            output=args.output,
            resume=args.resume,
        )
