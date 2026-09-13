"""Portable experiment artifacts and a concise human-readable companion."""

import importlib.metadata
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def provenance() -> dict[str, Any]:
    project = Path(__file__).resolve().parents[2]

    def git(*args: str) -> str | None:
        try:
            return subprocess.check_output(
                ["git", "-C", str(project), *args], stderr=subprocess.DEVNULL, text=True
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    status = git("status", "--porcelain")
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {
            name: importlib.metadata.version(name) for name in ("noema-geometry", "numpy", "scipy")
        },
        "git_revision": git("rev-parse", "HEAD"),
        "git_dirty": status != "" if status is not None else None,
    }


def markdown(result: dict[str, Any]) -> str:
    config = result["config"]
    lines = [
        "# Noema synthetic validation",
        "",
        f"Gate: **{result['gate']['status']}**. {result['gate']['reason']}",
        "",
        "Synthetic results assess the measurement pipeline only. No formal proofs or "
        "theorem-geometry hypotheses have been tested.",
        "",
        f"Configuration SHA-256: `{result['config_sha256']}`",
        "",
        f"Seed {config['seed']}; {config['repeats']} trials per stratum; "
        f"{config['permutations']} permutations; alpha {config['alpha']}.",
        "",
        f"Primary test: pooled-bandwidth MMD². BH family: {len(result['trials'])} tests.",
        "",
        "Rejection rates use raw p-values for calibration/power. BH rates use the entire "
        "run as one family. Intervals are pointwise 95% Wilson intervals, not simultaneous "
        "bounds. Same-closer compares MMD²(anchor, replicate) with MMD²(anchor, comparison).",
        "",
        "| Scenario | n | d | Noise | Reject (95% CI) | BH discoveries | Same closer |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["summary"]:
        low, high = row["rejection_wilson_95"]
        lines.append(
            f"| {row['scenario']} | {row['n']} | {row['dimension']} | {row['noise']:g} | "
            f"{row['rejection_rate']:.2f} ({low:.2f}–{high:.2f}) | "
            f"{row['bh_discovery_rate']:.2f} | {row['same_closer_rate']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Metric diagnostics",
            "",
            "Medians across trials; smaller distances indicate more similarity. Radius coverage "
            "is a diagnostic with larger values indicating more overlap. Its radius is half the "
            "pooled kernel bandwidth and changes between pairs; compare cautiously.",
            "",
            "| Scenario | n | d | Noise | MMD² | Energy | Sliced W1 | Coverage | Centroid |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in result["summary"]:
        values = row["median_metrics"]
        cells = " | ".join(
            f"{values[k]:.4f}"
            for k in (
                "mmd_squared",
                "energy_statistic",
                "sliced_wasserstein_1",
                "radius_coverage",
                "centroid_distance",
            )
        )
        lines.append(
            f"| {row['scenario']} | {row['n']} | {row['dimension']} | {row['noise']:g} | {cells} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation limits",
            "",
            "- Same-shape samples are independent, not identical arrays.",
            "- Ring/disk, Gaussian/mixture, and branches/ring share population centroids; "
            "finite-sample centroids fluctuate.",
            "- Noise is per ambient coordinate; increasing dimension increases total noise.",
            "- Sliced Wasserstein averages 1D projections; it is not full-dimensional transport.",
            "- Candidate metrics and thresholds are not yet scientifically qualified or frozen.",
            "- Proof states are correlated; future proof experiments require proof/theorem-level "
            "sampling and nulls rather than this iid permutation test.",
            "",
        ]
    )
    return "\n".join(lines)
