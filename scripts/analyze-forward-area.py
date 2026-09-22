"""Is the forward result just a subfield detector?

The deflationary story for the forward test goes: the encoder reads Lean text,
text carries an area's house style, theorems in the same active area get
connected by the same people later anyway — so the angle predicts the 2026 label
without understanding anything. That story is testable, because Mathlib files
say which area a theorem lives in.

It does not hold. The angle is a weak area detector, area is a weak predictor of
the label, and the angle keeps essentially all of its AUC on cross-area pairs
alone — where the confound cannot operate, since the two theorems are not in the
same area to begin with.

This does not settle the wider question of whether the geometry reads structure
or spelling; a within-area style effect and an α-rename effect are different
things, and the rename test (issue #2) is still the one that would settle it.
What this rules out is the specific and otherwise very plausible story that the
forward result is the map noticing "these two live in the same part of Mathlib".

Area is the second component of the module path, the definition
`analyze-state-bridge.py` already uses for its cross-area rows.

Reproduce: `.venv/bin/python scripts/analyze-forward-area.py`
"""

import argparse
import collections
import gzip
import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np

from noema.paths import result_path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "forward", ROOT / "scripts/analyze-mathlib-forward.py"
)
forward = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forward)


def areas(selection):
    record = json.loads(gzip.open(selection, "rt").read())
    return {
        t["name"]: (t["module"].split(".")[1] if t["module"].count(".") else "")
        for t in record["theorems"]
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--centroids", type=Path, default=result_path("mathlib-forward-v1/centroids.npz")
    )
    ap.add_argument(
        "--selection", type=Path, default=result_path("state-bridge-v1/selected.json.gz")
    )
    ap.add_argument("--edges", type=Path, default=result_path("link-graph-v1/edges.jsonl.gz"))
    ap.add_argument(
        "--connectors", type=Path, default=result_path("mathlib-forward-v1/new-connectors.json")
    )
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    cen, _ = forward.centroids_from_archive(args.centroids)
    names = sorted(cen)
    index = {n: i for i, n in enumerate(names)}
    area = areas(args.selection)
    missing = [n for n in names if not area.get(n)]
    if missing:
        raise SystemExit(f"{len(missing)} theorems have no area, e.g. {missing[:3]}")

    rare = forward.rare_landmarks(set(names), args.edges)
    C = np.array([cen[n] for n in names])
    D = np.degrees(np.arccos(np.clip(C @ C.T, -1, 1)))
    i, j = np.triu_indices(len(names), 1)
    eligible = np.fromiter(
        (not (rare[names[a]] & rare[names[b]]) for a, b in zip(i, j, strict=True)), bool, len(i)
    )
    pi, pj, angle = i[eligible], j[eligible], D[i, j][eligible]

    truth = {
        (min(index[a], index[b]), max(index[a], index[b]))
        for targets in json.loads(args.connectors.read_text()).values()
        for a, b in itertools.combinations(sorted(targets), 2)
        if a in index and b in index and not (rare[a] & rare[b])
    }
    label = np.fromiter(((a, b) in truth for a, b in zip(pi, pj, strict=True)), bool, len(pi))
    same = np.fromiter(
        (area[names[a]] == area[names[b]] for a, b in zip(pi, pj, strict=True)), bool, len(pi)
    )

    top = collections.Counter(area.values()).most_common(5)
    print(f"{len(set(area.values()))} areas; largest: " + ", ".join(f"{a} {n}" for a, n in top))
    print(f"\n{'subset':<20}{'pairs':>12}{'hits':>6}{'angle AUC':>12}")
    rows = {}
    for tag, mask in (
        ("all eligible", np.ones(len(label), bool)),
        ("cross-area only", ~same),
        ("same-area only", same),
    ):
        a = forward.auc(-angle[mask], label[mask])
        print(f"{tag:<20}{int(mask.sum()):>12,}{int(label[mask].sum()):>6}{a:>12.3f}")
        rows[tag] = {"pairs": int(mask.sum()), "hits": int(label[mask].sum()), "auc": a}

    as_detector = forward.auc(-angle, same)
    area_predicts = forward.auc(same.astype(float), label)
    print(f"\nangle as an 'are these the same area?' detector : AUC {as_detector:.3f}")
    print(f"'same area' alone as a predictor of the 2026 link: AUC {area_predicts:.3f}")
    print(
        "\nIf the forward result were the map noticing shared subfield, the angle would"
        "\nbe a strong area detector and the cross-area row would collapse. Neither"
        "\nhappens: area is a weak predictor on its own, and the angle keeps its AUC"
        "\nwhere the confound cannot reach."
    )

    if args.out:
        args.out.write_text(
            json.dumps(
                {
                    "areas": len(set(area.values())),
                    "subsets": rows,
                    "auc_angle_predicts_same_area": as_detector,
                    "auc_same_area_predicts_label": area_predicts,
                },
                indent=2,
            )
            + "\n"
        )
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
