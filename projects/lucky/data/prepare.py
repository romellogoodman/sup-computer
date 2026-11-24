"""prepare.py -- tokenize the committed draws for one game.

Stage 3 of the lucky pipeline (fetch -> crosscheck -> prepare). Reads
data/<game>/draws.csv and writes, into data/<game>/tokenized/:

  draws.bin   every draw in time order, one row of tokens per draw (uint16)
  meta.pkl    vocab (stoi/itos, the studio's meta.pkl contract, ADR-0012),
              tokens_per_draw, and the split boundaries

The split is by time, never shuffled: the oldest 80% of draws train, the
next 10% pick the stopping step (val), and the most recent 10% are the
held-out test every reported number comes from. One file holds all three
so a held-out draw's history can reach back across the boundary into the
real draws before it.

Powerball whites are stored sorted, as published. The loader reshuffles
them every epoch (train.py); nothing here fixes an order.

Run from the repo root:
    uv run python projects/lucky/data/prepare.py --game pick3
    uv run python projects/lucky/data/prepare.py --game powerball
"""

import argparse
import csv
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from common import GAMES, encode_draw  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--game", required=True, choices=list(GAMES))
    args = ap.parse_args()
    g = GAMES[args.game]

    with open(os.path.join(HERE, args.game, "draws.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    if args.game == "pick3":
        draws = [r["digits"] for r in rows]
    else:
        draws = [([int(r[f"w{i}"]) for i in range(1, 6)], int(r["red"])) for r in rows]
    tokens = np.array([encode_draw(args.game, d) for d in draws], dtype=np.uint16)

    n = len(tokens)
    n_test = n // 10
    n_val = n // 10
    n_train = n - n_val - n_test
    meta = {
        "game": args.game,
        "vocab_size": len(g["vocab"]),
        "stoi": g["stoi"],
        "itos": {i: t for i, t in enumerate(g["vocab"])},
        "arm": g["arm"],
        "tokens_per_draw": g["tokens_per_draw"],
        "n_draws": n,
        "splits": {"train": [0, n_train], "val": [n_train, n_train + n_val], "test": [n_train + n_val, n]},
        "dates": {"first": rows[0]["date"], "train_last": rows[n_train - 1]["date"],
                  "val_last": rows[n_train + n_val - 1]["date"], "last": rows[-1]["date"]},
    }
    out = os.path.join(HERE, args.game, "tokenized")
    os.makedirs(out, exist_ok=True)
    tokens.tofile(os.path.join(out, "draws.bin"))
    with open(os.path.join(out, "meta.pkl"), "wb") as f:
        pickle.dump(meta, f)
    print(f"{args.game}: {n} draws x {g['tokens_per_draw']} tokens = {tokens.size} tokens, vocab {meta['vocab_size']}")
    print(f"  train {n_train} ({meta['dates']['first']} .. {meta['dates']['train_last']})")
    print(f"  val   {n_val} (.. {meta['dates']['val_last']})")
    print(f"  test  {n_test} (.. {meta['dates']['last']})")


if __name__ == "__main__":
    main()
