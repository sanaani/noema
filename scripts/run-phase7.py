#!/usr/bin/env python3
"""run-phase7.py -- phase 7 parts 1 and 2: train the pickers, score the population, test.

Every setting is fixed in results/phase-7-lemma-selection/README.md. Encoder B
is frozen; every picker learns from the 2024 graph only. No 2026 data is read
until the population's positive flags are used in the analysis stage.

    train    GNN, GNN-noB, JEPA, JEPA-multi, CLASSIFIER, RERANK (each resumable:
             a finished model is loaded, not retrained)
    score    the four baselines and the pickers over the whole test population
    analyze  H1 (Holm across five pickers against the best baseline), H2 (GNN
             minus GNN-noB), the reported rows, RERANK, part 2 (H3) and the
             candidate lists parts 1 and 3 need for the Lean fit check

    scripts/run-phase7.py --vectors b-statements-2024.npz --b-model <phase 4 out> \
        --predictor predictor.pt --population <build-phase7-pairs out> --out <dir>
    ... --smoke    tiny CPU run: a slice of everything, one epoch
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import re
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
E24 = ROOT / "results/phase-1-recognition/link-graph-v1/edges.jsonl.gz"
SEED = 20260930
CAP = 64
EPOCHS = 20
LR = 1e-3
HELD = 0.05
SUPERVISION = 0.10
D = 256
BOOT = 2000
GENERIC = 200
PRIMARY = ("GNN", "JEPA", "JEPA-multi", "CLASSIFIER", "ENSEMBLE")
BASELINES = ("NEAREST", "POPULAR", "GRAPH", "WORDS")
TOPK = (1_000, 10_000, 100_000)
NOVEL_TOP = 100_000
NOVEL_K = 10_000
RERANK_EXAMPLES = 2_000_000
RERANK_LR = 3e-4
RERANK_BATCH = 64
RERANK_SIDE = 255
RERANK_TOP = 10_000
# analyze-forward-vocabulary.py's tokenizer, copied so the GPU task needs no package
TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_.']*")


def _load(stem: str, rel: str):
    spec = importlib.util.spec_from_file_location(stem, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# The 2024 graph
# ---------------------------------------------------------------------------


class Graph:
    """Nodes are 2024 theorems holding a vector, in the vector file's order."""

    def __init__(self, names: list[str], limit: int | None):
        self.names = names
        self.row = {n: i for i, n in enumerate(names)}
        n = len(names)
        self.indeg = np.zeros(n, np.int64)  # citations from every 2024 theorem (phase 6's deg)
        self.module = np.array([""] * n, dtype=object)
        citer, deps_full, mods = [], [], []
        with gzip.open(E24, "rt") as f:
            for k, r in enumerate(map(json.loads, f)):
                if limit and k >= limit:
                    break
                deps = set(r.get("deps", ())) - {r["theorem"]}
                ids = np.array(sorted(self.row[d] for d in deps if d in self.row), np.int64)
                self.indeg[ids] += 1
                t = self.row.get(r["theorem"], -1)
                if t >= 0:
                    self.module[t] = r["module"]
                citer.append(t)
                deps_full.append(ids)
                mods.append(r["module"])
        self.citer = np.array(citer, np.int64)  # -1 where the citing theorem has no vector
        self.deps = deps_full
        self.mods = np.array(mods, dtype=object)
        self.outdeg = np.zeros(n, np.int64)
        for t, ids in zip(self.citer, self.deps, strict=True):
            if t >= 0:
                self.outdeg[t] = len(ids)
        area = [m.split(".")[1] if m.count(".") else "" for m in self.module]
        codes: dict[str, int] = {}
        self.area = np.array([codes.setdefault(a, len(codes)) for a in area], np.int64)
        self.n_areas = len(codes)

    def capped(self, ids: np.ndarray) -> np.ndarray:
        """Phase 6's rule: at most 64, keeping the rarest by 2024 in-degree."""
        order = np.lexsort((ids, self.indeg[ids]))
        return ids[order][:CAP]

    def cocite_codes(self, which: np.ndarray | None = None) -> np.ndarray:
        """Sorted codes i * N + j (i < j) of pairs some (selected) 2024 theorem cites together."""
        n = len(self.names)
        chunks = []
        for k, ids in enumerate(self.deps):
            if (which is not None and not which[k]) or len(ids) < 2:
                continue
            i, j = np.triu_indices(len(ids), 1)
            chunks.append(ids[i] * n + ids[j])
        return np.unique(np.concatenate(chunks)) if chunks else np.empty(0, np.int64)

    def adjacency(self, which: np.ndarray | None, dev) -> torch.Tensor:
        """Row-normalised undirected citation adjacency (mean aggregation), sparse CSR."""
        n = len(self.names)
        rows, cols = [], []
        for k, (t, ids) in enumerate(zip(self.citer, self.deps, strict=True)):
            if t < 0 or len(ids) == 0 or (which is not None and not which[k]):
                continue
            rows.append(np.full(len(ids), t))
            cols.append(ids)
        r = np.concatenate(rows) if rows else np.empty(0, np.int64)
        c = np.concatenate(cols) if cols else np.empty(0, np.int64)
        A = sp.coo_matrix((np.ones(len(r), np.float32), (r, c)), shape=(n, n)).tocsr()
        A = ((A + A.T) > 0).astype(np.float32).tocsr()
        deg = np.asarray(A.sum(1)).ravel()
        A = sp.diags(1.0 / np.maximum(deg, 1)).astype(np.float32) @ A
        A = A.tocsr()
        return torch.sparse_csr_tensor(
            torch.from_numpy(A.indptr.astype(np.int64)),
            torch.from_numpy(A.indices.astype(np.int64)),
            torch.from_numpy(A.data.astype(np.float32)), size=(n, n),
        ).to(dev)  # fmt: skip

    def undirected_scipy(self) -> sp.csr_matrix:
        n = len(self.names)
        rows, cols = [], []
        for t, ids in zip(self.citer, self.deps, strict=True):
            if t >= 0 and len(ids):
                rows.append(np.full(len(ids), t))
                cols.append(ids)
        r, c = np.concatenate(rows), np.concatenate(cols)
        A = sp.coo_matrix((np.ones(len(r), np.float32), (r, c)), shape=(n, n)).tocsr()
        return ((A + A.T) > 0).astype(np.float32).tocsr()


