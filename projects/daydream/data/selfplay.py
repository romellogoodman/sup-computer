"""
selfplay.py -- shared Fairy-Stockfish self-play corpus generator for the
synthetic tiers (Micro, Grand). No human corpus exists for non-standard
board sizes, so both tiers' corpora come from Fairy-Stockfish playing
itself under the tier's variant rules -- pure self-play, not
strength-varied (see the daydream design plan: the dreaming effect is
meant to come from the trained model + sampler at inference time, not
baked into the training corpus).

Drives the engine directly over its UCI stdin/stdout pipe rather than
depending on any Python chess-variant library, since python-chess doesn't
know about Fairy-Stockfish's custom variants (gardner, grand12).

Usage (run from the repo root):
    uv run python projects/daydream/data/selfplay.py \
        --variant gardner --games 2000 --out projects/daydream/data/micro/games.txt

    uv run python projects/daydream/data/selfplay.py \
        --variant grand12 --variants-ini projects/daydream/engine/variants.ini \
        --games 2000 --out projects/daydream/data/grand/games.txt
"""
from __future__ import annotations

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine_client import Engine  # noqa: E402  -- shared UCI client, also used by harness.py

MAX_PLIES = 150  # safety valve against pathological non-terminating games
REPETITION_WINDOW = 8  # if the last 8 moves == the 8 before that, the engine is shuffling -- stop


def is_shuffling(moves: list) -> bool:
    """True if the last REPETITION_WINDOW moves exactly repeat the
    REPETITION_WINDOW before that -- the deterministic-search version of
    'both sides just shuffle back and forth,' cheap to detect without
    tracking full board hashes."""
    n = len(moves)
    w = REPETITION_WINDOW
    if n < 2 * w:
        return False
    return moves[n - w:] == moves[n - 2 * w:n - w]


def play_one_game(variant: str, variants_ini: str, depth: int, random_opening_plies: int, rng: random.Random) -> str:
    engine = Engine(variant, variants_ini)
    moves = []
    try:
        # Randomize the opening so self-play games don't all collapse to the
        # same deterministic line (fixed low-depth search has no exploration
        # noise on its own) -- then let the engine search take over.
        for _ in range(random_opening_plies):
            legal = engine.legal_moves(moves)
            if not legal:
                break
            moves.append(rng.choice(legal))
        for _ in range(MAX_PLIES - len(moves)):
            move = engine.best_move(moves, depth=depth)
            if move is None:
                break
            moves.append(move)
            if is_shuffling(moves):
                break
    finally:
        engine.close()
    return " ".join(moves)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True, help="e.g. gardner, grand12")
    ap.add_argument("--variants-ini", default="", help="path to a custom variants.ini, if needed")
    ap.add_argument("--games", type=int, default=2000)
    ap.add_argument("--depth", type=int, default=6, help="bounded search depth -- speed, not strength reduction")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-plies", type=int, default=6)
    ap.add_argument("--random-opening-plies", type=int, default=6,
                     help="random legal plies before engine search takes over -- the only source "
                          "of game-to-game diversity, since fixed-depth search is deterministic")
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    kept = 0
    with open(args.out, "w") as f:
        for i in range(args.games):
            line = play_one_game(args.variant, args.variants_ini, args.depth, args.random_opening_plies, rng)
            n_plies = len(line.split()) if line else 0
            if n_plies >= args.min_plies:
                f.write(line + "\n")
                kept += 1
            if (i + 1) % 100 == 0:
                print(f"  played {i + 1:,}/{args.games:,}, kept {kept:,}")

    print(f"done: played {args.games:,} games, kept {kept:,} -> {args.out}")


if __name__ == "__main__":
    main()
