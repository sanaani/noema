"""Versioned synthetic experiment configuration and deterministic execution."""

import hashlib
import itertools
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from noema.metrics import measure
from noema.statistics import benjamini_hochberg, permutation_mmd, wilson_interval
from noema.synthetic import SCENARIOS, sample_pair


@dataclass(frozen=True)
class Config:
    seed: int = 20260913
    sample_sizes: tuple[int, ...] = (32, 64)
    dimensions: tuple[int, ...] = (2, 64)
    noise_levels: tuple[float, ...] = (0.05,)
    repeats: int = 12
    null_repeats: int | None = None
    permutations: int = 199
    projections: int = 64
    alpha: float = 0.05
    mode: str = "smoke"

    def __post_init__(self) -> None:
        if self.null_repeats is not None and (
            type(self.null_repeats) is not int or self.null_repeats < 1
        ):
            raise ValueError("null_repeats must be a positive integer or null")
        for name, minimum in (("seed", 0), ("repeats", 1), ("permutations", 1), ("projections", 1)):
            value = getattr(self, name)
            if type(value) is not int or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        for name in ("sample_sizes", "dimensions"):
            values = getattr(self, name)
            if not isinstance(values, (list, tuple)) or not values:
                raise ValueError(f"{name} must be a nonempty list")
            if any(type(v) is not int or v < 2 for v in values):
                raise ValueError(f"{name} values must be integers >= 2")
            if len(set(values)) != len(values):
                raise ValueError(f"duplicate {name} would duplicate experimental strata")
            object.__setattr__(self, name, tuple(values))
        noise = self.noise_levels
        if not isinstance(noise, (list, tuple)) or not noise:
            raise ValueError("noise_levels must be a nonempty list")
        if any(type(v) not in (int, float) or not np.isfinite(v) or v < 0 for v in noise):
            raise ValueError("noise levels must be finite numbers >= 0")
        if len(set(noise)) != len(noise):
            raise ValueError("duplicate noise levels would duplicate experimental strata")
        object.__setattr__(self, "noise_levels", tuple(float(v) for v in noise))
        if type(self.alpha) not in (int, float) or self.alpha != 0.05:
            raise ValueError("this protocol fixes alpha at 0.05")
        if self.mode not in ("smoke", "pilot", "qualification"):
            raise ValueError("mode must be smoke, pilot, or qualification")

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "Config":
        if not isinstance(values, dict):
            raise ValueError("configuration must be a JSON object")
        unknown = values.keys() - cls.__dataclass_fields__.keys()
        if unknown:
            raise ValueError(f"unknown configuration keys: {sorted(unknown)}")
        return cls(**values)

    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def trial_seeds(config: Config, scenario: str, n: int, d: int, noise: float, trial: int):
    # Stable across changes in iteration order and additional strata. No Python hash().
    payload = json.dumps([config.seed, scenario, n, d, noise, trial])
    digest = hashlib.sha256(payload.encode()).digest()
    return [int.from_bytes(digest[i : i + 8], "big") for i in range(0, 24, 8)]


def summarize(rows: list[dict[str, Any]], alpha: float) -> list[dict[str, Any]]:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["scenario"], row["n"], row["dimension"], row["noise"])].append(row)
    summaries = []
    for (scenario, n, dimension, noise), group in sorted(groups.items()):
        rejected = sum(r["p_value"] <= alpha for r in group)
        rank_wins = sum(r["same_mmd_squared"] < r["metrics"]["mmd_squared"] for r in group)
        rank_ties = sum(r["same_mmd_squared"] == r["metrics"]["mmd_squared"] for r in group)
        summaries.append(
            {
                "scenario": scenario,
                "kind": SCENARIOS[scenario][2],
                "n": n,
                "dimension": dimension,
                "noise": noise,
                "trials": len(group),
                "rejection_rate": rejected / len(group),
                "rejection_wilson_95": wilson_interval(rejected, len(group)),
                "bh_discovery_rate": sum(r["q_value"] <= alpha for r in group) / len(group),
                "same_closer_rate": (rank_wins + 0.5 * rank_ties) / len(group),
                "median_metrics": {
                    metric: float(np.median([r["metrics"][metric] for r in group]))
                    for metric in group[0]["metrics"]
                },
            }
        )
    return summaries