def in_sorted(codes: torch.Tensor, q: torch.Tensor) -> torch.Tensor:
    if len(codes) == 0:
        return torch.zeros_like(q, dtype=torch.bool)
    k = torch.searchsorted(codes, q).clamp(max=len(codes) - 1)
    return codes[k] == q


def pair_code(a: torch.Tensor, b: torch.Tensor, n: int) -> torch.Tensor:
    return torch.minimum(a, b) * n + torch.maximum(a, b)


def file_split(g: Graph, rng) -> tuple[set, set]:
    """Files permuted once: the first 5% are held out, the first 10% are supervision."""
    files = np.unique(g.mods)
    perm = rng.permutation(files)
    held = set(perm[: int(round(HELD * len(files)))])
    sup = set(perm[: int(round(SUPERVISION * len(files)))])
    return held, sup


# ---------------------------------------------------------------------------
# Pickers
# ---------------------------------------------------------------------------


class SAGE(nn.Module):
    def __init__(self, d_in: int, n_areas: int = 0):
        super().__init__()
        self.area = nn.Embedding(n_areas, 32) if n_areas else None
        d0 = d_in + (32 if n_areas else 0)
        self.s1, self.n1 = nn.Linear(d0, 256), nn.Linear(d0, 256)
        self.s2, self.n2 = nn.Linear(256, 256), nn.Linear(256, 256)

    def forward(self, x, A, area=None):
        if self.area is not None:
            x = torch.cat([x, self.area(area)], -1)
        h = F.gelu(self.s1(x) + self.n1(torch.sparse.mm(A, x)))
        return self.s2(h) + self.n2(torch.sparse.mm(A, h))


class DeepSets(nn.Module):
    """Phase 6's architecture; `heads` > 1 gives JEPA-multi."""

    def __init__(self, heads: int = 1):
        super().__init__()
        self.heads = heads
        self.phi = nn.Sequential(nn.Linear(D, 512), nn.GELU(), nn.Linear(512, 512), nn.GELU())
        self.rho = nn.Sequential(nn.Linear(1024, 512), nn.GELU(), nn.Linear(512, D * heads))

    def forward(self, x, mask):
        h = self.phi(x)
        m = mask.unsqueeze(-1)
        mean = (h * m).sum(1) / m.sum(1).clamp(min=1)
        mx = h.masked_fill(~m, float("-inf")).max(1).values
        out = self.rho(torch.cat([mean, mx], -1)).view(-1, self.heads, D)
        return F.normalize(out, dim=-1)


class PairMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(3 * D, 512), nn.GELU(), nn.Linear(512, 256), nn.GELU(),
                                 nn.Linear(256, 1))  # fmt: skip

    def forward(self, a, b):
        return self.net(torch.cat([a + b, a * b, (a - b).abs()], -1)).squeeze(-1)


def epoch_loop(name, out, model, opt, epochs, run_epoch, held_loss):
    """Shared resumable loop: keep the epoch with the lowest held-out loss."""
    best_path, state_path = out / f"{name}.pt", out / f"{name}.state.pt"
    if (out / f"{name}.done").exists():
        model.load_state_dict(torch.load(best_path, map_location="cpu"))
        return json.loads((out / f"{name}.done").read_text())
    curve, best, best_epoch, start = [], float("inf"), -1, 1
    if state_path.exists():
        st = torch.load(state_path, weights_only=False, map_location="cpu")
        model.load_state_dict(st["model"])
        opt.load_state_dict(st["opt"])
        torch.set_rng_state(st["torch_rng"])
        curve, best, best_epoch, start = st["curve"], st["best"], st["best_epoch"], st["epoch"] + 1
        log(f"{name}: resuming after epoch {st['epoch']}")
    t0 = time.time()
    for epoch in range(start, epochs + 1):
        model.train()
        tr = run_epoch(epoch)
        model.eval()
        with torch.no_grad():
            va = held_loss()
        curve.append({"epoch": epoch, "train": tr, "held": va})
        log(f"{name} epoch {epoch:2d} train {tr:.4f} held {va:.4f} {time.time() - t0:.0f}s")
        if va < best:
            best, best_epoch = va, epoch
            torch.save(model.state_dict(), best_path)
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(),
                    "torch_rng": torch.get_rng_state(), "curve": curve, "best": best,
                    "best_epoch": best_epoch, "epoch": epoch}, state_path)  # fmt: skip
    model.load_state_dict(torch.load(best_path, map_location="cpu"))
    summary = {"chosen_epoch": best_epoch, "held_loss": best, "curve": curve}
    (out / f"{name}.done").write_text(json.dumps(summary))
    return summary


