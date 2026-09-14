"""Archive raw clustered trials, complete power tables and standard research plots."""

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--plots", action="store_true")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
raw = (args.source / "report.json").read_bytes()
report = json.loads(raw)
(args.output / "report.json.gz").write_bytes(gzip.compress(raw, mtime=0))
(args.output / "report.md").write_text((args.source / "report.md").read_text())
columns = [
    "metric",
    "m",
    "n",
    "d",
    "noise",
    "family",
    "effect",
    "trials",
    "rejections",
    "rate",
    "wilson_lower",
    "wilson_upper",
]
with (args.output / "power-curves.csv").open("w") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns)
    writer.writeheader()
    for row in report["strata"]:
        for metric, summary in row["summary"].items():
            writer.writerow(
                {
                    **{k: row[k] for k in ("m", "n", "d", "noise", "family", "effect")},
                    "metric": metric,
                    **{k: summary[k] for k in ("trials", "rejections", "rate")},
                    "wilson_lower": summary["wilson_95"][0],
                    "wilson_upper": summary["wilson_95"][1],
                }
            )
if args.plots:
    plt.rcParams.update(
        {"font.size": 9, "figure.dpi": 160, "svg.hashsalt": "noema-cluster-power-v1"}
    )
    for dimension in (256, 384):
        for noise in (0.02, 0.15):
            figure, axes = plt.subplots(2, 3, figsize=(10, 6), sharex=True, sharey=True)
            for i, metric in enumerate(("mmd_squared", "energy_statistic")):
                for j, family in enumerate(("separated", "ring_disk", "gaussian_mixture")):
                    axis = axes[i, j]
                    for n, color in ((2, "#0072B2"), (4, "#009E73")):
                        for effect, style in ((1.0, "-"), (0.5, "--")):
                            rows = sorted(
                                (
                                    r
                                    for r in report["strata"]
                                    if r["d"] == dimension
                                    and r["noise"] == noise
                                    and r["family"] == family
                                    and r["n"] == n
                                    and r["effect"] == effect
                                ),
                                key=lambda r: r["m"],
                            )
                            x = [r["m"] for r in rows]
                            y = [r["summary"][metric]["rate"] for r in rows]
                            interval = np.array([r["summary"][metric]["wilson_95"] for r in rows])
                            axis.plot(
                                x,
                                y,
                                style,
                                color=color,
                                marker="o",
                                markersize=3,
                                label=f"n={n}, effect={effect:g}",
                            )
                            axis.fill_between(
                                x, interval[:, 0], interval[:, 1], color=color, alpha=0.08
                            )
                    axis.axhline(0.8, color="black", linewidth=0.7, linestyle=":")
                    axis.set_xscale("log", base=2)
                    axis.set_xticks([8, 16, 32, 64], labels=[8, 16, 32, 64])
                    axis.set_ylim(0, 1.03)
                    axis.grid(alpha=0.18)
                    axis.set_title(f"{metric}\n{family.replace('_', ' ')}")
                    if i == 1:
                        axis.set_xlabel("Independent proofs m")
                    if j == 0:
                        axis.set_ylabel("Raw rejection rate at alpha=.05")
            axes[0, 0].legend(loc="lower right", fontsize=7)
            figure.suptitle(
                f"Proof-block power: d={dimension}, ambient noise={noise}; 100 trials/cell"
            )
            figure.text(
                0.5,
                0.01,
                "Bands: Wilson 95%. Qualification also requires power lower bound >=.80 "
                "and both null upper bounds <=.10.",
                ha="center",
                fontsize=8,
            )
            figure.tight_layout(rect=(0, 0.035, 1, 0.95))
            figure.savefig(args.output / f"power-d{dimension}-noise{noise}.png")
            plt.close(figure)
    (args.output / "plot-provenance.json").write_text(
        json.dumps({"matplotlib": matplotlib.__version__}, indent=2) + "\n"
    )
files = sorted(p for p in args.output.iterdir() if p.is_file())
(args.output / "SHA256SUMS").write_text(
    "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files)
)
