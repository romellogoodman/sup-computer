"""Attribution: which sibling wrote this passage? Encoder vs n-gram baseline vs chance.

Reads the JSONL files sample.py wrote. The main task is K-way over the runs
named seed-<k>; held out by sampling seed (the last --holdout_frac of seeds).
Controls are binary: seed-1 vs seed-1-iter1000 (training step), and
seed-1 vs seed-1-t<temp> (temperature).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from tinyenc import Encoder, evaluate, fit  # noqa: E402

VOCAB = 1024
PAD = VOCAB
HASH_DIM = 1 << 16


def read(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def split(recs, holdout_frac):
    seeds = sorted({r["sample_seed"] for r in recs})
    k = max(1, int(round(len(seeds) * holdout_frac)))
    held = set(seeds[-k:])
    return [r for r in recs if r["sample_seed"] not in held], [r for r in recs if r["sample_seed"] in held]


def ngram_features(ids):
    idx = set()
    for n in (1, 2, 3):
        for i in range(len(ids) - n + 1):
            idx.add(hash((n, tuple(ids[i:i + n]))) % HASH_DIM)
    return sorted(idx)


def ngram_logistic(train, test, n_classes, device, epochs=30):
    """Multinomial logistic regression over hashed 1-3-gram presence."""
    def mat(data):
        rows, cols = [], []
        for i, d in enumerate(data):
            f = ngram_features(d["ids"])
            rows += [i] * len(f)
            cols += f
        v = torch.ones(len(rows))
        return torch.sparse_coo_tensor(torch.tensor([rows, cols]), v, (len(data), HASH_DIM)).coalesce()
    Xtr, Xte = mat(train), mat(test)
    ytr = torch.tensor([d["label"] for d in train])
    W = torch.zeros(HASH_DIM, n_classes, requires_grad=True)
    b = torch.zeros(n_classes, requires_grad=True)
    opt = torch.optim.Adam([W, b], lr=0.05)
    for _ in range(epochs):
        opt.zero_grad()
        logits = torch.sparse.mm(Xtr, W) + b
        loss = torch.nn.functional.cross_entropy(logits, ytr) + 1e-4 * (W * W).sum()
        loss.backward()
        opt.step()
    with torch.no_grad():
        pred = (torch.sparse.mm(Xte, W) + b).argmax(-1).tolist()
    yte = [d["label"] for d in test]
    acc = sum(int(p == y) for p, y in zip(pred, yte)) / len(yte)
    cm = [[0] * n_classes for _ in range(n_classes)]
    for p, y in zip(pred, yte):
        cm[y][p] += 1
    return {"acc": acc, "confusion": cm}


def task(name, groups, holdout_frac, device, epochs, seeds, log):
    """groups: list of (label, records). Returns encoder + n-gram results."""
    n = len(groups)
    train, test = [], []
    for label, recs in groups:
        tr, te = split(recs, holdout_frac)
        train += [{"ids": r["ids"], "label": label} for r in tr]
        test += [{"ids": r["ids"], "label": label} for r in te]
    log(f"[{name}] {n}-way, train {len(train)} test {len(test)}, chance {1 / n:.3f}")
    out = {"n_way": n, "n_train": len(train), "n_test": len(test), "chance": 1 / n, "encoder": []}
    for s in range(seeds):
        m = Encoder(VOCAB, n, d=128, n_layer=2, n_head=4, max_len=260, dropout=0.1)
        fit(m, train, device, n, epochs=epochs, seed=s, class_weight=False, log=lambda *_: None)
        r = evaluate(m, test, device, n)
        out["encoder"].append({"acc": r["acc"], "confusion": r.get("confusion")})
        log(f"[{name}] encoder seed {s}: acc {r['acc']:.3f}")
    out["encoder_acc_mean"] = sum(e["acc"] for e in out["encoder"]) / seeds
    ng = ngram_logistic(train, test, n, device)
    out["ngram"] = ng
    log(f"[{name}] n-gram logistic: acc {ng['acc']:.3f}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--holdout_frac", type=float, default=0.2)
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--device", default="mps")
    a = ap.parse_args()
    files = {os.path.basename(p)[:-6]: p for p in glob.glob(os.path.join(a.samples, "*.jsonl"))}
    sibs = sorted((k for k in files if re.fullmatch(r"seed-\d+", k)), key=lambda k: int(k.split("-")[1]))
    results = {"siblings": sibs}
    with open(os.path.join(a.samples, "meta.json")) as f:
        results["meta"] = json.load(f)
    results["attribution"] = task("attribution", [(i, read(files[k])) for i, k in enumerate(sibs)],
                                  a.holdout_frac, a.device, a.epochs, a.seeds, print)
    first = sibs[0]
    for ctrl in sorted(k for k in files if k.startswith(first + "-")):
        results[f"control:{first}-vs-{ctrl}"] = task(
            f"{first} vs {ctrl}", [(0, read(files[first])), (1, read(files[ctrl]))],
            a.holdout_frac, a.device, a.epochs, a.seeds, print)
    for ctrl in (k for k in files if re.fullmatch(rf"{first}-iter\d+", k)):
        results[f"control:{first}-vs-{ctrl}"] = task(
            f"{first} vs {ctrl}", [(0, read(files[first])), (1, read(files[ctrl]))],
            a.holdout_frac, a.device, a.epochs, a.seeds, print)
    with open(a.out, "w") as f:
        json.dump(results, f, indent=1)
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
