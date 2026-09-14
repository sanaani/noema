"""Export registered v2 outcomes; this script never computes new cloud scores."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def save(fig, directory, name):
    for extension in ("png", "pdf"):
        fig.savefig(directory / f"{name}.{extension}", dpi=200)
    plt.close(fig)


def main():
    archive = Path("results/strategy-transfer-v2")
    output = archive / "figures"
    output.mkdir(exist_ok=True)
    power = json.loads((archive / "power/report.json").read_text())
    rows = [r for r in power["rows"] if r["condition"] == "alternative"]
    values = np.array([r["rate"] for r in rows])
    intervals = np.array([r["wilson_95"] for r in rows])
    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    ax.errorbar(
        [r["n"] for r in rows],
        values,
        yerr=np.array([values - intervals[:, 0], intervals[:, 1] - values]),
        fmt="o-",
        color="#186580",
        capsize=4,
    )
    ax.axhline(0.80, linestyle="--", color="#ad4713", label="Required lower power bound")
    ax.set(
        xlabel="Independent triplets",
        ylabel="Joint detection probability",
        ylim=(0.5, 1.02),
        title="Power qualification before v2 task scores",
    )
    ax.set_xticks([256, 512, 1024])
    ax.legend(loc="lower right")
    ax.text(
        0.02,
        0.97,
        "10,000 trials per size; .80 cloud vs .65 controls\n"
        "Gain ≥ .10 and exact paired p ≤ .05 against all nine",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
    )
    save(fig, output, "power")
    screen = json.loads((archive / "headroom/headroom-report.json").read_text())
    scores = screen["baselines"]
    fig, ax = plt.subplots(figsize=(9, 5.6), constrained_layout=True)
    for i, b in enumerate(scores.values()):
        color = "#186580" if b["upper_95"] < 0.90 else "#ad4713"
        ax.plot([b["accuracy"], b["upper_95"]], [i, i], color=color, linewidth=2)
        ax.plot(b["accuracy"], i, "o", color=color)
        ax.plot(b["upper_95"], i, "|", color=color, markersize=9)
        ax.text(1.005, i, f"{sum(b['outcomes'])}/64", va="center", fontsize=9)
    ax.set_yticks(range(len(scores)), [k.replace("_", " ") for k in scores])
    ax.invert_yaxis()
    ax.axvline(0.5, color="gray", linestyle=":")
    ax.axvline(0.9, color="#ad4713", linestyle="--")
    ax.set(
        xlim=(0.25, 1.085),
        xlabel="Accuracy and one-sided exact 95% upper confidence limit",
        title="64 fresh triplets with exact structural matching",
    )
    ax.text(
        0,
        -0.16,
        "Source and target clade distances, premise overlap and bag distances match exactly.\n"
        "The three matched controls tie in every triplet; their half-credit score is .500.",
        transform=ax.transAxes,
        fontsize=9,
    )
    save(fig, output, "headroom")
    path = archive / "geometry/geometry-report.json"
    if path.exists():
        geometry = json.loads(path.read_text())
        gains = [t["minimum_gain"] for t in geometry["trials"]]
        fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
        ax.hist(
            gains,
            bins=np.arange(-1.0078125, 1.0234375, 0.015625),
            color="#186580",
            edgecolor="white",
        )
        ax.set_xlim(min(min(gains), 0.10) - 0.05, max(max(gains), 0.10) + 0.05)
        ax.axvline(
            0.10, color="#ad4713", linestyle="--", label="Required gain in at least 80/100 draws"
        )
        ax.set(
            xlabel="ReProver energy gain over the strongest control in each draw",
            ylabel="Proof-resampling draws",
            title="Conditional stability on the fixed development task",
        )
        ax.legend(fontsize=9)
        ax.text(
            0.02,
            0.97,
            "100 prespecified draws; four proofs × two states\n"
            "Centroids use the same proof sample as energy",
            transform=ax.transAxes,
            va="top",
            fontsize=9,
        )
        save(fig, output, "stability")


if __name__ == "__main__":
    main()
