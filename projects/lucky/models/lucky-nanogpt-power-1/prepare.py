"""prepare.py -- tokenize this folder's draws.csv (frozen copy, lucky-nanogpt-power-1).

Writes draws.bin (every draw in time order, one row of tokens per draw) and
meta.pkl (vocab, tokens_per_draw, split boundaries) beside this file.

The split is by time: the oldest 80% of draws train, the next 10% pick the
stopping step, the most recent 10% are the held-out test.

    python prepare.py
"""

import csv
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import GAMES, encode_draw  # noqa: E402

GAME = "powerball"


def main():
    g = GAMES[GAME]
    with open(os.path.join(HERE, "draws.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    if GAME == "pick3":
        draws = [r["digits"] for r in rows]
    else:
        draws = [([int(r[f"w{i}"]) for i in range(1, 6)], int(r["red"])) for r in rows]
    tokens = np.array([encode_draw(GAME, d) for d in draws], dtype=np.uint16)

    n = len(tokens)
    n_test = n // 10
    n_val = n // 10
    n_train = n - n_val - n_test
    meta = {
        "game": GAME,
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
    tokens.tofile(os.path.join(HERE, "draws.bin"))
    with open(os.path.join(HERE, "meta.pkl"), "wb") as f:
        pickle.dump(meta, f)
    print(f"{GAME}: {n} draws x {g['tokens_per_draw']} tokens, vocab {meta['vocab_size']}; "
          f"train {n_train} / val {n_val} / test {n_test} (test ends {meta['dates']['last']})")


if __name__ == "__main__":
    main()
