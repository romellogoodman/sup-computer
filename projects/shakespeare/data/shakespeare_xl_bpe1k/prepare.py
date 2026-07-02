"""
r5 XL round — enlarged early-modern-drama corpus, custom byte-level BPE (~1024).

Run with the tokenizers lib provided ad hoc (not in pyproject):
    uv run --with tokenizers python projects/shakespeare/data/shakespeare_xl_bpe1k/prepare.py

Shares the corpus + splits with the other r5 datasets (see ../_xl_corpus.py); the
held-out test slice is EXACTLY projects/shakespeare/test.txt and is never trained on.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _xl_bpe import build_bpe_dataset  # noqa: E402
from _xl_corpus import build_splits  # noqa: E402

VOCAB_SIZE = 1024

if __name__ == "__main__":
    train_text, val_text = build_splits()
    build_bpe_dataset("shakespeare_xl_bpe1k", VOCAB_SIZE, train_text, val_text)
