"""Plot every fixture's cumulative mass on the same radius scale."""

import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/encoder-invariance-v1"
result = json.loads((OUT / "analysis.json").read_text())
styles = {
    "original": ("Original", "#222222", "-"),
    "alpha": ("α-renamed", "#0072B2", "--"),
    "pretty_narrow": ("Narrow printer", "#D55E00", "-."),
    "pretty_no_notation": ("No notation", "#009E73", ":"),
    "defeq_id": ("Defeq id", "#CC79A7", "--"),
}
fig, axes = plt.subplots(2, 4, figsize=(15, 7), sharex=True, sharey=True)
for ax, name in zip(axes.flat, result["theorems"], strict=True):
    rows = [r for r in result["objects"] if r["theorem"] == name]
    radii = {"original": rows[0]["both_transformed"]["before_radii"]}
    radii.update({r["arm"]: r["both_transformed"]["after_radii"] for r in rows})
    for arm, values in radii.items():
        label, color, style = styles[arm]
        values = np.sort(values)
        ax.step(
            np.r_[0, values, 2],
            np.r_[0, np.arange(1, len(values) + 1) / len(values), 1],
            where="post",
            label=label,
            color=color,
            linestyle=style,
            linewidth=1.6,
        )
    ax.set_title(f"{name.replace('_', ' ')} · {rows[0]['occurrences']} States")
    ax.set(xlim=(0, 2), ylim=(0, 1.03))
    ax.grid(alpha=0.18)
for ax in axes[-1]:
    ax.set_xlabel("Euclidean radius from initial State")
for ax in axes[:, 0]:
    ax.set_ylabel("Cumulative fraction F_T(r)")
fig.suptitle("The same Lean obligations, different presentations", fontsize=17)
handles, labels = axes.flat[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 0.04))
fig.text(
    0.5,
    0.01,
    "Both center and all nonempty States transformed; repeated occurrences retained. "
    "Eight fixtures are a falsification screen, not corpus validation.",
    ha="center",
    fontsize=10,
)
fig.tight_layout(rect=(0, 0.1, 1, 0.95))
for suffix in ("svg", "png"):
    fig.savefig(OUT / f"curves.{suffix}", dpi=160)
