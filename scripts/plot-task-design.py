#!/usr/bin/env python3
"""Export the archived task-design evidence as standalone research figures."""

import gzip
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    output = Path("results/strategy-transfer-v1/figures")
    output.mkdir(exist_ok=True)
    report = json.loads(gzip.decompress(Path("results/adversarial-v1/report.json.gz").read_bytes()))
    arms = report["encoders"]["minilm"]
    titles = (
        "Original context\nTheorem alignment: 1.000",
        "Rotated gallery context\nTheorem: .341; context donor: 1.000",
    )
    keys = ("original", "rotated_gallery_context")
    ceiling = max(np.max(arms[k]["distances"]) for k in keys)
    fig, axes = plt.subplots(1, 2, figsize=(9.3, 4.4), constrained_layout=True)
    for ax, key, title in zip(axes, keys, titles, strict=True):
        im = ax.imshow(arms[key]["distances"], vmin=0, vmax=ceiling, cmap="viridis_r")
        ax.set(title=title, xlabel="Gallery theorem index", ylabel="Anchor theorem index")
        ax.set_xticks([0, 3, 6, 9, 11])
        ax.set_yticks([0, 3, 6, 9, 11])
    fig.colorbar(im, ax=axes, label="Euclidean centroid distance", shrink=0.8)
    for extension in ("png", "pdf"):
        fig.savefig(output / f"context-swap.{extension}", dpi=200)
    plt.close(fig)

    screen = json.loads(Path("results/strategy-transfer-v1/headroom-report.json").read_text())
    baselines = screen["baselines"]
    fig, ax = plt.subplots(figsize=(9, 5.6), constrained_layout=True)
    for i, values in enumerate(baselines.values()):
        accuracy, upper = values["accuracy"], values["upper_95"]
        color = "#ad4713" if upper >= 0.90 else "#186580"
        ax.plot([accuracy, upper], [i, i], color=color, linewidth=2)
        ax.plot(accuracy, i, "o", color=color)
        ax.plot(upper, i, "|", color=color, markersize=9)
        ax.text(1.015, i, f"{round(32 * accuracy)}/32", va="center", fontsize=9)
    ax.set_yticks(range(len(baselines)), [name.replace("_", " ") for name in baselines])
    ax.invert_yaxis()
    ax.axvline(0.5, color="gray", linestyle=":", label="Chance")
    ax.axvline(0.9, color="#ad4713", linestyle="--", label="Headroom bound")
    ax.set(
        xlim=(0.25, 1.095),
        xlabel="Accuracy and one-sided exact 95% upper confidence limit",
        title="Strategy-transfer headroom screen: 32 frozen triplets",
    )
    ax.legend(loc="lower left", fontsize=9)
    ax.text(
        0,
        -0.17,
        "Ties use a frozen fair bit per triplet. Token-bag and premise comparisons tie in all 32.\n"
        "Gate requires every upper confidence limit below .90. No cloud distance was scored.",
        transform=ax.transAxes,
        fontsize=9,
    )
    for extension in ("png", "pdf"):
        fig.savefig(output / f"headroom.{extension}", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
