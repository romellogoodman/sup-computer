"""
prepare.py (FROZEN release copy) -- char-level tokenization for
daydream-chess-nanogpt-grand-1. Reads ./games.txt (vendored, synthetic,
seeded) and writes ./grand/{train,val}.bin + meta.pkl.

Run from inside this folder:
    python prepare.py
"""
import os
import pickle

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "games.txt")
OUT_DIR = os.path.join(HERE, "grand")

with open(RAW, "r") as f:
    data = f.read()
n_games = data.count("\n")
print(f"corpus: {len(data):,} characters, {n_games:,} games")

chars = sorted(list(set(data)))
vocab_size = len(chars)
stoi = {ch: i for i, ch in enumerate(chars)}
itos = {i: ch for i, ch in enumerate(chars)}
print(f"vocab size: {vocab_size}")


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
