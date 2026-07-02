"""
fetch_filtered.py (FROZEN release copy) -- streams a Lichess monthly PGN
dump and writes an Elo-filtered, UCI-converted corpus, all paths relative
to THIS folder. See the working copy at
projects/daydream/data/regular/fetch_filtered.py for full documentation;
this is an unmodified vendored copy so the frozen folder has no dependency
on the project root.

Run from inside this folder:
    python fetch_filtered.py
"""
import argparse
import io
import os

import chess
import chess.pgn
import requests
import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "games.txt")

DEFAULT_MONTH = "2018-01"
DEFAULT_MIN_ELO = 1400
DEFAULT_MAX_ELO = 1800
DEFAULT_TARGET_GAMES = 15_000
DEFAULT_MIN_MOVES = 10


def dump_url(month: str) -> str:
    return f"https://database.lichess.org/standard/lichess_db_standard_rated_{month}.pgn.zst"


def stream_games(month: str):
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


def qualifies(game: chess.pgn.Game, min_elo: int, max_elo: int) -> bool:
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


def game_to_uci_line(game: chess.pgn.Game, min_moves: int):
    ucis = [move.uci() for move in game.mainline_moves()]
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
    kept = 0
    seen = 0
    with open(args.out, "w") as f:
        for game in stream_games(args.month):
            seen += 1
            if seen % 20_000 == 0:
                print(f"  scanned {seen:,} games, kept {kept:,}")
            if not qualifies(game, args.min_elo, args.max_elo):
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
