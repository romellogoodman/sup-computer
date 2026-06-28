"""
Prepare the synthetic Gatsby corpus for character-level language modeling.

Unlike the Shakespeare sibling project, the corpus here is *generated*, not
downloaded: run `python generate.py` first to produce `data/raw.txt` (a
concatenation of TinyStories-register stories, each prefixed with a
`[green=N] topic: ...` control line). This script then maps characters to ints
and writes:

  train.bin / val.bin  - the encoded token ids (uint16)
  meta.pkl             - vocab_size + stoi/itos (encoder/decoder)

All artifacts are gitignored; this script rebuilds them from raw.txt.
"""
import os
import pickle

HERE = os.path.dirname(os.path.abspath(__file__))
raw_path = os.path.join(HERE, 'data', 'raw.txt')

if not os.path.exists(raw_path):
    raise SystemExit(
        "data/raw.txt not found. Generate the corpus first:\n"
        "    python generate.py --n 20       # tiny sample to validate the pipeline\n"
        "    python generate.py --n 1000 --batch   # a real run (uses the Claude API)\n"
        "See README.md and docs/plan.md for details."
    )

import numpy as np  # imported after the raw.txt check so the guidance shows pre-deps

with open(raw_path, 'r', encoding='utf-8') as f:
    data = f.read()
print(f"length of corpus in characters: {len(data):,}")

# all the unique characters that occur in the corpus
chars = sorted(list(set(data)))
vocab_size = len(chars)
print("all the unique characters:", repr(''.join(chars)))
print(f"vocab size: {vocab_size:,}")

# character <-> integer mappings
stoi = {ch: i for i, ch in enumerate(chars)}
itos = {i: ch for i, ch in enumerate(chars)}
def encode(s):
    return [stoi[c] for c in s]

# train/val split
n = len(data)
train_data = data[:int(n * 0.9)]
val_data = data[int(n * 0.9):]
train_ids = encode(train_data)
val_ids = encode(val_data)
print(f"train has {len(train_ids):,} tokens")
print(f"val has {len(val_ids):,} tokens")

# export the encoded ids
np.array(train_ids, dtype=np.uint16).tofile(os.path.join(HERE, 'train.bin'))
np.array(val_ids, dtype=np.uint16).tofile(os.path.join(HERE, 'val.bin'))

# meta for sample.py / train.py to encode/decode
meta = {'vocab_size': vocab_size, 'itos': itos, 'stoi': stoi}
with open(os.path.join(HERE, 'meta.pkl'), 'wb') as f:
    pickle.dump(meta, f)

print("wrote train.bin, val.bin, meta.pkl in this folder")