def qualification_gate(config: Config, summary: list[dict[str, Any]]) -> dict[str, Any]:
    limits = {
        "minimum_trials_per_stratum": 100,
        "minimum_permutations": 999,
        "null_wilson_upper_maximum": 0.10,
        "alternative_wilson_lower_minimum": 0.80,
    }
    if config.mode != "qualification" or config.repeats < 100 or config.permutations < 999:
        return {
            "status": "not_qualified",
            "thresholds": limits,
            "reason": "Development run or insufficient trials/permutations; no metric freeze.",
        }
    expected = set(
        itertools.product(SCENARIOS, config.sample_sizes, config.dimensions, config.noise_levels)
    )
    actual = {(r["scenario"], r["n"], r["dimension"], r["noise"]) for r in summary}
    if (
        actual != expected
        or len(summary) != len(expected)
        or any(row.get("trials", 0) < 100 for row in summary)
    ):
        return {
            "status": "failed",
            "thresholds": limits,
            "reason": "Qualification requires complete summaries for every target stratum.",
        }
    failures = []
    for row in summary:
        low, high = row["rejection_wilson_95"]
        failed = (row["kind"] == "null" and high > 0.10) or (
            row["kind"] == "alternative" and low < 0.80
        )
        if failed:
            failures.append(
                {k: row[k] for k in ("scenario", "n", "dimension", "noise", "rejection_wilson_95")}
            )
    return {
        "status": "failed" if failures else "candidate_pass_requires_protocol_review",
        "thresholds": limits,
        "failures": failures,
        "reason": (
            "One or more target strata failed the fixed calibration/power thresholds."
            if failures
            else "A candidate pass still requires a preregistered held-out run and protocol freeze."
        ),
    }


def run(config: Config) -> dict[str, Any]:
    rows = []
    strata = itertools.product(
        config.sample_sizes, config.dimensions, config.noise_levels, SCENARIOS
    )
    trials = (
        (*stratum, trial)
        for stratum in strata
        for trial in range(
            config.null_repeats
            if config.null_repeats is not None and SCENARIOS[stratum[3]][2] == "null"
            else config.repeats
        )
    )
    for n, dimension, noise, scenario, trial in trials:
        data_seed, permutation_seed, projection_seed = trial_seeds(
            config, scenario, n, dimension, noise, trial
        )
        anchor, replicate, comparison = sample_pair(
            scenario, n=n, dimension=dimension, noise=noise, seed=data_seed
        )
        metrics = measure(
            anchor, comparison, projection_seed=projection_seed, projections=config.projections
        )
        same_metrics = measure(
            anchor, replicate, projection_seed=projection_seed, projections=config.projections
        )
        test = permutation_mmd(
            anchor, comparison, seed=permutation_seed, permutations=config.permutations
        )
        rows.append(
            {
                "scenario": scenario,
                "kind": SCENARIOS[scenario][2],
                "n": n,
                "dimension": dimension,
                "noise": noise,
                "trial": trial,
                "data_seed": data_seed,
                "permutation_seed": permutation_seed,
                "projection_seed": projection_seed,
                "metrics": metrics,
                "same_mmd_squared": same_metrics["mmd_squared"],
                "same_metrics": same_metrics,
                "p_value": test["p_value"],
            }
        )
    for row, q_value in zip(rows, benjamini_hochberg([r["p_value"] for r in rows]), strict=True):
        row["q_value"] = q_value
    summary = summarize(rows, config.alpha)
    return {
        "schema_version": 1,
        "config": asdict(config),
        "config_sha256": config.digest(),
        "inference": {
            "primary_statistic": "biased_gaussian_mmd_squared",
            "null": "iid pooled-label exchangeability within each synthetic comparison",
            "bandwidth": "sqrt(median positive pooled pairwise squared distances)",
            "correction": "Benjamini-Hochberg across all primary tests in this run",
            "family_size": len(rows),
            "minimum_p_value": 1 / (config.permutations + 1),
            "diagnostics": "Other metrics have no attached significance test.",
        },
        "gate": qualification_gate(config, summary),
        "summary": summary,
        "trials": rows,
    }
