"""Supplementary anisotropy, sampler-shift and invariance audit."""

import argparse
import json
from pathlib import Path

import numpy as np

from noema.corpus import digest
from noema.metrics import measure
from noema.report import provenance
from noema.statistics import benjamini_hochberg, permutation_mmd, wilson_interval

SCENARIOS = {
    "anisotropic_null": "null",
    "narrow_axis_shift": "alternative",
    "rotated_isotropic_null": "null",
    "sampler_weights": "alternative",
}


def sample(scenario, config, rng):
    n, d = config["n"], config["dimension"]
    x, y = rng.normal(size=(2, n, 2))
    if scenario in ("anisotropic_null", "narrow_axis_shift"):
        x *= [4, 0.25]
        y *= [4, 0.25]
        if scenario == "narrow_axis_shift":
            y += [0, 1]
    elif scenario == "rotated_isotropic_null":
        rotation, _ = np.linalg.qr(rng.normal(size=(2, 2)))
        y = y @ rotation
    elif scenario == "sampler_weights":
        x *= 0.25
        y *= 0.25
        x[:, 0] += np.where(rng.random(n) < 0.5, -1.5, 1.5)
        y[:, 0] += np.where(rng.random(n) < 0.85, -1.5, 1.5)
    else:
        raise ValueError("unknown stress scenario")
    mapping, _ = np.linalg.qr(rng.normal(size=(d, 2)))
    return [z @ mapping.T + rng.normal(scale=config["noise"], size=(n, d)) for z in (x, y)]


def run(config, output):
    # Reuse strict foundation validation for numeric budgets before reserving output.
    from noema.experiment import Config

    Config(
        seed=config["seed"],
        repeats=config["repeats"],
        permutations=config["permutations"],
        sample_sizes=(config["n"],),
        dimensions=(config["dimension"],),
        noise_levels=(config["noise"],),
        projections=config["projections"],
        alpha=config["alpha"],
    )
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "config": config,
        "config_sha256": digest(json.dumps(config, sort_keys=True)),
        "provenance": provenance(),
        "trials": [],
        "invariance": [],
        "gate": "exploratory_only; frozen qualification scope unchanged",
    }
    for scenario in SCENARIOS:
        for trial in range(config["repeats"]):
            seed = int(digest(f"{config['seed']}:{scenario}:{trial}")[:16], 16)
            rng = np.random.default_rng(seed)
            x, y = sample(scenario, config, rng)
            metrics = measure(x, y, projection_seed=seed, projections=config["projections"])
            test = permutation_mmd(x, y, seed=seed + 1, permutations=config["permutations"])
            result["trials"].append(
                {
                    "scenario": scenario,
                    "trial": trial,
                    "seed": seed,
                    "metrics": metrics,
                    "p_value": test["p_value"],
                }
            )
            if trial == 0:
                rotation, _ = np.linalg.qr(rng.normal(size=(config["dimension"],) * 2))
                translation = rng.normal(size=config["dimension"]) * 5
                transformed = measure(
                    x @ rotation + translation,
                    y @ rotation + translation,
                    projection_seed=seed,
                    projections=config["projections"],
                )
                result["invariance"].append(
                    {
                        "scenario": scenario,
                        "absolute_metric_deltas": {
                            k: abs(v - transformed[k]) for k, v in metrics.items()
                        },
                    }
                )
        print(f"Stress: {scenario} complete", flush=True)
    qs = benjamini_hochberg([r["p_value"] for r in result["trials"]])
    for row, q in zip(result["trials"], qs, strict=True):
        row["q_value"] = q
    result["bh_family_size"] = len(qs)
    result["summary"] = []
    for scenario, kind in SCENARIOS.items():
        rows = [r for r in result["trials"] if r["scenario"] == scenario]
        rejected = sum(r["p_value"] <= config["alpha"] for r in rows)
        result["summary"].append(
            {
                "scenario": scenario,
                "kind": kind,
                "rejection_rate": rejected / len(rows),
                "wilson_95": wilson_interval(rejected, len(rows)),
                "bh_discovery_rate": sum(r["q_value"] <= config["alpha"] for r in rows) / len(rows),
            }
        )
    (output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    lines = [
        "# Supplementary measurement stress audit",
        "",
        result["gate"],
        "",
        "| Scenario | Kind | Rejection rate (95% Wilson CI) | BH rate |",
        "|---|---|---|---:|",
    ]
    for row in result["summary"]:
        low, high = row["wilson_95"]
        lines.append(
            f"| {row['scenario']} | {row['kind']} | {row['rejection_rate']:.2f} "
            f"({low:.3f}, {high:.3f}) | {row['bh_discovery_rate']:.2f} |"
        )
    lines += [
        "",
        f"BH family: {len(qs)} tests. Raw metrics and transformation deltas are in JSON.",
        "",
        "The sampler-weight alternative changes the empirical distribution even though "
        "its possible component support is unchanged. This is a sampler-bias diagnostic, "
        "not evidence of a change in mathematical content.",
        "",
    ]
    (output / "report.md").write_text("\n".join(lines))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run(json.loads(args.config.read_text()), args.output)


if __name__ == "__main__":
    main()