def train_gnn(ctx, name: str, use_b: bool):
    g, dev, out, epochs = ctx["g"], ctx["dev"], ctx["out"], ctx["epochs"]
    n = len(g.names)
    rng = np.random.default_rng(SEED + (1 if use_b else 2))
    torch.manual_seed(SEED + (1 if use_b else 2))
    held_files, sup_files = ctx["held_files"], ctx["sup_files"]
    is_sup = np.array([m in sup_files for m in g.mods])
    is_held = np.array([m in held_files for m in g.mods])
    mp_codes = torch.from_numpy(g.cocite_codes(~is_sup)).to(dev)

    def sup_pairs(sel):
        chunks = []
        for k in np.where(sel)[0]:
            ids = np.sort(g.capped(g.deps[k]))
            if len(ids) < 2:
                continue
            i, j = np.triu_indices(len(ids), 1)
            chunks.append(np.stack([ids[i], ids[j]], 1))
        p = torch.from_numpy(np.unique(np.concatenate(chunks), axis=0)).to(dev)
        keep = ~in_sorted(mp_codes, pair_code(p[:, 0], p[:, 1], n))
        return p[keep]

    tr_pos, va_pos = sup_pairs(is_sup & ~is_held), sup_pairs(is_sup & is_held)
    cited = torch.from_numpy(np.where(g.indeg > 0)[0]).to(dev)
    gen = torch.Generator(device=dev).manual_seed(SEED)
    va_neg = cited[torch.randint(len(cited), (len(va_pos),), generator=gen, device=dev)]
    A_mp = g.adjacency(~is_sup, dev)
    x, area = features(ctx, use_b)
    model = SAGE(x.shape[1], g.n_areas if not use_b else 0).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    log(f"{name}: supervision positives train {len(tr_pos):,} held {len(va_pos):,}")
    batch = 4096

    def loss_of(z, pos, neg_b):
        s_pos = (z[pos[:, 0]] * z[pos[:, 1]]).sum(-1)
        s_neg = (z[pos[:, 0]] * z[neg_b]).sum(-1)
        return 0.5 * (
            F.binary_cross_entropy_with_logits(s_pos, torch.ones_like(s_pos))
            + F.binary_cross_entropy_with_logits(s_neg, torch.zeros_like(s_neg))
        )

    def run_epoch(epoch):
        perm = torch.from_numpy(rng.permutation(len(tr_pos))).to(dev)
        total = 0.0
        for a in range(0, len(perm), batch):
            p = tr_pos[perm[a : a + batch]]
            neg = cited[torch.randint(len(cited), (len(p),), device=dev)]
            z = model(x, A_mp, area)
            loss = loss_of(z, p, neg)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += float(loss) * len(p)
        return total / len(tr_pos)

    def held_loss():
        z = model(x, A_mp, area)
        return float(loss_of(z, va_pos, va_neg))

    summary = epoch_loop(name, out, model, opt, epochs, run_epoch, held_loss)
    summary.update(train_positives=len(tr_pos), held_positives=len(va_pos))
    model.eval()
    with torch.no_grad():
        z = model(x, ctx["A_full"], area)
    return summary, z


def features(ctx, use_b: bool):
    g, dev = ctx["g"], ctx["dev"]
    if use_b:
        return ctx["V"], None
    f = np.stack([np.log1p(g.indeg), np.log1p(g.outdeg)], 1).astype(np.float32)
    f = (f - f.mean(0)) / f.std(0).clip(min=1e-6)
    return torch.from_numpy(f).to(dev), torch.from_numpy(g.area).to(dev)


def training_sets(ctx):
    """Training theorems (citing >= 2 vector-bearing theorems), capped sets, held flag."""
    g = ctx["g"]
    sets, held = [], []
    for k, ids in enumerate(g.deps):
        if g.citer[k] < 0 or len(ids) < 2:
            continue
        sets.append(g.capped(ids))
        held.append(g.mods[k] in ctx["held_files"])
    idx = np.zeros((len(sets), CAP), np.int64)
    ln = np.array([len(s) for s in sets], np.int64)
    for r, s in enumerate(sets):
        idx[r, : len(s)] = s
    return idx, ln, np.array(held)


def train_jepa(ctx, name: str, heads: int):
    dev, out, epochs, V = ctx["dev"], ctx["out"], ctx["epochs"], ctx["V"]
    torch.manual_seed(SEED + 10 + heads)
    rng = np.random.default_rng(SEED + 10 + heads)
    idx, ln, held = ctx["sets"]
    idx_t, ln_t = torch.from_numpy(idx).to(dev), torch.from_numpy(ln).to(dev)
    tr_rows, va_rows = np.where(~held)[0], np.where(held)[0]
    model = DeepSets(heads).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    batch = 256

    def masked(rows, gen):
        b = torch.from_numpy(rows).to(dev)
        n = ln_t[b]
        keys = torch.rand(len(b), CAP, generator=gen, device=dev)
        keys = keys.masked_fill(torch.arange(CAP, device=dev)[None] >= n[:, None], 2.0)
        perm = keys.argsort(1)
        members = idx_t[b].gather(1, perm)
        hidden = members[:, 0]
        k = (torch.rand(len(b), generator=gen, device=dev) * (n - 1)).long() + 1  # 1..n-1
        pos = torch.arange(CAP, device=dev)[None]
        mask = (pos >= 1) & (pos <= k[:, None])
        return V[members], mask, V[hidden]

    def loss_of(pred, target):
        per = 1 - (pred * target[:, None]).sum(-1)  # (b, heads)
        if heads == 1:
            return per[:, 0].mean()
        return (0.95 * per.min(1).values + 0.05 * per.mean(1)).mean()

    gen = torch.Generator(device=dev).manual_seed(SEED + 20 + heads)

    def run_epoch(epoch):
        total = 0.0
        perm = rng.permutation(tr_rows)
        for a in range(0, len(perm), batch):
            x, m, y = masked(perm[a : a + batch], gen)
            loss = loss_of(model(x, m), y)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += float(loss) * len(x)
        return total / len(tr_rows)

    def held_loss():
        vgen = torch.Generator(device=dev).manual_seed(SEED)
        total = 0.0
        for a in range(0, len(va_rows), 4096):
            x, m, y = masked(va_rows[a : a + 4096], vgen)
            total += float(loss_of(model(x, m), y)) * len(x)
        return total / len(va_rows)

    summary = epoch_loop(name, out, model, opt, epochs, run_epoch, held_loss)
    return summary, model


