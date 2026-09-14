"""Plot the archived GPU check without recomputing or selecting outcomes."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    archive = Path("results/gpu-execution-check-v1")
    report = json.loads((archive / "report.json").read_text())
    comparisons = report["registered_rule_applied_descriptively"]["comparisons"]
    fig, ax = plt.subplots(figsize=(10.5, 6))
    for index, value in enumerate(comparisons.values()):
        lower, upper = value["bootstrap_95"]
        ax.plot([100 * lower, 100 * upper], [index, index], color="#186580", linewidth=2)
        ax.plot(100 * value["gain"], index, "o", color="#186580")
        ax.text(
            1.02,
            index,
            f"p={value['exact_one_sided_p']:.4f}",
            transform=ax.get_yaxis_transform(),
            va="center",
            fontsize=9,
        )
    ax.set_yticks(range(len(comparisons)), [n.replace("_", " ") for n in comparisons])
    ax.invert_yaxis()
    ax.axvline(0, color="#ad4713", linestyle="--", linewidth=1)
    ax.set(
        xlabel="ReProver cloud minus control accuracy (percentage points)",
        title="GPU check: 512 triplets, paired gains and marginal 95% intervals",
    )
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    output = archive / "figures"
    output.mkdir(exist_ok=True)
    fig.savefig(output / "paired-gains.png", dpi=180, bbox_inches="tight")
    fig.savefig(output / "paired-gains.pdf", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
