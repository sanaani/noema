#!/usr/bin/env python3
"""train-encoders-gpu.py -- train and apply phase 4's two self-supervised encoders.

Every setting here is fixed in results/phase-4-trained-encoder/README.md; this
script implements that and takes no tuning arguments. It never reads a label.

    B  byte-level BPE (16,384) + 6-layer Transformer encoder, whole-word masked
       tokens, on the union's 88,498 state and statement texts. Output: one
       256-d vector per text, in texts.json order -- the same shape as phase 3's
       ReProver embeddings, so the phase 3 centroid and analysis code reads it.
    C  the paper's tactic-head denoising encoder (4+2 layers, d 128) on each
       observed theorem's tactic heads. Output: one 128-d vector per theorem.

Both hold out 10% of their inputs for the loss curve and report, for the
training-health check, the held-out loss of a unigram frequency predictor on
the same masked positions.

    scripts/train-encoders-gpu.py --inputs <dir> --out <dir>
    scripts/train-encoders-gpu.py --inputs <dir> --out <dir> --smoke   # tiny CPU run
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

SEED = 20260926
PAD, UNK, MASK, BOS, EOS = 0, 1, 2, 3, 4
SPECIAL = ["<pad>", "<unk>", "<mask>", "<bos>", "<eos>"]

B_CFG = dict(
    vocab=16_384, d=256, heads=8, layers=6, ff=1024, dropout=0.1, max_len=512,
    mask=0.15, epochs=30, batch=64, lr=3e-4, wd=0.01, val=0.10,
)  # fmt: skip
C_CFG = dict(
    d=128, heads=4, enc=4, dec=2, dropout=0.1, max_len=64, min_count=5,
    mask=0.20, epochs=20, batch=128, lr=3e-4, wd=0.01, val=0.10,
)  # fmt: skip
C_RESERVED = 5  # PAD CLS SEP MASK UNK, as in the paper's code
C_CLS, C_SEP, C_MASK, C_UNK = 1, 2, 3, 4


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cosine_lr(opt, base: float, epoch: int, epochs: int) -> None:
    for g in opt.param_groups:
        g["lr"] = base * 0.5 * (1 + math.cos(math.pi * epoch / epochs))


# ---------------------------------------------------------------------------
# B: proof-state encoder
# ---------------------------------------------------------------------------


class StateEncoder(nn.Module):
    def __init__(self, vocab: int, d: int, heads: int, layers: int, ff: int, dropout: float,
                 max_len: int):  # fmt: skip
        super().__init__()
        self.tok = nn.Embedding(vocab, d, padding_idx=PAD)
        self.pos = nn.Embedding(max_len, d)
        layer = nn.TransformerEncoderLayer(
            d, heads, ff, dropout, activation="gelu", batch_first=True
        )
        self.encoder = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.norm = nn.LayerNorm(d)
        self.lm = nn.Linear(d, vocab, bias=False)

    def hidden(self, ids):
        pos = torch.arange(ids.shape[1], device=ids.device)
        pad = ids == PAD
        h = self.encoder(self.tok(ids) + self.pos(pos)[None], src_key_padding_mask=pad)
        return self.norm(h), pad

    def forward(self, ids):
        h, _ = self.hidden(ids)
        return self.lm(h)

    def pooled(self, ids):
        h, pad = self.hidden(ids)
        keep = (~pad).unsqueeze(-1).to(h.dtype)
        return (h * keep).sum(1) / keep.sum(1).clamp(min=1)


def train_tokenizer(texts: list[str], vocab: int):
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

    tok = Tokenizer(models.BPE(unk_token="<unk>"))
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(
        vocab_size=vocab,
        special_tokens=SPECIAL,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        show_progress=False,
    )
    tok.train_from_iterator(texts, trainer=trainer)
    assert [tok.token_to_id(s) for s in SPECIAL] == list(range(5))
    return tok


def tokenize(tok, texts: list[str], max_len: int):
    """Token ids with BOS/EOS, and each token's word index (-1 for BOS/EOS)."""
    ids, words, truncated = [], [], 0
    for e in tok.encode_batch(texts):
        body, w = e.ids, [x if x is not None else -1 for x in e.word_ids]
        if len(body) > max_len - 2:
            truncated += 1
            body, w = body[: max_len - 2], w[: max_len - 2]
        ids.append(np.array([BOS, *body, EOS], dtype=np.int32))
        words.append(np.array([-1, *w, -1], dtype=np.int32))
    return ids, words, truncated


