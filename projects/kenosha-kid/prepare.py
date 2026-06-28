"""
prepare.py — char-level tokenization for kenosha-kid.

Reads the frozen corpus (data/raw.txt, written by generate.py) and writes the
dataset the shared core engine trains on:

    data/kenosha/train.bin   uint16 char ids (90%)
    data/kenosha/val.bin     uint16 char ids (10%)
    data/kenosha/meta.pkl    {vocab_size, stoi, itos}

meta.pkl IS the tokenizer contract (see ADR-0012): its presence tells
core/nanogpt_core/{train,sample}.py and core/export/export.py to treat this as a
char model. No core changes; kenosha-kid rides the shared engine as-is.

Run from the repo root:
    uv run python projects/kenosha-kid/prepare.py
"""
import os
import pickle

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw.txt")
OUT_DIR = os.path.join(HERE, "data", "kenosha")  # data_root=<.../data>, dataset='kenosha'

with open(RAW, "r") as f:
    data = f.read()
print(f"corpus: {len(data):,} characters")

chars = sorted(list(set(data)))
vocab_size = len(chars)
stoi = {ch: i for i, ch in enumerate(chars)}
itos = {i: ch for i, ch in enumerate(chars)}
print(f"vocab size: {vocab_size}  ->  {''.join(chars)!r}")


def encode(s):
    return [stoi[c] for c in s]


n = len(data)
train_data = data[: int(n * 0.9)]
val_data = data[int(n * 0.9):]

os.makedirs(OUT_DIR, exist_ok=True)
np.array(encode(train_data), dtype=np.uint16).tofile(os.path.join(OUT_DIR, "train.bin"))
np.array(encode(val_data), dtype=np.uint16).tofile(os.path.join(OUT_DIR, "val.bin"))
with open(os.path.join(OUT_DIR, "meta.pkl"), "wb") as f:
    pickle.dump({"vocab_size": vocab_size, "stoi": stoi, "itos": itos}, f)

print(f"train: {len(train_data):,} tokens   val: {len(val_data):,} tokens")
print(f"wrote train.bin / val.bin / meta.pkl -> {OUT_DIR}")
