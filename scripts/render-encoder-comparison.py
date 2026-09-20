"""Export a comparison of presentation sensitivity and distinction retention."""

import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/encoder-comparison-v1"
NAMES = {
    "reprover": "ReProver (reference)",
    "minilm": "MiniLM",
    "leansearch": "LeanStateSearch",
    "e5": "E5-small-v2",
    "bge": "BGE-small-en-v1.5",
    "qwen": "Qwen3 Embedding 0.6B",
    "qwen-instruct": "Qwen + fixed instruction",
}


def main():
    result = json.loads((OUT / "summary.json").read_text())
    arms = ["alpha", "pretty_narrow", "pretty_no_notation", "defeq_id"]
    matrix = (
        np.array(
            [
                [result[name]["raw"]["summary"][arm]["median_w1_over_mean_radius"] for arm in arms]
                for name in NAMES
            ]
        )
        * 100
    )
    fig, (ax, contrasts) = plt.subplots(
        1, 2, figsize=(13, 6.4), gridspec_kw={"width_ratios": [1.4, 1]}, layout="constrained"
    )
    heat = ax.imshow(matrix, cmap="YlOrRd", vmin=0, vmax=max(50, matrix.max()), aspect="auto")
    ax.set_yticks(range(len(NAMES)), NAMES.values())
    ax.set_xticks(range(4), ["α-renaming", "Line wrapping", "No notation", "Defeq id"])
    ax.set_title("Raw input: relative change in cumulative mass", pad=16)
    for i in range(len(NAMES)):
        for j in range(4):
            ax.text(
                j,
                i,
                f"{matrix[i, j]:.1f}%",
                ha="center",
                va="center",
                color="white" if matrix[i, j] > 0.65 * heat.norm.vmax else "black",
            )
    fig.colorbar(
        heat,
        ax=ax,
        location="bottom",
        shrink=0.85,
        label="Median radial W₁ / original mean radius (%)",
    )
    scores = [result[name]["raw"]["contrast_summary"]["equivalent_closer"] for name in NAMES]
    collapses = [result[name]["raw"]["contrast_summary"]["collapsed_pairs"] for name in NAMES]
    y = np.arange(len(NAMES))
    contrasts.barh(y, scores, color="#397fa3", height=0.55)
    contrasts.set(
        ylim=(len(NAMES) - 0.5, -0.5),
        xlim=(0, 108),
        xlabel="Equivalent presentation closer than changed proposition (of 96)",
    )
    contrasts.set_yticks(y, [""] * len(y))
    contrasts.set_title("Raw input: distinction controls", pad=16)
    for i, (score, collapse) in enumerate(zip(scores, collapses, strict=True)):
        contrasts.text(score + 1, i, f"{score}/96", va="center", fontsize=10)
        if collapse:
            contrasts.text(
                103, i, f"{collapse} collapse", va="center", ha="right", fontsize=8, color="#9a3000"
            )
    contrasts.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Changing the encoder does not remove the presentation problem", fontsize=16)
    passed = sum(
        all(s["cdf_w1_failures"] == 0 for s in result[n]["canonical"]["summary"].values())
        and result[n]["canonical"]["contrast_summary"]["collapsed_pairs"] == 0
        for n in NAMES
    )
    fig.supxlabel(
        f"Canonical input: {passed}/{len(NAMES)} configurations pass this screen and retain "
        "12/12 distinctions.\nThis is a finite, constructed screen; "
        "mathematical relatedness remains unvalidated.",
        fontsize=10,
    )
    for extension in ("png", "svg"):
        fig.savefig(OUT / f"comparison.{extension}", dpi=170)


if __name__ == "__main__":
    main()
