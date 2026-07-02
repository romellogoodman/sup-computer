"""
prepare.py -- char-level tokenization for daydream, shared across all three
tiers (Micro, Regular, Grand). Same shape as kenosha-kid's prepare.py:
build a vocab from whatever characters actually appear in the corpus, split
90/10, write train.bin/val.bin/meta.pkl. meta.pkl IS the tokenizer contract
(ADR-0012) -- no core changes needed to train on chess.

Each tier gets its own vocab, built from its own corpus, because square
names depend on board dimensions -- Micro's files only run a-e, Grand's run
a-l plus promotion letters for Chancellor/Archbishop that don't exist
anywhere else. Never share a vocab across tiers.

Corpus format (written by fetch_filtered.py / selfplay.py): one game per
line, moves space-separated UCI (e.g. "e2e4 e7e5 g1f3 ..."). The newline is
part of the vocab too -- it's the model's only signal for "game boundary."

Run from the repo root:
    uv run python projects/daydream/data/prepare.py --tier micro
    uv run python projects/daydream/data/prepare.py --tier regular
    uv run python projects/daydream/data/prepare.py --tier grand
"""
import argparse
import os
import pickle

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", required=True, choices=["micro", "regular", "grand"])
    args = ap.parse_args()

    tier_dir = os.path.join(HERE, args.tier)
    raw_path = os.path.join(tier_dir, "games.txt")
    out_dir = os.path.join(tier_dir, "tokenized")

    with open(raw_path, "r") as f:
        data = f.read()
    n_games = data.count("\n")
    print(f"[{args.tier}] corpus: {len(data):,} characters, {n_games:,} games")

    chars = sorted(list(set(data)))
    vocab_size = len(chars)
    stoi = {ch: i for i, ch in enumerate(chars)}
    itos = {i: ch for i, ch in enumerate(chars)}
    print(f"[{args.tier}] vocab size: {vocab_size}  ->  {''.join(repr(c)[1:-1] for c in chars)}")

    def encode(s):
        return [stoi[c] for c in s]

    n = len(data)
    train_data = data[: int(n * 0.9)]
    val_data = data[int(n * 0.9):]

    os.makedirs(out_dir, exist_ok=True)
    np.array(encode(train_data), dtype=np.uint16).tofile(os.path.join(out_dir, "train.bin"))
    np.array(encode(val_data), dtype=np.uint16).tofile(os.path.join(out_dir, "val.bin"))
    with open(os.path.join(out_dir, "meta.pkl"), "wb") as f:
        pickle.dump({"vocab_size": vocab_size, "stoi": stoi, "itos": itos}, f)

    print(f"[{args.tier}] train: {len(train_data):,} tokens   val: {len(val_data):,} tokens")
    print(f"[{args.tier}] wrote train.bin / val.bin / meta.pkl -> {out_dir}")


if __name__ == "__main__":
    main()
