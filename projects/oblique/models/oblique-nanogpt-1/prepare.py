"""prepare.py — char-level tokenization for oblique-nanogpt-1 (frozen release copy).

Reads corpus.txt, pinned beside this file (one aphorism per line, each
prefixed by its register token, the two registers mixed 50/50 and shuffled),
and writes the dataset train.py reads:

    oblique/train.bin   uint16 char ids, the first 90% of lines
    oblique/val.bin     uint16 char ids, the last 10% of lines
    oblique/meta.pkl    {vocab_size, stoi, itos}

The split is by whole line, so a held-out line is never half-seen. meta.pkl
is the tokenizer contract (ADR-0012). The stream opens with a newline so the
first line is preceded by one like every other; a sample is primed with
"\\n[s] " or "\\n[f] ".

Run in place:
    python prepare.py
"""
import os
import pickle

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "corpus.txt")
OUT_DIR = os.path.join(HERE, "oblique")
VAL_FRACTION = 0.1


def split_lines(path=CORPUS):
    """(train lines, val lines), tokens included. The harness imports this so
    its idea of the training set is the one the model saw."""
    with open(path, encoding="utf-8") as f:
        lines = [ln for ln in f.read().split("\n") if ln]
    cut = int(len(lines) * (1 - VAL_FRACTION))
    return lines[:cut], lines[cut:]


def main():
    train, val = split_lines()
    train_text = "\n" + "\n".join(train) + "\n"
    val_text = "\n" + "\n".join(val) + "\n"
    chars = sorted(set(train_text + val_text))
    stoi = {ch: i for i, ch in enumerate(chars)}
    itos = {i: ch for i, ch in enumerate(chars)}
    print(f"corpus: {len(train) + len(val):,} lines, vocab {len(chars)} -> {''.join(chars)!r}")

    os.makedirs(OUT_DIR, exist_ok=True)
    for name, text in (("train", train_text), ("val", val_text)):
        np.array([stoi[c] for c in text], dtype=np.uint16).tofile(
            os.path.join(OUT_DIR, f"{name}.bin"))
    with open(os.path.join(OUT_DIR, "meta.pkl"), "wb") as f:
        pickle.dump({"vocab_size": len(chars), "stoi": stoi, "itos": itos}, f)
    for reg in "sf":
        print(f"  [{reg}] train {sum(ln[1] == reg for ln in train):,}  "
              f"val {sum(ln[1] == reg for ln in val):,}")
    print(f"train: {len(train_text):,} tokens   val: {len(val_text):,} tokens -> {OUT_DIR}")


if __name__ == "__main__":
    main()
