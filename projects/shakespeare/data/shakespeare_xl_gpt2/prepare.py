"""
r5 XL round — CONTROL: enlarged early-modern-drama corpus, GPT-2 tiktoken vocab.

Same corpus + splits as the custom-BPE r5 datasets (see ../_xl_corpus.py), but
encoded with GPT-2 byte-pair encoding (50,257 tokens) — the tokenizer the current
champion (r3-bpe / shakespeare-nanogpt-2) uses. Isolates the effect of the enlarged
corpus alone. No meta.pkl is written, so core train/eval/sample fall back to GPT-2
tiktoken (ADR-0012).

    uv run python projects/shakespeare/data/shakespeare_xl_gpt2/prepare.py

The held-out test slice is EXACTLY projects/shakespeare/test.txt and is never trained on.
"""
import os
import sys

import numpy as np
import tiktoken

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _xl_corpus import build_splits  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    train_text, val_text = build_splits()
    enc = tiktoken.get_encoding("gpt2")
    train_ids = enc.encode_ordinary(train_text)
    val_ids = enc.encode_ordinary(val_text)
    np.array(train_ids, dtype=np.uint16).tofile(os.path.join(HERE, "train.bin"))
    np.array(val_ids, dtype=np.uint16).tofile(os.path.join(HERE, "val.bin"))
    print(
        f"data/shakespeare_xl_gpt2/  vocab=50257 (gpt2)  "
        f"train {len(train_text):,} chars -> {len(train_ids):,} tok "
        f"({len(train_text)/len(train_ids):.2f} chars/tok)  "
        f"val {len(val_text):,} -> {len(val_ids):,} tok"
    )
    print("wrote train.bin/val.bin (no meta.pkl -> GPT-2 BPE fallback)")
