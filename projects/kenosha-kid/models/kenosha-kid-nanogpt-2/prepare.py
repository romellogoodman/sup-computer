"""
prepare.py — char-level tokenization for kenosha-kid (FROZEN release copy).

This is the self-contained release prepare. Unlike the working project at the
repo root (which writes into data/kenosha/), every path here resolves relative to
THIS folder, so the snapshot rebuilds in place with no dependency on the project
root or the shared core.

Reads the vendored corpus (raw.txt next to this script, written by generate.py)
and writes the dataset the vendored engine trains on, all into THIS folder:

    kenosha/train.bin   uint16 char ids (90%)
    kenosha/val.bin     uint16 char ids (10%)
    kenosha/meta.pkl    {vocab_size, stoi, itos}

meta.pkl IS the tokenizer contract (see ADR-0012): its presence tells
train.py / sample.py to treat this as a char model. With config.py's
out_dir='.', data_root='.', dataset='kenosha', the engine reads ./kenosha/.

The .bin/.pkl outputs are gitignored; this script rebuilds them deterministically
from raw.txt. Run from inside this folder:
    python prepare.py
"""
import os
import pickle

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw.txt")
OUT_DIR = os.path.join(HERE, "kenosha")  # data_root='.', dataset='kenosha'

if not os.path.exists(RAW):
    raise SystemExit(
        "raw.txt not found next to this script. The frozen release ships the\n"
        "corpus vendored in-folder; restore it from git (it is committed), or\n"
        "regenerate it deterministically with `python generate.py`."
    )

import numpy as np  # imported after the raw.txt check so the guidance shows pre-deps

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
