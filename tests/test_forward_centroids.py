"""The forward test must reproduce from git alone, and its committed input must
still be the collapse of the encode it claims to come from.

`results/mathlib-forward-v1/centroids.npz` is the only part of the forward test
that is derived rather than captured, so it is the only part that can silently
drift from its source. Two checks: the committed table is reproducible from it,
and — whenever the 272 MB encode happens to be present in a working tree — it is
bit-identical to what that encode produces.
"""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "results/mathlib-forward-v1/centroids.npz"

spec = importlib.util.spec_from_file_location(
    "forward", ROOT / "scripts/analyze-mathlib-forward.py"
)
forward = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forward)


def test_committed_centroids_carry_their_provenance():
    z = np.load(ARCHIVE, allow_pickle=False)
    provenance = json.loads(str(z["provenance"]))
    assert provenance["max_state_df"] == 0.5
    assert len(provenance["vectors_sha256"]) == 64
    assert z["centroids"].shape == (1797, 1472)
    assert z["centroids"].dtype == np.float32
    assert len(z["names"]) == len(z["sizes"]) == 1797
    assert len(set(map(str, z["names"]))) == 1797
    # Centroids are unit vectors; angles are meaningless otherwise.
    assert np.allclose(np.linalg.norm(z["centroids"], axis=1), 1, rtol=0, atol=1e-6)


def test_committed_centroids_reproduce_the_published_bands():
    """Re-derive the README's table from the committed centroids alone."""
    cen, size = forward.centroids_from_archive(ARCHIVE)
    names = sorted(cen)
    index = {n: i for i, n in enumerate(names)}
    rare = forward.rare_landmarks(set(names), ROOT / "results/link-graph-v1/edges.jsonl.gz")
    C = np.array([cen[n] for n in names])
    D = np.degrees(np.arccos(np.clip(C @ C.T, -1, 1)))
    i, j = np.triu_indices(len(names), 1)
    eligible = np.fromiter(
        (not (rare[names[a]] & rare[names[b]]) for a, b in zip(i, j, strict=True)), bool, len(i)
    )
    pi, pj, angle = i[eligible], j[eligible], D[i, j][eligible]

    import itertools

    connectors = json.loads((ROOT / "results/mathlib-forward-v1/new-connectors.json").read_text())
    truth = {
        (min(index[a], index[b]), max(index[a], index[b]))
        for targets in connectors.values()
        for a, b in itertools.combinations(sorted(targets), 2)
        if a in index and b in index and not (rare[a] & rare[b])
    }
    label = np.fromiter(((a, b) in truth for a, b in zip(pi, pj, strict=True)), bool, len(pi))

    published = json.loads((ROOT / "results/mathlib-forward-v1/band-report.json").read_text())
    assert len(angle) == published["eligible_pairs"]
    assert int(label.sum()) == published["positives"]
    for row in published["bands"]:
        mask = (angle >= row["low"]) & (angle < row["high"])
        assert int(mask.sum()) == row["pairs"], row
        assert int(label[mask].sum()) == row["hits"], row

    minsize = np.fromiter(
        (min(size[names[a]], size[names[b]]) for a, b in zip(pi, pj, strict=True)), float, len(pi)
    )
    # Six significant figures, not bit-identity. The 1,797x1,472 Gram matrix is a
    # BLAS reduction, so its summation order follows the thread count: one thread
    # and eight give 0.9581502411706998 against 0.9581502114640211. A handful of
    # near-tied angles swap rank and the rank sum moves in the 8th digit. The
    # published number is three digits; this is three orders tighter than that.
    assert forward.auc(-angle, label) == pytest.approx(published["auc_angle"], rel=1e-6)
    assert forward.auc(minsize, label) == pytest.approx(published["auc_proof_size"], rel=1e-6)


@pytest.mark.skipif(
    not (ROOT / "outputs/state-bridge-v1/vectors/reprover-embeddings.npz").exists(),
    reason="the 272 MB encode is not in git; this check runs where it is present",
)
def test_committed_centroids_match_the_encode_they_came_from():
    z = np.load(ARCHIVE, allow_pickle=False)
    provenance = json.loads(str(z["provenance"]))
    cen, size = forward.centroids_from_vectors(
        ROOT / provenance["vectors"], ROOT / provenance["index"], provenance["max_state_df"]
    )
    names = [str(n) for n in z["names"]]
    assert sorted(cen) == names
    assert [size[n] for n in names] == list(map(int, z["sizes"]))
    np.testing.assert_array_equal(
        np.array([cen[n] for n in names], dtype=np.float32), z["centroids"]
    )