def whole_word_mask(ids, words, p: float, rng: np.random.Generator):
    """Batch of (corrupted, target, mask) with whole words masked at rate p."""
    L = max(len(x) for x in ids)
    inp = np.zeros((len(ids), L), dtype=np.int64)
    tgt = np.zeros_like(inp)
    msk = np.zeros((len(ids), L), dtype=bool)
    for r, (x, w) in enumerate(zip(ids, words, strict=True)):
        uniq = np.unique(w[w >= 0])
        chosen = uniq[rng.random(len(uniq)) < p]
        if len(chosen) == 0 and len(uniq):
            chosen = rng.choice(uniq, 1)
        m = np.isin(w, chosen)
        inp[r, : len(x)] = np.where(m, MASK, x)
        tgt[r, : len(x)] = x
        msk[r, : len(x)] = m
    return torch.from_numpy(inp), torch.from_numpy(tgt), torch.from_numpy(msk)


def masked_loss(logits, tgt, msk):
    return F.cross_entropy(logits[msk].float(), tgt[msk])


def unigram_baseline(train_ids, val_batches, vocab: int) -> float:
    counts = np.bincount(np.concatenate(train_ids), minlength=vocab).astype(np.float64)
    counts[:5] = 0
    logp = np.log((counts + 1) / (counts + 1).sum())
    nll = [(-logp[t[m].numpy()]).sum() for _, t, m in val_batches]
    n = sum(int(m.sum()) for _, _, m in val_batches)
    return float(sum(nll) / n)


