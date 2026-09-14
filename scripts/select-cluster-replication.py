"""Freeze every provisional minimum and its null controls for new seeded trials."""

import argparse
import json
from pathlib import Path

from noema.cluster_power import row_key
from noema.corpus import digest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("report", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
report = json.loads(args.report.read_text())
selected = {}
for envelope in report["envelopes"]:
    minimum = envelope["minimum"]
    if minimum is None:
        continue
    row = {
        "m": minimum["m"],
        "n": minimum["n"],
        "d": envelope["d"],
        "noise": envelope["noise"],
        "family": envelope["family"],
        "effect": envelope["effect"],
    }
    selected[row_key(row)] = row
    for family in ("gaussian_null", "ring_null"):
        null = {**row, "family": family, "effect": 1.0}
        selected[row_key(null)] = null
args.output.mkdir(parents=True, exist_ok=False)
config = {**report["config"], "seed": 928195, "repeats": 200, "null_repeats": 400}
(args.output / "config.json").write_text(json.dumps(config, indent=2) + "\n")
(args.output / "selected.json").write_text(
    json.dumps(sorted(selected.values(), key=row_key), indent=2) + "\n"
)
(args.output / "freeze.json").write_text(
    json.dumps(
        {
            "calibration_report_sha256": digest(args.report.read_text()),
            "selection": "union of every provisional envelope minimum and both same-regime nulls",
            "strata": len(selected),
            "alternative_trials": sum(not r["family"].endswith("null") for r in selected.values())
            * 200,
            "null_trials": sum(r["family"].endswith("null") for r in selected.values()) * 400,
            "config_sha256": digest((args.output / "config.json").read_text()),
            "selected_sha256": digest((args.output / "selected.json").read_text()),
        },
        indent=2,
    )
    + "\n"
)
