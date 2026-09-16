"""Render the historical pilot with inspectable inputs and full-space distances."""

import json
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parents[1]
out = root / "results/historical-connections-v1"
analysis = json.loads((out / "analysis.json").read_text())
inputs = json.loads((out / "inputs.json").read_text())
distances = np.load(out / "distances.npy", allow_pickle=False)
names = [n for c in analysis["cases"] for n in (c["a"], c["b"], c["bridge"])]
matrices = {}
for variant in ("typed", "closed", "introduced"):
    idx = [
        next(i for i, r in enumerate(inputs) if r["name"] == n and r["variant"] == variant)
        for n in names
    ]
    matrices[variant] = distances[np.ix_(idx, idx)].tolist()
data = {"cases": analysis["cases"], "inputs": inputs, "matrices": matrices}
payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
template = (root / "scripts/historical-connections-viewer.html").read_text()
(out / "explore.html").write_text(template.replace("__DATA__", payload))
print(out / "explore.html")