def run_b(texts, cfg, device, amp, rng, report, out: Path):
    log(f"B: tokenizer on {len(texts):,} texts")
    tok = train_tokenizer(texts, cfg["vocab"])
    tok.save(str(out / "b-tokenizer.json"))
    ids, words, truncated = tokenize(tok, texts, cfg["max_len"])
    lengths = np.array([len(x) for x in ids])
    report["truncated"] = truncated
    report["truncated_share"] = truncated / len(texts)
    report["tokens_median"] = int(np.median(lengths))
    log(f"B: {truncated:,} of {len(texts):,} texts over {cfg['max_len']} tokens")

    perm = rng.permutation(len(texts))
    n_val = int(round(cfg["val"] * len(texts)))
    val_idx, tr_idx = np.sort(perm[:n_val]), perm[n_val:]
    vrng = np.random.default_rng(SEED + 1)  # fixed held-out masks, same every epoch
    val_batches = [
        whole_word_mask([ids[i] for i in c], [words[i] for i in c], cfg["mask"], vrng)
        for c in np.array_split(val_idx, max(1, len(val_idx) // cfg["batch"]))
    ]
    report["unigram_val_loss"] = unigram_baseline([ids[i] for i in tr_idx], val_batches,
                                                  cfg["vocab"])  # fmt: skip

    lr = cfg["lr"]
    for _attempt in (1, 2):
        torch.manual_seed(SEED)
        model = StateEncoder(cfg["vocab"], cfg["d"], cfg["heads"], cfg["layers"], cfg["ff"],
                             cfg["dropout"], cfg["max_len"]).to(device)  # fmt: skip
        opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=cfg["wd"])
        curve, diverged = [], False
        # Length-sorted chunks, shuffled: less padding, same content per epoch.
        order = tr_idx[np.argsort(lengths[tr_idx], kind="stable")]
        chunks = np.array_split(order, max(1, len(order) // cfg["batch"]))
        for epoch in range(cfg["epochs"]):
            cosine_lr(opt, lr, epoch, cfg["epochs"])
            model.train()
            t0, tot, nb = time.time(), 0.0, 0
            for k in rng.permutation(len(chunks)):
                c = chunks[k]
                x, t, m = whole_word_mask([ids[i] for i in c], [words[i] for i in c],
                                          cfg["mask"], rng)  # fmt: skip
                x, t, m = x.to(device), t.to(device), m.to(device)
                with torch.autocast(device.type, dtype=torch.bfloat16, enabled=amp):
                    loss = masked_loss(model(x), t, m)
                if not torch.isfinite(loss):
                    diverged = True
                    break
                opt.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
                tot, nb = tot + loss.item(), nb + 1
            if diverged:
                break
            vl = evaluate_b(model, val_batches, device, amp)
            curve.append({"epoch": epoch + 1, "train": tot / max(nb, 1), "val": vl,
                          "seconds": round(time.time() - t0, 1)})  # fmt: skip
            log(f"B epoch {epoch + 1}/{cfg['epochs']} train {tot / max(nb, 1):.4f} val {vl:.4f}"
                f" ({time.time() - t0:.0f}s)")  # fmt: skip
        if not diverged:
            break
        log(f"B diverged at lr {lr}; rerunning once at {lr / 2}")
        report.setdefault("diverged_at_lr", []).append(lr)
        lr /= 2
    report |= {"lr_used": lr, "curve": curve, "diverged_final": diverged}
    torch.save(model.state_dict(), out / "b-model.pt")

    log("B: embedding every text")
    model.eval()
    vecs = np.zeros((len(texts), cfg["d"]), dtype=np.float32)
    by_len = np.argsort(lengths, kind="stable")
    with torch.no_grad():
        for c in np.array_split(by_len, max(1, len(by_len) // 256)):
            L = max(len(ids[i]) for i in c)
            x = np.zeros((len(c), L), dtype=np.int64)
            for r, i in enumerate(c):
                x[r, : len(ids[i])] = ids[i]
            with torch.autocast(device.type, dtype=torch.bfloat16, enabled=amp):
                v = model.pooled(torch.from_numpy(x).to(device)).float()
            vecs[c] = F.normalize(v, dim=1).cpu().numpy()
    np.savez(out / "b-embeddings.npz", texts=np.array(texts), vectors=vecs)


def evaluate_b(model, batches, device, amp) -> float:
    model.eval()
    tot, n = 0.0, 0
    with torch.no_grad():
        for x, t, m in batches:
            x, t, m = x.to(device), t.to(device), m.to(device)
            with torch.autocast(device.type, dtype=torch.bfloat16, enabled=amp):
                logits = model(x)
            tot += F.cross_entropy(logits[m].float(), t[m], reduction="sum").item()
            n += int(m.sum())
    return tot / max(n, 1)


# ---------------------------------------------------------------------------
# C: tactic-head encoder (the paper's main recipe)
# ---------------------------------------------------------------------------


class TacticEncoder(nn.Module):
    def __init__(self, vocab: int, d: int, heads: int, enc: int, dec: int, dropout: float,
                 max_len: int):  # fmt: skip
        super().__init__()
        self.embed = nn.Embedding(vocab, d, padding_idx=PAD)
        self.pos = nn.Embedding(max_len, d)
        el = nn.TransformerEncoderLayer(d, heads, d * 4, dropout, activation="gelu",
                                        batch_first=True)  # fmt: skip
        self.encoder = nn.TransformerEncoder(el, enc, enable_nested_tensor=False)
        dl = nn.TransformerDecoderLayer(d, heads, d * 4, dropout, activation="gelu",
                                        batch_first=True)  # fmt: skip
        self.decoder = nn.TransformerDecoder(dl, dec)
        self.head = nn.Linear(d, vocab)

    def encode(self, x):
        pos = self.pos(torch.arange(x.shape[1], device=x.device))[None]
        pad = x == PAD
        return self.encoder(self.embed(x) + pos, src_key_padding_mask=pad), pad

    def pooled(self, x):
        h, pad = self.encode(x)
        keep = (~pad).float().unsqueeze(-1)
        return (h * keep).sum(1) / keep.sum(1).clamp(min=1)

    def forward(self, x):
        mem, pad = self.encode(x)
        q = self.pos(torch.arange(x.shape[1], device=x.device))[None].expand(x.shape[0], -1, -1)
        return self.head(self.decoder(q, mem, memory_key_padding_mask=pad))


def c_corrupt(X: np.ndarray, p: float, rng: np.random.Generator):
    m = (rng.random(X.shape) < p) & (X >= C_RESERVED)
    return (torch.from_numpy(np.where(m, C_MASK, X)).long(), torch.from_numpy(X).long(),
            torch.from_numpy(m))  # fmt: skip


def run_c(records, cfg, device, rng, report, out: Path):
    counts = collections.Counter(h for r in records for h in r["heads"])
    vocab = {h: i + C_RESERVED for i, h in enumerate(sorted(k for k, c in counts.items()
                                                            if c >= cfg["min_count"]))}  # fmt: skip
    V = len(vocab) + C_RESERVED
    L = cfg["max_len"]
    X = np.zeros((len(records), L), dtype=np.int64)
    for r, rec in enumerate(records):
        seq = [C_CLS, *[vocab.get(h, C_UNK) for h in rec["heads"][: L - 2]], C_SEP]
        X[r, : len(seq)] = seq
    report |= {"vocab": V, "theorems": len(records)}
    (out / "c-vocab.json").write_text(json.dumps(vocab, indent=1, ensure_ascii=False))

    perm = rng.permutation(len(records))
    n_val = int(round(cfg["val"] * len(records)))
    val_idx, tr_idx = perm[:n_val], perm[n_val:]
    vx = c_corrupt(X[val_idx], cfg["mask"], np.random.default_rng(SEED + 2))
    tc = np.bincount(X[tr_idx].ravel(), minlength=V).astype(np.float64)
    tc[:C_RESERVED] = 0
    logp = np.log((tc + 1) / (tc + 1).sum())
    report["unigram_val_loss"] = float(-logp[vx[1][vx[2]].numpy()].mean())

    lr = cfg["lr"]
    for _attempt in (1, 2):
        torch.manual_seed(SEED)
        model = TacticEncoder(V, cfg["d"], cfg["heads"], cfg["enc"], cfg["dec"], cfg["dropout"],
                              L).to(device)  # fmt: skip
        opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=cfg["wd"])
        curve, diverged = [], False
        for epoch in range(cfg["epochs"]):
            cosine_lr(opt, lr, epoch, cfg["epochs"])
            model.train()
            t0, tot, nb = time.time(), 0.0, 0
            order = rng.permutation(tr_idx)
            for s in range(0, len(order) - cfg["batch"] + 1, cfg["batch"]):  # drop_last
                x, t, m = (a.to(device) for a in c_corrupt(X[order[s : s + cfg["batch"]]],
                                                            cfg["mask"], rng))  # fmt: skip
                if not m.any():
                    continue
                loss = F.cross_entropy(model(x)[m], t[m])
                if not torch.isfinite(loss):
                    diverged = True
                    break
                opt.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
                tot, nb = tot + loss.item(), nb + 1
            if diverged:
                break
            model.eval()
            with torch.no_grad():
                x, t, m = (a.to(device) for a in vx)
                vl = F.cross_entropy(model(x)[m], t[m]).item()
            curve.append({"epoch": epoch + 1, "train": tot / max(nb, 1), "val": vl,
                          "seconds": round(time.time() - t0, 1)})  # fmt: skip
            log(f"C epoch {epoch + 1}/{cfg['epochs']} train {tot / max(nb, 1):.4f} val {vl:.4f}")
        if not diverged:
            break
        log(f"C diverged at lr {lr}; rerunning once at {lr / 2}")
        report.setdefault("diverged_at_lr", []).append(lr)
        lr /= 2
    report |= {"lr_used": lr, "curve": curve, "diverged_final": diverged}
    torch.save(model.state_dict(), out / "c-model.pt")

    model.eval()
    vecs = np.zeros((len(records), cfg["d"]), dtype=np.float32)
    with torch.no_grad():
        for s in range(0, len(records), 512):
            v = model.pooled(torch.from_numpy(X[s : s + 512]).to(device))
            vecs[s : s + 512] = F.normalize(v, dim=1).cpu().numpy()
    np.savez(out / "c-embeddings.npz", names=np.array([r["name"] for r in records]),
             vectors=vecs)  # fmt: skip


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--inputs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true", help="tiny subset, 2 epochs, for a CPU check")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    manifest = json.loads((args.inputs / "inputs-manifest.json").read_text())
    for key, name in (("texts_sha256", "texts.json.gz"),
                      ("tactic_heads_sha256", "tactic-heads.jsonl.gz")):  # fmt: skip
        if sha256(args.inputs / name) != manifest[key]:
            raise SystemExit(f"{name} does not match the frozen manifest")
    with gzip.open(args.inputs / "texts.json.gz", "rt") as f:
        texts = json.load(f)
    with gzip.open(args.inputs / "tactic-heads.jsonl.gz", "rt") as f:
        records = [json.loads(line) for line in f]
    if len(texts) != manifest["texts"]:
        raise SystemExit("text count does not match the manifest")

    b_cfg, c_cfg = dict(B_CFG), dict(C_CFG)
    if args.smoke:
        texts, records = texts[:600], records[:600]
        b_cfg |= {"vocab": 2000, "epochs": 2, "layers": 2}
        c_cfg |= {"epochs": 2}

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    amp = device.type == "cuda"
    report = {
        "seed": SEED,
        "smoke": args.smoke,
        "device": torch.cuda.get_device_name(0) if amp else "cpu",
        "torch": torch.__version__,
        "inputs_manifest": manifest,
        "B": {"config": b_cfg},
        "C": {"config": c_cfg},
    }
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    t0 = time.time()
    run_b(texts, b_cfg, device, amp, np.random.default_rng(SEED), report["B"], args.out)
    run_c(records, c_cfg, device, np.random.default_rng(SEED), report["C"], args.out)
    report["seconds"] = round(time.time() - t0)
    (args.out / "training-report.json").write_text(json.dumps(report, indent=2) + "\n")
    log(f"done in {report['seconds']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
