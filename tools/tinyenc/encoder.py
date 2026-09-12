"""Tiny transformer encoder + classifier head, and a plain train/eval loop."""
from __future__ import annotations

import math
import random

import torch
import torch.nn as nn
import torch.nn.functional as F


class Encoder(nn.Module):
    """Bidirectional transformer encoder with mean pooling and a linear head."""

    def __init__(self, vocab_size: int, n_classes: int, d: int = 128, n_layer: int = 2,
                 n_head: int = 4, max_len: int = 512, dropout: float = 0.1, n_extra: int = 0):
        super().__init__()
        self.tok = nn.Embedding(vocab_size + 1, d)  # +1 for pad
        self.pos = nn.Embedding(max_len, d)
        layer = nn.TransformerEncoderLayer(d, n_head, 4 * d, dropout, batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(layer, n_layer)
        self.norm = nn.LayerNorm(d)
        self.head = nn.Linear(d + n_extra, n_classes)
        self.pad = vocab_size
        self.max_len = max_len
        self.n_extra = n_extra

    def forward(self, ids: torch.Tensor, extra: torch.Tensor | None = None) -> torch.Tensor:
        mask = ids == self.pad
        pos = torch.arange(ids.size(1), device=ids.device)
        x = self.tok(ids) + self.pos(pos)[None]
        x = self.enc(x, src_key_padding_mask=mask)
        x = self.norm(x)
        keep = (~mask).float().unsqueeze(-1)
        pooled = (x * keep).sum(1) / keep.sum(1).clamp(min=1)
        if self.n_extra:
            pooled = torch.cat([pooled, extra], dim=-1)
        return self.head(pooled)


def pad_batch(seqs: list, pad: int, max_len: int, device) -> torch.Tensor:
    seqs = [s[-max_len:] for s in seqs]
    L = max(len(s) for s in seqs)
    out = torch.full((len(seqs), L), pad, dtype=torch.long)
    for i, s in enumerate(seqs):
        out[i, : len(s)] = torch.tensor(s, dtype=torch.long)
    return out.to(device)


def auroc(scores: list, labels: list) -> float:
    """Rank-based AUROC (Mann-Whitney), ties split."""
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return float("nan")
    ranked = sorted([(s, 1) for s in pos] + [(s, 0) for s in neg])
    # average ranks for ties
    ranks = [0.0] * len(ranked)
    i = 0
    while i < len(ranked):
        j = i
        while j + 1 < len(ranked) and ranked[j + 1][0] == ranked[i][0]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = r
        i = j + 1
    rank_pos = sum(r for r, (_, y) in zip(ranks, ranked) if y)
    return (rank_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


@torch.no_grad()
def predict(model: Encoder, data: list, device, batch: int = 64) -> torch.Tensor:
    model.eval()
    outs = []
    for i in range(0, len(data), batch):
        chunk = data[i : i + batch]
        ids = pad_batch([d["ids"] for d in chunk], model.pad, model.max_len, device)
        extra = None
        if model.n_extra:
            extra = torch.tensor([d["extra"] for d in chunk], dtype=torch.float, device=device)
        outs.append(model(ids, extra).float().cpu())
    return torch.cat(outs)


def evaluate(model: Encoder, data: list, device, n_classes: int) -> dict:
    logits = predict(model, data, device)
    labels = [d["label"] for d in data]
    pred = logits.argmax(-1).tolist()
    acc = sum(int(p == y) for p, y in zip(pred, labels)) / max(len(labels), 1)
    out = {"n": len(labels), "acc": acc}
    if n_classes == 2:
        prob = torch.softmax(logits, -1)[:, 1].tolist()
        out["auroc"] = auroc(prob, labels)
        out["scores"] = prob
    else:
        cm = [[0] * n_classes for _ in range(n_classes)]
        for p, y in zip(pred, labels):
            cm[y][p] += 1
        out["confusion"] = cm
    return out


def fit(model: Encoder, train: list, device, n_classes: int, epochs: int = 10, lr: float = 3e-4,
        batch: int = 32, seed: int = 0, class_weight: bool = True, log=print) -> None:
    """Plain AdamW loop for a fixed number of epochs. No model selection, so
    nothing about a held-out split leaks into which weights are kept."""
    torch.manual_seed(seed)
    random.seed(seed)
    model.to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    weight = None
    if class_weight:
        counts = [max(1, sum(1 for d in train if d["label"] == c)) for c in range(n_classes)]
        weight = torch.tensor([len(train) / (n_classes * c) for c in counts], dtype=torch.float, device=device)
    for ep in range(epochs):
        model.train()
        order = list(range(len(train)))
        random.shuffle(order)
        tot = 0.0
        for i in range(0, len(order), batch):
            chunk = [train[j] for j in order[i : i + batch]]
            ids = pad_batch([d["ids"] for d in chunk], model.pad, model.max_len, device)
            extra = None
            if model.n_extra:
                extra = torch.tensor([d["extra"] for d in chunk], dtype=torch.float, device=device)
            y = torch.tensor([d["label"] for d in chunk], dtype=torch.long, device=device)
            loss = F.cross_entropy(model(ids, extra), y, weight=weight)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tot += loss.item() * len(chunk)
        log(f"epoch {ep + 1}/{epochs} train loss {tot / max(len(train), 1):.3f}")


def train_classifier(model: Encoder, train: list, dev: list, device, n_classes: int,
                     epochs: int = 10, lr: float = 3e-4, batch: int = 32, seed: int = 0,
                     class_weight: bool = True, log=print) -> dict:
    """fit() one epoch at a time, keeping the best-dev weights (AUROC for
    binary, accuracy otherwise). Use only with a dev split that is not the
    test split."""
    key = "auroc" if n_classes == 2 else "acc"
    best, best_state = -math.inf, None
    for ep in range(epochs):
        fit(model, train, device, n_classes, epochs=1, lr=lr, batch=batch, seed=seed + ep,
            class_weight=class_weight, log=lambda *_: None)
        m = evaluate(model, dev, device, n_classes)
        score = m[key] if m[key] == m[key] else m["acc"]  # nan guard
        log(f"epoch {ep + 1}/{epochs} dev acc {m['acc']:.3f}" + (f" auroc {m['auroc']:.3f}" if n_classes == 2 else ""))
        if score > best:
            best = score
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    if best_state is not None:
        model.load_state_dict(best_state)
    return evaluate(model, dev, device, n_classes)
