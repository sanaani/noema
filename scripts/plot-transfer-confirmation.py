"""Plot archived confirmation power and, when present, paired effect intervals."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def save(fig, directory, name):
    fig.tight_layout()
    fig.savefig(directory / f"{name}.png", dpi=180)
    fig.savefig(directory / f"{name}.pdf")
    plt.close(fig)


def main():
    archive = Path("results/strategy-transfer-confirmation-v1")
    output = archive / "figures"
    output.mkdir(exist_ok=True)
    power = json.loads((archive / "power.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, discordance in zip(axes, (0.05, 0.10), strict=True):
        for n, color in ((512, "#186580"), (1024, "#b35625"), (2048, "#708a42")):
            rows = [r for r in power["rows"] if r["n"] == n and r["discordance"] == discordance]
            ax.plot(
                [100 * r["gain"] for r in rows],
                [r["power"] for r in rows],
                "o-",
                color=color,
                label=f"N={n:,}" + (" (registered)" if n == 512 else " (planning)"),
            )
        ax.set(
            title=f"Discordance = {discordance:.0%}",
            xlabel="True accuracy gain (percentage points)",
            ylim=(0, 1.04),
            xlim=(0, 5.1),
        )
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Exact individual paired-test power")
    fig.suptitle("Sensitivity below the removed ten-point margin", fontsize=13)
    save(fig, output, "small-effect-power")
    path = archive / "run/report.json"
    if not path.exists():
        return
    report = json.loads(path.read_text())
    comparisons = report["inference"]["comparisons"]
    fig, ax = plt.subplots(figsize=(11, 6.5))
    names = list(comparisons)
    for index, name in enumerate(names):
        value = comparisons[name]
        lower, upper = value["bootstrap_95"]
        ax.plot([100 * lower, 100 * upper], [index, index], color="#186580", linewidth=2)
        ax.plot(100 * value["gain"], index, "o", color="#186580")
        ax.text(
            1.01,
            index,
            f"p={value['exact_one_sided_p']:.4g}",
            transform=ax.get_yaxis_transform(),
            va="center",
            fontsize=9,
        )
    ax.set_yticks(range(len(names)), [n.replace("_", " ") for n in names])
    ax.invert_yaxis()
    ax.axvline(0, color="#ad4713", linestyle="--")
    ax.set(
        xlabel="ReProver energy minus control accuracy (percentage points)",
        title="512-triplet confirmation: paired gains and marginal bootstrap 95% intervals",
    )
    ax.grid(axis="x", alpha=0.2)
    fig.subplots_adjust(right=0.84)
    save(fig, output, "paired-gains")


if __name__ == "__main__":
    main()
