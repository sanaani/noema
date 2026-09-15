"""Render every admitted object, retaining every state in each display."""

import argparse
import gzip
import hashlib
import json
import math
import platform
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy.spatial import ConvexHull, QhullError

from noema.state_objects import atomic_json
from noema.theorem_admission import load_admission


def outline(ax, points):
    try:
        vertices = ConvexHull(points).vertices
        ax.fill(*points[vertices].T, color="#bddfdb", alpha=0.65, zorder=0)
        closed = points[np.r_[vertices, vertices[0]]]
        ax.plot(*closed.T, color="#347d87", lw=0.6, zorder=1)
    except QhullError:
        # A segment or point still has every generating row drawn below.
        order = np.argsort(points[:, 0])
        ax.plot(*points[order].T, color="#347d87", lw=0.6)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=Path("results/state-objects-admitted-v1"))
    parser.add_argument("--forms", type=Path, default=Path("results/theorem-forms-v1"))
    args = parser.parse_args()
    root, out = args.records, args.forms
    forms = json.loads((out / "forms.json").read_text())
    construction = json.loads((out / "construction.json").read_text())
    summary = json.loads((out / "summary.json").read_text())
    if (
        hashlib.sha256((root / "SHA256SUMS").read_bytes()).hexdigest()
        != summary["source_checksums_sha256"]
    ):
        raise ValueError("forms refer to another source archive")
    for line in (root / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if hashlib.sha256((root / name.lstrip("*")).read_bytes()).hexdigest() != digest:
            raise ValueError("source archive failed checksum verification")
    manifest = json.loads((root / "vector-manifest.json").read_text())
    corpus = json.load(gzip.open(Path(manifest["source_archive"]) / "corpus.json.gz"))
    if {f["theorem_id"] for f in forms} != load_admission(corpus, root):
        raise ValueError("forms do not match source admission")
    records = [json.loads(s) for s in (root / "states.jsonl").read_text().splitlines()]
    common = np.load(root / "projection-xy.npy", allow_pickle=False)
    with np.load(out / "local-projections.npz", allow_pickle=False) as part:
        local = part["xy"].copy()
    if local.shape != common.shape or len(local) != len(records):
        raise ValueError("projection row coverage mismatch")
    data = {
        "forms": forms,
        "objects": construction,
        "records": records,
        "local": local.tolist(),
        "common": common.tolist(),
        "summary": summary,
        "formatting": json.loads((out / "formatting-sensitivity.json").read_text()),
    }
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    template = Path(__file__).with_name("theorem-forms-viewer.html").read_text()
    segment = json.loads((out / "segment-certificate.json").read_text())
    if len(segment) != 1 or segment[0]["extent"] != "exact_shared_segment":
        template = template.replace(
            "its intersection is a segment, verified in the original space",
            "its intersection includes at least a segment",
        )
    (out / "explore.html").write_text(template.replace("/*__DATA__*/", text))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "svg.fonttype": "none"})
    fig, panels = plt.subplots(math.ceil(len(forms) / 6), 6, figsize=(16, 34))
    for f, obj, ax in zip(forms, construction, panels.flat, strict=True):
        indices = obj["vector_rows"]
        xy = local[indices]
        outline(ax, xy)
        colors = ["#b85835" if records[i]["text"] == "no goals" else "#167d8a" for i in indices]
        ax.scatter(*xy.T, s=2, c=colors, alpha=0.6, linewidths=0)
        ax.set_aspect("equal", adjustable="datalim")
        name = (
            f["name"]
            .replace("lean_workbook_plus_", "Workbook+ ")
            .replace("lean_workbook_", "Workbook ")
        )
        ax.set_title(
            f"{name}\n{len(indices)} states | dimension {f['numerical_affine_rank']}"
            f" | diameter {f['diameter']:.3f}",
            fontsize=7,
        )
        ax.tick_params(labelsize=5)
        for spine in ax.spines.values():
            spine.set_color("#b8c5c4")
    fig.suptitle(
        "All 102 admitted theorem objects\nLocal two-axis shadows; all 16,592 rows retained."
        " Axes and scales differ between panels.",
        fontsize=15,
        y=0.998,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.984), h_pad=1.3)
    fig.savefig(out / "atlas.pdf")
    fig.savefig(out / "atlas.svg")
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    a, b, c, d = axes.flat
    a.hist([f["diameter"] for f in forms], bins=15, color="#27818d", edgecolor="white")
    a.set(
        xlabel="Full-space diameter",
        ylabel="Theorem objects",
        title="Every diameter uses the same empty-goal point",
    )
    b.scatter(
        [f["numerical_affine_rank"] for f in forms],
        [f["row_spread_axes"]["95"] for f in forms],
        color="#27818d",
        alpha=0.7,
    )
    b.set(
        xlabel="Numerical affine dimension",
        ylabel="Axes retaining 95% of recorded spread",
        title="Many directions, but few dominate the recorded spread",
    )
    c.scatter(
        [f["empty_display_fraction"] for f in forms],
        [f["row_spread_first_axis_fraction"] for f in forms],
        color="#b85835",
        alpha=0.7,
    )
    c.set(
        xlabel="Fraction of records showing 'no goals'",
        ylabel="First-axis fraction of recorded spread",
        title="Repeated empty displays influence the apparent form",
    )
    d.scatter(
        [f["diameter"] for f in forms],
        [f["lateral_extent_over_diameter"] for f in forms],
        color="#27818d",
        alpha=0.7,
    )
    d.set(
        xlabel="Full-space diameter",
        ylabel="Maximum sideways distance / diameter",
        title="Similar longest spans; differing sideways extent",
    )
    for ax in axes.flat:
        ax.grid(alpha=0.15)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Theorem-object forms · 102 admitted groups · all 16,592 states", fontsize=15)
    fig.text(
        0.5,
        0.01,
        "Descriptive recorded-display geometry; "
        "no inference of mathematical meaning or independent sampling.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.025, 1, 0.97))
    for extension in ("png", "svg", "pdf"):
        fig.savefig(out / f"overview.{extension}", dpi=160)
    plt.close(fig)
    atomic_json(
        out / "rendering.json",
        {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__,
            "objects_rendered": len(forms),
            "rows_in_each_projection": len(records),
            "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "template_sha256": hashlib.sha256(
                Path(__file__).with_name("theorem-forms-viewer.html").read_bytes()
            ).hexdigest(),
            "object_definition_changed": False,
        },
    )
    print(out / "explore.html")


if __name__ == "__main__":
    main()
