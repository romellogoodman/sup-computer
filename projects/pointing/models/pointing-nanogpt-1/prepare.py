"""prepare.py -- tokenize the pairs build_corpus.py wrote.

Char-level, one vocabulary for both sides of the pair: the input alphabet
(letters, digits, space, apostrophe, hyphen), the separator, the newline, the
empty slot and the sixteen marks. The vocabulary is fixed by strip.py, not
read off the corpus, so a mark the training works never use still has an id.

Writes train.bin / val.bin / meta.pkl (the ADR-0012 contract) into
tokenized/, and a second meta.pkl beside ckpt.pt, where the ONNX export
looks for the vocabulary.

Run in place, after build_corpus.py:
    python prepare.py
"""
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import strip  # noqa: E402

CORPUS_DIR = os.path.join(HERE, "corpus")
OUT_DIR = os.path.join(HERE, "tokenized")

CHARS = ["\n", " ", "'", "-"] + list("0123456789") + list("abcdefghijklmnopqrstuvwxyz") \
    + [strip.SEP, strip.NONE] + strip.MARKS


def main():
    stoi = {c: i for i, c in enumerate(CHARS)}
    itos = {i: c for i, c in enumerate(CHARS)}
    os.makedirs(OUT_DIR, exist_ok=True)
    for split in ("train", "val"):
        with open(os.path.join(CORPUS_DIR, f"{split}.txt"), encoding="utf-8") as f:
            data = f.read()
        ids = np.array([stoi[c] for c in data], dtype=np.uint16)
        ids.tofile(os.path.join(OUT_DIR, f"{split}.bin"))
        print(f"{split}: {len(ids):,} tokens, {data.count(chr(10)):,} lines")
    meta = {"vocab_size": len(CHARS), "stoi": stoi, "itos": itos, "arm": "char", "tokenizer_name": "pointing-char-v1"}
    for d in (OUT_DIR, HERE):
        with open(os.path.join(d, "meta.pkl"), "wb") as f:
            pickle.dump(meta, f)
    print(f"vocab: {len(CHARS)} symbols -> {OUT_DIR}")


if __name__ == "__main__":
    main()