class NegSampler:
    """CLASSIFIER's sampler: a theorem uniformly, a pair from its capped set, three negatives."""

    def __init__(self, ctx):
        g, dev, V = ctx["g"], ctx["dev"], ctx["V"]
        self.dev, self.n = dev, len(g.names)
        idx, ln, held = ctx["sets"]
        self.idx, self.ln = torch.from_numpy(idx).to(dev), torch.from_numpy(ln).to(dev)
        self.held = held
        self.cocited = ctx["co24"]
        cited = np.where(g.indeg > 0)[0]
        self.cited = torch.from_numpy(cited).to(dev)
        # deciles of in-degree among cited theorems
        edges = np.quantile(g.indeg[cited], np.linspace(0, 1, 11)[1:-1])
        dec = np.searchsorted(edges, g.indeg, side="right")
        self.decile = torch.from_numpy(dec).to(dev)
        order = np.argsort(dec[cited], kind="stable")
        self.by_dec = torch.from_numpy(cited[order]).to(dev)
        counts = np.bincount(dec[cited], minlength=10)
        self.dec_start = torch.from_numpy(np.concatenate([[0], np.cumsum(counts)[:-1]])).to(dev)
        self.dec_count = torch.from_numpy(counts).to(dev)
        self.nn50 = nearest50(V, dev)

    def draw(self, rows: np.ndarray, gen):
        dev = self.dev
        b = torch.from_numpy(rows).to(dev)
        n = self.ln[b]
        i = (torch.rand(len(b), generator=gen, device=dev) * n).long()
        j = (torch.rand(len(b), generator=gen, device=dev) * (n - 1)).long()
        j = j + (j >= i).long()
        a = self.idx[b].gather(1, i[:, None])[:, 0]
        p = self.idx[b].gather(1, j[:, None])[:, 0]

        def rnd():
            return self.cited[torch.randint(len(self.cited), (len(a),), generator=gen, device=dev)]

        def look():
            k = torch.randint(50, (len(a),), generator=gen, device=dev)
            return self.nn50[a, k]

        def pop():
            d = self.decile[p]
            u = torch.rand(len(a), generator=gen, device=dev)
            return self.by_dec[self.dec_start[d] + (u * self.dec_count[d]).long()]

        negs, keep = [], torch.ones(len(a), dtype=torch.bool, device=dev)
        for fn in (rnd, look, pop):
            x = fn()
            for _ in range(3):  # redraw a negative co-cited with a in 2024
                bad = in_sorted(self.cocited, pair_code(a, x, self.n)) | (x == a)
                if not bad.any():
                    break
                x = torch.where(bad, fn(), x)
            bad = in_sorted(self.cocited, pair_code(a, x, self.n)) | (x == a)
            keep &= ~bad
            negs.append(x)
        return a[keep], p[keep], [x[keep] for x in negs]


def nearest50(V: torch.Tensor, dev) -> torch.Tensor:
    n = len(V)
    blk = 4096 if dev.type == "cuda" else 512
    out = torch.empty(n, 50, dtype=torch.long, device=dev)
    for a in range(0, n, blk):
        s = V[a : a + blk] @ V.T
        s[torch.arange(s.shape[0], device=dev), torch.arange(a, a + s.shape[0], device=dev)] = -2
        out[a : a + blk] = s.topk(50, dim=1).indices
    return out


def train_classifier(ctx, sampler: NegSampler):
    dev, out, epochs, V = ctx["dev"], ctx["out"], ctx["epochs"], ctx["V"]
    torch.manual_seed(SEED + 30)
    rng = np.random.default_rng(SEED + 30)
    held = sampler.held
    tr_rows, va_rows = np.where(~held)[0], np.where(held)[0]
    model = PairMLP().to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    gen = torch.Generator(device=dev).manual_seed(SEED + 31)
    batch = 256

    def loss_on(a, p, negs):
        s_pos = model(V[a], V[p])
        loss = F.binary_cross_entropy_with_logits(s_pos, torch.ones_like(s_pos))
        for x in negs:
            s = model(V[a], V[x])
            loss = loss + F.binary_cross_entropy_with_logits(s, torch.zeros_like(s))
        return loss / 4

    vgen = torch.Generator(device=dev).manual_seed(SEED)
    held_draw = sampler.draw(va_rows, vgen)

    def run_epoch(epoch):
        total, count = 0.0, 0
        perm = rng.permutation(tr_rows)
        for s in range(0, len(perm), batch):
            a, p, negs = sampler.draw(perm[s : s + batch], gen)
            loss = loss_on(a, p, negs)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += float(loss) * len(a)
            count += len(a)
        return total / max(count, 1)

    def held_loss():
        a, p, negs = held_draw
        return float(loss_on(a, p, negs))

    summary = epoch_loop("CLASSIFIER", out, model, opt, epochs, run_epoch, held_loss)
    return summary, model


# ---------------------------------------------------------------------------
# RERANK: a cross-encoder initialised from B
# ---------------------------------------------------------------------------


class Rerank(nn.Module):
    def __init__(self, enc):
        super().__init__()
        self.enc = enc
        self.head = nn.Linear(D, 1)

    def forward(self, ids):
        return self.head(self.enc.pooled(ids)).squeeze(-1)


def rerank_tokens(ctx, texts: list[str]):
    tr = ctx["tr"]
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(ctx["b_model"] / "b-tokenizer.json"))
    ids = np.zeros((len(texts), RERANK_SIDE), np.int16)
    ln = np.zeros(len(texts), np.int64)
    for a in range(0, len(texts), 20_000):
        for r, e in enumerate(tok.encode_batch(texts[a : a + 20_000])):
            body = e.ids[:RERANK_SIDE]
            ids[a + r, : len(body)] = body
            ln[a + r] = len(body)
    assert tr.PAD == 0
    return torch.from_numpy(ids.astype(np.int64)), torch.from_numpy(ln)


