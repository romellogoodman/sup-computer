"""
fetch_filtered.py -- streams a Lichess monthly PGN dump and writes a small,
Elo-filtered, UCI-converted corpus for Regular (8x8) without ever storing
the full multi-GB dump on disk.

The Lichess open database (database.lichess.org) has no built-in Elo filter
and no size cap -- every game for the month is in one file. We stream-decode
the zstd-compressed PGN directly over HTTP, parse games one at a time with
python-chess, keep only games where both players are rated ~1400-1800 (the
mid-band: coherent enough to have positional shape, loose enough to produce
the near-miss texture daydream wants -- see the daydream design plan),
convert each kept game's move list from SAN to UCI, and stop once we have
enough qualifying games. Nothing outside the kept games ever touches disk.

Per the project plan: start with one filtered month, don't pre-commit to a
game count beyond a reasonable starting corpus -- scale up later only if
harness verification shows the model is data-starved.

Run from the repo root:
    uv run python projects/daydream/data/regular/fetch_filtered.py
"""
from __future__ import annotations

import argparse
import io
import os

import chess
import chess.pgn
import requests
import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "games.txt")

DEFAULT_MONTH = "2018-01"  # small-ish, well-established, definitely-archived month
DEFAULT_MIN_ELO = 1400
DEFAULT_MAX_ELO = 1800
DEFAULT_TARGET_GAMES = 50_000
DEFAULT_MIN_MOVES = 10  # skip aborted/near-instant games


def dump_url(month: str) -> str:
    return f"https://database.lichess.org/standard/lichess_db_standard_rated_{month}.pgn.zst"


def stream_games(month: str):
    """Yield python-chess Game objects, decompressed and parsed on the fly."""
    url = dump_url(month)
    resp = requests.get(url, stream=True, timeout=30)
    resp.raise_for_status()
    dctx = zstandard.ZstdDecompressor()
    with dctx.stream_reader(resp.raw) as reader:
        text_stream = io.TextIOWrapper(reader, encoding="utf-8", errors="replace")
        while True:
            game = chess.pgn.read_game(text_stream)
            if game is None:
                return
            yield game
    resp.close()


def qualifies(game: chess.pgn.Game, min_elo: int, max_elo: int, min_moves: int) -> bool:
    headers = game.headers
    try:
        white_elo = int(headers.get("WhiteElo", "0"))
        black_elo = int(headers.get("BlackElo", "0"))
    except ValueError:
        return False
    if not (min_elo <= white_elo <= max_elo and min_elo <= black_elo <= max_elo):
        return False
    if headers.get("Termination") == "Abandoned":
        return False
    return True


def game_to_uci_line(game: chess.pgn.Game, min_moves: int) -> str | None:
    board = game.board()
    ucis = []
    for move in game.mainline_moves():
        ucis.append(move.uci())
        board.push(move)
    if len(ucis) < min_moves:
        return None
    return " ".join(ucis)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", default=DEFAULT_MONTH)
    ap.add_argument("--min-elo", type=int, default=DEFAULT_MIN_ELO)
    ap.add_argument("--max-elo", type=int, default=DEFAULT_MAX_ELO)
    ap.add_argument("--target-games", type=int, default=DEFAULT_TARGET_GAMES)
    ap.add_argument("--min-moves", type=int, default=DEFAULT_MIN_MOVES)
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()

    print(f"streaming {dump_url(args.month)}")
    print(f"filter: Elo [{args.min_elo}, {args.max_elo}], min {args.min_moves} plies, "
          f"target {args.target_games:,} games")

    kept = 0
    seen = 0
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        for game in stream_games(args.month):
            seen += 1
            if seen % 20_000 == 0:
                print(f"  scanned {seen:,} games, kept {kept:,}")
            if not qualifies(game, args.min_elo, args.max_elo, args.min_moves):
                continue
            line = game_to_uci_line(game, args.min_moves)
            if line is None:
                continue
            f.write(line + "\n")
            kept += 1
            if kept >= args.target_games:
                break

    print(f"done: scanned {seen:,} games, kept {kept:,} -> {args.out}")


if __name__ == "__main__":
    main()
