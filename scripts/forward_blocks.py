"""Blocked pair statistics for the unseeded corpus, in bounded memory.

`analyze-forward-residual.py` materialises the whole upper triangle -- 66M
angles, 66M Jaccards, two 66M index vectors -- which is why it needs a 64 GB
worker. Every question asked of that array is a *rank* question, and a rank
question only needs a histogram of the population plus the positives' own
values. This walks the triangle in row blocks and accumulates one histogram
per subset, so the corpus scaling sweep and the residual null can both run on
a laptop.

Faithfulness to the published numbers is the acceptance test, not a claim:
`--self-check` reproduces `residual.json`'s four rows from this path.
"""

from __future__ import annotations

import gzip
import importlib.util
import itertools
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import scipy.sparse as sp

ROOT = Path(__file__).resolve().parents[1]


def _load(stem: str, path: str):
    spec = importlib.util.spec_from_file_location(stem, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


forward = _load("forward", "scripts/analyze-mathlib-forward.py")
vocabmod = _load("vocabulary", "scripts/analyze-forward-vocabulary.py")

# 0.0005 deg bins over [0, 180]. Within-bin pairs are scored as ties, so the
# bin width is the only approximation here: at 66M pairs over 360k bins the
# average bin holds ~180 pairs, and a tie contributes half of that to one
# positive's rank, i.e. ~1e-6 of the AUC. Three decimals are safe.
NBINS = 360_000
BINW = 180.0 / NBINS

SUBSETS = ("all eligible", "cross-area only", "vocab<5%", "cross-area AND vocab<5%")


@dataclass
class Corpus:
    names: list[str]
    C: np.ndarray  # (N, d) float32, unit rows
    rare: sp.csr_matrix  # (N, L) float32 indicator over rare 2024 landmarks
    vocab: sp.csr_matrix  # (N, V) float32 indicator over state identifiers
    vsize: np.ndarray  # (N,) float32, |vocabulary| per theorem
    area: np.ndarray  # (N,) int32, Mathlib area code
    module: np.ndarray  # (N,) int32, source file code -- the unit the corpus was drawn in
    pos_i: np.ndarray  # (P,) int32, eligible positive pairs, i < j
    pos_j: np.ndarray

    @property
    def n(self) -> int:
        return len(self.names)


def load_corpus(centroids: Path, connectors: Path, states: Path, selection: Path, edges: Path):
    """Same inputs, same tokenizer and same eligibility rule as the published scripts."""
    cen = np.load(centroids, allow_pickle=False)
    names = [str(x) for x in cen["names"]]
    C = np.ascontiguousarray(cen["centroids"], dtype=np.float32)
    index = {n: i for i, n in enumerate(names)}
    n = len(names)

    area_of = {
        t["name"]: (t["module"].split(".")[1] if t["module"].count(".") else "")
        for t in json.loads(gzip.open(selection, "rt").read())["theorems"]
    }
    codes: dict[str, int] = {}
    area = np.fromiter(
        (codes.setdefault(area_of.get(nm, ""), len(codes)) for nm in names), np.int32, n
    )
    mod_of = {
        t["name"]: t["module"] for t in json.loads(gzip.open(selection, "rt").read())["theorems"]
    }
    mcodes: dict[str, int] = {}
    module = np.fromiter(
        (mcodes.setdefault(mod_of.get(nm, ""), len(mcodes)) for nm in names), np.int32, n
    )

    rare_sets = forward.rare_landmarks(set(names), edges)
    rare = _indicator(names, {k: v for k, v in rare_sets.items()})

    vocab_sets = vocabmod.vocabularies(states)
    vocab = _indicator(names, vocab_sets)
    vsize = np.asarray(vocab.sum(axis=1)).ravel().astype(np.float32)

    truth = {
        (min(index[a], index[b]), max(index[a], index[b]))
        for targets in json.loads(connectors.read_text()).values()
        for a, b in itertools.combinations(sorted(targets), 2)
        if a in index and b in index and not (rare_sets[a] & rare_sets[b])
    }
    pairs = np.array(sorted(truth), dtype=np.int32).reshape(-1, 2)
    return Corpus(names, C, rare, vocab, vsize, area, module, pairs[:, 0], pairs[:, 1])


def _indicator(names, sets) -> sp.csr_matrix:
    """Rows are theorems, columns are tokens; one shared column index for all rows."""
    col: dict[str, int] = {}
    indptr, indices = [0], []
    for nm in names:
        for tok in sorted(sets.get(nm, ())):
            indices.append(col.setdefault(tok, len(col)))
        indptr.append(len(indices))
    data = np.ones(len(indices), dtype=np.float32)
    return sp.csr_matrix(
        (data, np.asarray(indices, dtype=np.int32), np.asarray(indptr, dtype=np.int64)),
        shape=(len(names), max(len(col), 1)),
    )


def angles(C: np.ndarray, i: np.ndarray, j: np.ndarray, chunk: int = 16384) -> np.ndarray:
    """Angle in degrees for an explicit pair list, gathering in chunks.

    `C[i]` on a million-pair null draw is a 1,472-wide gather -- six gigabytes
    of temporary on this corpus, which on a small machine is all swap and made
    the null forty times slower than the matmul it wraps.
    """
    out = np.empty(len(i), dtype=np.float64)
    for a in range(0, len(i), chunk):
        b = slice(a, min(a + chunk, len(i)))
        dot = np.einsum("ij,ij->i", C[i[b]], C[j[b]], dtype=np.float32)
        out[b] = np.degrees(np.arccos(np.clip(dot, -1.0, 1.0)))
    return out


def pair_features(corpus: Corpus, i: np.ndarray, j: np.ndarray, threshold: float = 0.05):
    """Angle, eligibility, cross-area and low-overlap flags for an explicit pair list."""
    inter = np.asarray(corpus.vocab[i].multiply(corpus.vocab[j]).sum(axis=1)).ravel()
    union = corpus.vsize[i] + corpus.vsize[j] - inter
    jac = np.where(union > 0, inter / np.maximum(union, 1e-9), 0.0)
    shared_rare = np.asarray(corpus.rare[i].multiply(corpus.rare[j]).sum(axis=1)).ravel()
    return {
        "angle": angles(corpus.C, i, j),
        "eligible": shared_rare == 0,
        "cross": corpus.area[i] != corpus.area[j],
        "low": jac < threshold,
    }


def subset_masks(feat: dict) -> dict[str, np.ndarray]:
    base = feat["eligible"]
    return {
        "all eligible": base,
        "cross-area only": base & feat["cross"],
        "vocab<5%": base & feat["low"],
        "cross-area AND vocab<5%": base & feat["cross"] & feat["low"],
    }


def population_histograms(corpus: Corpus, sel: np.ndarray, threshold=0.05, block=256, log=None):
    """Angle histograms over the eligible upper triangle of `sel`, one per subset.

    `sel` is a sorted array of corpus row indices -- the subsampled corpus. Work
    is O(|sel|^2) in time and O(block * |sel|) in memory.
    """
    sel = np.asarray(sel, dtype=np.int32)
    m = len(sel)
    C, area, vsize = corpus.C[sel], corpus.area[sel], corpus.vsize[sel]
    V, R = corpus.vocab[sel], corpus.rare[sel]
    Vt, Rt = V.T.tocsc(), R.T.tocsc()

    hist = {k: np.zeros(NBINS, dtype=np.int64) for k in SUBSETS}
    for a0 in range(0, m, block):
        a1 = min(a0 + block, m)
        b = a1 - a0
        ang = np.degrees(np.arccos(np.clip(C[a0:a1] @ C.T, -1.0, 1.0)))

        keep = np.arange(m, dtype=np.int32)[None, :] > (a0 + np.arange(b, dtype=np.int32))[:, None]
        keep &= np.asarray((R[a0:a1] @ Rt).todense()) == 0

        inter = np.asarray((V[a0:a1] @ Vt).todense(), dtype=np.float32)
        union = vsize[a0:a1, None] + vsize[None, :] - inter
        np.divide(inter, np.maximum(union, 1e-9), out=inter)
        low = inter < threshold
        cross = area[a0:a1, None] != area[None, :]

        idx = np.minimum((ang * (1.0 / BINW)).astype(np.int32), NBINS - 1)
        for tag, mask in (
            ("all eligible", keep),
            ("cross-area only", keep & cross),
            ("vocab<5%", keep & low),
            ("cross-area AND vocab<5%", keep & cross & low),
        ):
            hist[tag] += np.bincount(idx[mask], minlength=NBINS)
        if log:
            log(a1, m)
    return hist


def bin_of(angle: np.ndarray) -> np.ndarray:
    return np.minimum((np.asarray(angle) * (1.0 / BINW)).astype(np.int32), NBINS - 1)


def auc_from_hist(hist: np.ndarray, pos_bins: np.ndarray) -> float:
    """Mann-Whitney AUC for 'smaller angle = positive', ties averaged within a bin.

    `hist` counts the whole population including the positives, which is what
    the blocked pass produces; the negatives are recovered by subtraction.
    """
    k = len(pos_bins)
    if k < 2:
        return float("nan")
    pos_hist = np.bincount(pos_bins, minlength=NBINS).astype(np.int64)
    neg_hist = hist - pos_hist
    n_neg = int(neg_hist.sum())
    if n_neg < 2:
        return float("nan")
    # cum[b] = negatives strictly below bin b
    cum = np.concatenate(([0], np.cumsum(neg_hist)))
    greater = n_neg - cum[pos_bins + 1]  # negatives in a strictly higher bin
    tied = neg_hist[pos_bins]
    return float((greater + 0.5 * tied).sum() / (k * n_neg))


class Population:
    """A subset's angle histogram, prepared for repeated AUC queries.

    `auc_from_hist` rebuilds a 360k-bin cumulative sum on every call, which is
    the whole cost of a 5,000-draw null. The population is fixed across draws,
    so its cumulative is built once and each draw only corrects it for its own
    k positives -- O(k log k) instead of O(bins).
    """

    def __init__(self, hist: np.ndarray):
        self.hist = np.asarray(hist, dtype=np.int64)
        self.cum = np.concatenate(([0], np.cumsum(self.hist)))  # cum[b] = count below bin b
        self.total = int(self.hist.sum())

    def auc(self, pos_bins: np.ndarray) -> float:
        k = len(pos_bins)
        n_neg = self.total - k
        if k < 2 or n_neg < 2:
            return float("nan")
        order = np.sort(pos_bins)
        pos_below = np.searchsorted(order, pos_bins, "left")
        pos_tied = np.searchsorted(order, pos_bins, "right") - pos_below
        neg_below = self.cum[pos_bins] - pos_below
        neg_tied = self.hist[pos_bins] - pos_tied
        greater = n_neg - neg_below - neg_tied
        return float((greater + 0.5 * neg_tied).sum() / (k * n_neg))