def join(ctx, toks, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """BOS a EOS b, each side at most 255 tokens, padded to the batch's longest."""
    tr = ctx["tr"]
    ids, ln = toks
    a, b = a.cpu(), b.cpu()
    la, lb = ln[a], ln[b]
    total = 2 + la + lb
    L = int(total.max())
    out = torch.zeros(len(a), L, dtype=torch.long)
    pos = torch.arange(RERANK_SIDE)
    for r in range(len(a)):
        x, y = int(la[r]), int(lb[r])
        out[r, 0] = tr.BOS
        out[r, 1 : 1 + x] = ids[a[r], :x]
        out[r, 1 + x] = tr.EOS
        out[r, 2 + x : 2 + x + y] = ids[b[r], :y]
    del pos
    return out.to(ctx["dev"])


def train_rerank(ctx, sampler: NegSampler, toks):
    dev, out, tr = ctx["dev"], ctx["out"], ctx["tr"]
    cfg = tr.B_CFG
    enc = tr.StateEncoder(cfg["vocab"], cfg["d"], cfg["heads"], cfg["layers"], cfg["ff"],
                          cfg["dropout"], cfg["max_len"])  # fmt: skip
    enc.load_state_dict(torch.load(ctx["b_model"] / "b-model.pt", map_location="cpu"))
    model = Rerank(enc).to(dev)
    if (out / "RERANK.done").exists():
        model.load_state_dict(torch.load(out / "RERANK.pt", map_location="cpu"))
        model.eval()
        return json.loads((out / "RERANK.done").read_text()), model
    torch.manual_seed(SEED + 40)
    rng = np.random.default_rng(SEED + 40)
    gen = torch.Generator(device=dev).manual_seed(SEED + 41)
    opt = torch.optim.AdamW(model.parameters(), lr=RERANK_LR)
    groups = RERANK_BATCH // 4
    examples = ctx["rerank_examples"]
    tr_rows = np.where(~sampler.held)[0]
    steps = examples // RERANK_BATCH
    amp = dev.type == "cuda"
    model.train()
    t0, run = time.time(), 0.0
    for step in range(steps):
        rows = rng.choice(tr_rows, groups, replace=False)
        a, p, negs = sampler.draw(rows, gen)
        left = torch.cat([a, a, a, a])
        right = torch.cat([p, *negs])
        y = torch.cat([torch.ones(len(a)), torch.zeros(3 * len(a))]).to(dev)
        ids = join(ctx, toks, left, right)
        with torch.autocast(dev.type, dtype=torch.bfloat16, enabled=amp):
            s = model(ids)
        loss = F.binary_cross_entropy_with_logits(s.float(), y)
        opt.zero_grad()
        loss.backward()
        opt.step()
        run = 0.98 * run + 0.02 * float(loss) if step else float(loss)
        if step % 1000 == 0:
            log(f"RERANK step {step:,}/{steps:,} loss {run:.4f} {time.time() - t0:.0f}s")
    torch.save(model.state_dict(), out / "RERANK.pt")
    summary = {"steps": steps, "examples": steps * RERANK_BATCH, "final_running_loss": run}
    (out / "RERANK.done").write_text(json.dumps(summary))
    model.eval()
    return summary, model


def rerank_score(ctx, model, toks, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    dev = ctx["dev"]
    out = torch.empty(len(a), device=dev)
    amp = dev.type == "cuda"
    with torch.no_grad():
        for s in range(0, len(a), 256):
            x, y = a[s : s + 256], b[s : s + 256]
            with torch.autocast(dev.type, dtype=torch.bfloat16, enabled=amp):
                s1 = model(join(ctx, toks, x, y)).float()
                s2 = model(join(ctx, toks, y, x)).float()
            out[s : s + 256] = (s1 + s2) / 2
    return out


# ---------------------------------------------------------------------------
# Scoring the population
# ---------------------------------------------------------------------------


def chunked(n: int, size: int = 1 << 22):
    for a in range(0, n, size):
        yield slice(a, min(a + size, n))


def score_pairs(fn, A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    out = torch.empty(len(A), device=A.device)
    with torch.no_grad():
        for s in chunked(len(A), 1 << 18):
            out[s] = fn(A[s], B[s])
    return out


def sparse_block_scores(Xrows: sp.csr_matrix, Ycols: sp.csr_matrix, pi: np.ndarray,
                        pj: np.ndarray, kind: str, sizes=None) -> np.ndarray:  # fmt: skip
    """AA or Jaccard for pairs sorted by i, one corpus row block at a time."""
    out = np.empty(len(pi), np.float32)
    YT = Ycols.T.tocsc()
    starts = np.searchsorted(pi, np.arange(0, Xrows.shape[0] + 1024, 1024))
    for bi, a0 in enumerate(range(0, Xrows.shape[0], 1024)):
        s, e = starts[bi], starts[bi + 1]
        if s == e:
            continue
        M = np.asarray((Xrows[a0 : a0 + 1024] @ YT).todense(), dtype=np.float32)
        r, c = pi[s:e] - a0, pj[s:e]
        v = M[r, c]
        if kind == "jaccard":
            union = sizes[pi[s:e]] + sizes[c] - v
            v = np.where(union > 0, v / np.maximum(union, 1e-9), 0.0)
        out[s:e] = v
    return out


def placements(score: torch.Tensor, pos: torch.Tensor, within: torch.Tensor | None = None):
    """Per positive, the share of negatives it scores above (ties half); and its index order."""
    sel = torch.ones_like(pos) if within is None else within
    neg = score[sel & ~pos].sort().values
    sp_ = score[sel & pos]
    lt = torch.searchsorted(neg, sp_, right=False)
    le = torch.searchsorted(neg, sp_, right=True)
    return ((lt + 0.5 * (le - lt)).double() / max(len(neg), 1)).cpu().numpy()


def avg_rank(x: torch.Tensor) -> torch.Tensor:
    """Average-tie percentile ranks in [0, 1]."""
    s = x.sort().values
    lt = torch.searchsorted(s, x, right=False).double()
    le = torch.searchsorted(s, x, right=True).double()
    return (lt + le - 1) / 2 / max(len(x) - 1, 1)  # float64: 57.6M ranks need > 24 bits


def topk_hits(score: torch.Tensor, pos: torch.Tensor, ks) -> dict:
    k = min(max(ks), len(score))
    top = score.topk(k).indices
    hits = pos[top].cumsum(0)
    return {str(q): int(hits[min(q, k) - 1]) for q in ks}


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def boot_weights(pi: np.ndarray, pj: np.ndarray, rng, draws: int) -> np.ndarray:
    ends = np.unique(np.concatenate([pi, pj]))
    slot = np.searchsorted(ends, np.stack([pi, pj]))
    mults = rng.multinomial(len(ends), np.full(len(ends), 1 / len(ends)), size=draws)
    return (mults[:, slot[0]] * mults[:, slot[1]]).astype(np.float64)


def boot_diff(u: np.ndarray, w: np.ndarray) -> dict:
    d = (u[None] * w).sum(1) / np.maximum(w.sum(1), 1)
    lo, hi = np.percentile(d, [2.5, 97.5])
    return {"difference": float(u.mean()), "ci95": [float(lo), float(hi)],
            "p_one_sided": float((d <= 0).mean())}  # fmt: skip


def holm(ps: dict[str, float], alpha: float = 0.05) -> dict[str, bool]:
    order = sorted(ps, key=ps.get)
    out, m, stop = {}, len(ps), False
    for k, name in enumerate(order):
        ok = not stop and ps[name] <= alpha / (m - k)
        stop |= not ok
        out[name] = ok
    return out


def verdict3(ci, up, zero, down) -> str:
    return up if ci[0] > 0 else (down if ci[1] < 0 else zero)


# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--vectors", type=Path, required=True)
    ap.add_argument("--b-model", type=Path, required=True)
    ap.add_argument("--predictor", type=Path, required=True)
    ap.add_argument("--population", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        global NOVEL_TOP, NOVEL_K, RERANK_TOP
        NOVEL_TOP, NOVEL_K, RERANK_TOP = 2_000, 200, 500
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log(f"device {dev}")
    rng = np.random.default_rng(SEED)
    torch.manual_seed(SEED)

    z = np.load(args.vectors)
    names = [str(x) for x in z["names"]]
    V = torch.from_numpy(z["vectors"].astype(np.float32)).to(dev)
    g = Graph(names, 20_000 if args.smoke else None)
    log(f"graph: {len(names):,} nodes, {sum(len(d) for d in g.deps):,} citations")
    held_files, sup_files = file_split(g, rng)
    ctx = {
        "g": g, "dev": dev, "out": out, "V": V, "held_files": held_files, "sup_files": sup_files,
        "epochs": 1 if args.smoke else EPOCHS, "b_model": args.b_model,
        "tr": _load("tr", "scripts/train-encoders-gpu.py"),
        "rerank_examples": 2_048 if args.smoke else RERANK_EXAMPLES,
    }  # fmt: skip
    ctx["co24"] = torch.from_numpy(g.cocite_codes()).to(dev)
    ctx["A_full"] = g.adjacency(None, dev)
    ctx["sets"] = training_sets(ctx)
    log(f"co-cited 2024 pairs {len(ctx['co24']):,} | training theorems {len(ctx['sets'][1]):,} "
        f"(held {ctx['sets'][2].sum():,})")  # fmt: skip

    # ---- train ----
    report: dict = {"seed": SEED, "device": str(dev), "smoke": args.smoke, "training": {}}
    s_gnn, Z_gnn = train_gnn(ctx, "GNN", True)
    s_gnn0, Z_gnn0 = train_gnn(ctx, "GNN-noB", False)
    s_j1, jepa1 = train_jepa(ctx, "JEPA", 1)
    s_j5, jepa5 = train_jepa(ctx, "JEPA-multi", 5)
    sampler = NegSampler(ctx)
    s_cls, cls = train_classifier(ctx, sampler)
    with gzip.open(args.vectors.with_suffix(".texts.json.gz"), "rt") as f:
        texts = json.load(f)
    toks = rerank_tokens(ctx, texts)
    del texts
    s_rr, rerank = train_rerank(ctx, sampler, toks)
    report["training"] = {"GNN": s_gnn, "GNN-noB": s_gnn0, "JEPA": s_j1, "JEPA-multi": s_j5,
                          "CLASSIFIER": s_cls, "RERANK": s_rr}  # fmt: skip

    # ---- the population ----
    P = args.population
    cnames = json.loads((P / "names.json").read_text())
    crow = np.array([g.row[nm] for nm in cnames], np.int64)
    pi_c = np.fromfile(P / "i.int32", dtype=np.int32).astype(np.int64)
    pj_c = np.fromfile(P / "j.int32", dtype=np.int32).astype(np.int64)
    flags = np.fromfile(P / "flags.uint8", dtype=np.uint8)
    if args.smoke:
        m = 2_000_000
        pi_c, pj_c, flags = pi_c[:m], pj_c[:m], flags[:m]
    A = torch.from_numpy(crow[pi_c]).to(dev)
    B = torch.from_numpy(crow[pj_c]).to(dev)
    pos = torch.from_numpy((flags & 1).astype(bool)).to(dev)
    gen_ = torch.from_numpy(((flags >> 1) & 1).astype(bool)).to(dev)
    pool = torch.from_numpy(((flags >> 2) & 1).astype(bool)).to(dev)
    log(f"population {len(A):,} pairs, {int(pos.sum()):,} positives")

    # ---- score ----
    S: dict[str, torch.Tensor] = {}
    S["NEAREST"] = score_pairs(lambda a, b: (V[a] * V[b]).sum(-1), A, B)
    deg_t = torch.from_numpy(g.indeg).to(dev).float()
    S["POPULAR"] = score_pairs(lambda a, b: torch.log1p(deg_t[a]) + torch.log1p(deg_t[b]), A, B)
    Au = g.undirected_scipy()
    udeg = np.asarray(Au.sum(1)).ravel()
    Ac = Au[crow]
    X = sp.diags(1.0 / np.log(np.maximum(udeg, 2))).astype(np.float32)
    S["GRAPH"] = torch.from_numpy(
        sparse_block_scores((Ac @ X).tocsr(), Ac, pi_c, pj_c, "aa")).to(dev)  # fmt: skip
    log("GRAPH scored")
    with gzip.open(args.vectors.with_suffix(".texts.json.gz"), "rt") as f:
        texts = json.load(f)
    ctexts = [texts[r] for r in crow]
    del texts
    col: dict[str, int] = {}
    indptr, ind = [0], []
    for t in ctexts:
        for tok in sorted(set(TOKEN.findall(t))):
            ind.append(col.setdefault(tok, len(col)))
        indptr.append(len(ind))
    W = sp.csr_matrix((np.ones(len(ind), np.float32), ind, indptr), shape=(len(ctexts), len(col)))
    wsize = np.asarray(W.sum(1)).ravel().astype(np.float32)
    S["WORDS"] = torch.from_numpy(
        sparse_block_scores(W, W, pi_c, pj_c, "jaccard", wsize)).to(dev)  # fmt: skip
    log("WORDS scored")
    S["GNN"] = score_pairs(lambda a, b: (Z_gnn[a] * Z_gnn[b]).sum(-1), A, B)
    S["GNN-noB"] = score_pairs(lambda a, b: (Z_gnn0[a] * Z_gnn0[b]).sum(-1), A, B)
    single = torch.ones(1, 1, dtype=torch.bool, device=dev)
    with torch.no_grad():
        P1 = torch.cat([jepa1(V[s][:, None], single.expand(len(V[s]), 1))
                        for s in chunked(len(V), 65536)])  # (n, 1, D)  # fmt: skip
        P5 = torch.cat([jepa5(V[s][:, None], single.expand(len(V[s]), 1))
                        for s in chunked(len(V), 65536)])  # (n, 5, D)  # fmt: skip

    def jepa_score(Pm):
        def fn(a, b):
            ab = (Pm[a] * V[b][:, None]).sum(-1).max(1).values
            ba = (Pm[b] * V[a][:, None]).sum(-1).max(1).values
            return (ab + ba) / 2

        return fn

    S["JEPA"] = score_pairs(jepa_score(P1), A, B)
    S["JEPA-multi"] = score_pairs(jepa_score(P5), A, B)
    S["CLASSIFIER"] = score_pairs(lambda a, b: cls(V[a], V[b]), A, B)
    S["ENSEMBLE"] = sum(avg_rank(S[k]) for k in ("GNN", "JEPA", "JEPA-multi", "CLASSIFIER")) / 4
    log("all methods scored")

    # ---- analyze: part 1 ----
    pos_np = pos.cpu().numpy()
    pi_pos, pj_pos = pi_c[pos_np], pj_c[pos_np]
    draws = 50 if args.smoke else BOOT
    w = boot_weights(pi_pos, pj_pos, np.random.default_rng(SEED), draws)
    U = {k: placements(v, pos) for k, v in S.items()}
    auc = {k: float(u.mean()) for k, u in U.items()}
    best_base = max(BASELINES, key=auc.get)
    h1 = {}
    for k in PRIMARY:
        h1[k] = {"auc": auc[k], **boot_diff(U[k] - U[best_base], w)}
    passed = holm({k: h1[k]["p_one_sided"] for k in PRIMARY})
    for k in PRIMARY:
        h1[k]["passes_holm"] = passed[k]
    winners = [k for k in PRIMARY if passed[k]]
    if winners:
        v1 = "a 2024 picker beats every baseline"
    elif all(h1[k]["ci95"][1] < 0 for k in PRIMARY):
        v1 = "the baselines do better"
    else:
        v1 = "no picker beats the baselines"
    winner = max(winners or PRIMARY, key=auc.get)
    h2 = boot_diff(U["GNN"] - U["GNN-noB"], w)
    h2["verdict"] = verdict3(h2["ci95"], "the geometry adds to the citation network",
                             "no measurable difference", "the geometry hurts")  # fmt: skip
    n_ends = len(np.unique(np.r_[pi_pos, pj_pos]))
    report["population"] = {
        "pairs": len(A),
        "positives": int(pos.sum()),
        "positive_endpoints": n_ends,
    }
    report["auc"] = auc
    report["H1"] = {"best_baseline": best_base, "pickers": h1, "verdict": v1,
                    "passing": winners, "winner": winner}  # fmt: skip
    report["H2"] = h2
    log(
        f"H1: {v1}; best baseline {best_base} {auc[best_base]:.4f}; "
        f"winner {winner} {auc[winner]:.4f}"
    )
    log(f"H2: GNN - GNN-noB {h2['difference']:+.4f} {h2['ci95']} -> {h2['verdict']}")

    # reported rows
    n_pos = int(pos.sum())
    report["topk"] = {k: topk_hits(v, pos, TOPK) for k, v in S.items()}
    report["topk_chance"] = {str(q): q * n_pos / len(A) for q in TOPK}
    degsum = deg_t[A] + deg_t[B]
    qs = degsum.sort().values[(torch.linspace(0, 1, 6, device=dev)[1:-1] * (len(A) - 1)).long()]
    band = torch.bucketize(degsum, qs)
    report["auc_by_degree_quintile"] = {
        k: [float(placements(v, pos, band == q).mean()) if bool((pos & (band == q)).any()) else None
            for q in range(5)] for k, v in S.items()}  # fmt: skip
    report["degree_quintile_edges"] = qs.tolist()
    report["auc_non_generic"] = {k: float(placements(v, pos, ~gen_).mean()) for k, v in S.items()}

    # RERANK on each primary picker's top 10,000
    rr = {}
    for k in PRIMARY:
        top = S[k].topk(min(RERANK_TOP, len(A))).indices
        r = rerank_score(ctx, rerank, toks, A[top], B[top])
        before = int(pos[top[:1000]].sum())
        after = int(pos[top[r.topk(min(1000, len(top))).indices]].sum())
        rr[k] = {"hits_top1000_before": before, "hits_top1000_after": after,
                 "hits_in_top10000": int(pos[top].sum())}  # fmt: skip
    report["RERANK"] = rr
    log(f"RERANK: {rr}")

    # candidate lists for part 1's Lean fit check
    fit1 = {}
    for k in PRIMARY:
        top = S[k].topk(min(1000, len(A))).indices.cpu().numpy()
        fit1[k] = [[names[crow[pi_c[t]]], names[crow[pj_c[t]]], bool(pos_np[t])] for t in top]
    (out / "fit-candidates-part1.json").write_text(json.dumps(fit1))

    # ---- part 2: novelty ----
    p6 = _load("p6", "scripts/train-phase6-predictor.py")
    pred = p6.DeepSets().to(dev)
    pred.load_state_dict(torch.load(args.predictor, map_location="cpu"))
    pred.eval()

    def novelty_reach(a, b):
        nov = torch.empty(len(a), device=dev)
        rch = torch.empty(len(a), device=dev)
        with torch.no_grad():
            for s in chunked(len(a), 1024):
                x = torch.stack([V[a[s]], V[b[s]]], 1)
                p = pred(x, torch.ones(len(x), 2, dtype=torch.bool, device=dev))
                sim = p @ V.T
                ar = torch.arange(len(x), device=dev)
                sim[ar, a[s]] = -2
                sim[ar, b[s]] = -2
                nov[s] = 1 - sim.max(1).values
                rch[s] = 1 - torch.maximum((p * V[a[s]]).sum(-1), (p * V[b[s]]).sum(-1))
        return nov, rch

    top_n = min(NOVEL_TOP, len(A))
    top = S[winner].topk(top_n).indices
    nov, rch = novelty_reach(A[top], B[top])
    novel = (avg_rank(S[winner][top]) + avg_rank(nov) + avg_rank(rch)) / 3
    k = min(NOVEL_K, top_n)
    in_w = torch.zeros(top_n, dtype=torch.bool, device=dev)
    in_w[:k] = True  # topk returns in descending order
    in_n = torch.zeros(top_n, dtype=torch.bool, device=dev)
    in_n[novel.topk(k).indices] = True
    ppos = pos[top]
    sel = ppos.cpu().numpy()
    tops = top.cpu().numpy()
    h3 = {"winner": winner, "positives_in_top": int(sel.sum()),
          "hits_winner": int((in_w & ppos).sum()),
          "hits_novel": int((in_n & ppos).sum())}  # fmt: skip
    if sel.any():
        u = (in_n.float() - in_w.float())[ppos].cpu().numpy()
        w3 = boot_weights(pi_c[tops[sel]], pj_c[tops[sel]], np.random.default_rng(SEED + 3), draws)
        d = (u[None] * w3).sum(1)
        lo, hi = np.percentile(d, [2.5, 97.5])
        h3.update(difference=int(u.sum()), ci95=[float(lo), float(hi)])
        h3["verdict"] = verdict3(h3["ci95"], "novelty helps", "no measurable difference",
                                 "novelty hurts")  # fmt: skip
    else:
        h3["verdict"] = "no positives in the winner's top 100,000"
    report["H3"] = h3
    log(f"H3: {h3}")

    # ---- part 3 candidate lists (pool pairs only) ----
    pool_idx = torch.where(pool)[0]
    wp = S[winner][pool_idx]
    top_p = pool_idx[wp.topk(min(NOVEL_TOP, len(pool_idx))).indices]
    nov_p, rch_p = novelty_reach(A[top_p], B[top_p])
    novel_p = (avg_rank(S[winner][top_p]) + avg_rank(nov_p) + avg_rank(rch_p)) / 3
    # the whole NOVEL order: part 3 walks it until 40 pairs pass the fit check
    order = top_p[novel_p.argsort(descending=True)].cpu().numpy()
    near = pool_idx[S["NEAREST"][pool_idx].topk(min(5000, len(pool_idx))).indices].cpu().numpy()

    def rows(ix, key):
        return [{"a": names[crow[pi_c[t]]], "b": names[crow[pj_c[t]]],
                 key: float(S[key][t]) if key in S else None} for t in ix]  # fmt: skip

    (out / "part3-winner-novel.json").write_text(json.dumps(rows(order, winner)))
    (out / "part3-nearest.json").write_text(json.dumps(rows(near, "NEAREST")))

    for k in U:
        np.save(out / f"placements-{k}.npy", U[k])
    np.save(out / "positive-pairs.npy", np.stack([pi_pos, pj_pos]))
    (out / "phase7.json").write_text(json.dumps(report, indent=2) + "\n")
    log("JOB DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
