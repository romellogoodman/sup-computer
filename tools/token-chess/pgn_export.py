"""pgn_export.py -- turn Token Chess evidence JSONs into replayable PGNs.

Every round's evidence records complete move sequences, but as JSON — this
exports them to the format chess viewers open. Handles all three record
shapes: game.py (round one: the attempt log, accepted moves in order),
round2/round3 probes (per-move records), and game3.py (rounds three+:
per-turn records with picked moves). Regular tier only — Micro/Grand UCI
square names aren't standard chess and no viewer would accept them.

Run from the repo root:
    uv run python tools/token-chess/pgn_export.py \
        "tools/token-chess/evidence/round3-*/game-*.json" \
        --out_dir tools/token-chess/evidence/pgn
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import chess
import chess.pgn

RESULT = {"white": "1-0", "black": "0-1", None: "1/2-1/2"}


def moves_from_record(g: dict):
    if "turns" in g:  # game3.py (rounds 3+)
        return [t["picked"] for t in g["turns"]]
    if "moves" in g and g["moves"] and isinstance(g["moves"][0], dict):
        m = g["moves"][0]
        key = "picked" if "picked" in m else "move"  # round3 choice probe / round2 probe
        return [mv[key] for mv in g["moves"]]
    if "attempts" in g:  # game.py (round one): legal attempts, in order, are the game
        return [a["move"] for a in g["attempts"] if a["legal"]]
    return None


def export(path: str, out_dir: str) -> str | None:
    with open(path) as f:
        g = json.load(f)
    if g.get("tier", "regular") != "regular" or g.get("mode") == "profile":
        return None
    ucis = moves_from_record(g)
    if not ucis:
        return None

    game = chess.pgn.Game()
    tag = os.path.basename(os.path.dirname(path))
    game.headers["Event"] = f"Token Chess — {tag}"
    game.headers["Site"] = "sup computer (Daydream-exclusive moves)"
    game.headers["White"] = g.get("white_player", g.get("players", {}).get("white", "?"))
    game.headers["Black"] = g.get("black_player", g.get("players", {}).get("black", "?"))
    game.headers["Result"] = RESULT.get(g.get("winner"), "*")
    outcome = g.get("outcome", g.get("termination", "?"))
    game.headers["Termination"] = outcome
    if g.get("adjudication"):
        cp = g["adjudication"].get("white_cp")
        if cp is not None:
            game.headers["Termination"] += f" (engine adjudication, {cp:+d}cp for white)"

    node = game
    board = chess.Board()
    for uci in ucis:
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            return None  # Micro/Grand square names — not standard chess, no PGN
        if move not in board.legal_moves:
            return None  # corrupt / non-standard record; skip rather than emit a broken PGN
        node = node.add_variation(move)
        board.push(move)
    game.headers["PlyCount"] = str(len(ucis))

    name = f"{tag}--{os.path.splitext(os.path.basename(path))[0]}.pgn"
    dest = os.path.join(out_dir, name)
    os.makedirs(out_dir, exist_ok=True)
    with open(dest, "w") as f:
        print(game, file=f)
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("patterns", nargs="+", help="evidence JSON globs")
    ap.add_argument("--out_dir", default="tools/token-chess/evidence/pgn")
    args = ap.parse_args()

    done = skipped = 0
    for pattern in args.patterns:
        for path in sorted(glob.glob(pattern, recursive=True)):
            dest = export(path, args.out_dir)
            if dest:
                done += 1
            else:
                skipped += 1
    print(f"exported {done} PGNs to {args.out_dir} ({skipped} skipped: non-regular tier, "
          f"profile runs, or unparseable records)")


if __name__ == "__main__":
    main()
