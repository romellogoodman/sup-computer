"""round2_probe.py -- exploratory probe for the Token Chess round-two design
question: what do games look like when they always complete?

Round one's finding was that every game ends in budget-exhaustion forfeit --
no game ever reached a natural chess ending, so we have zero data on what a
*completed* Daydream game even looks like. Before adopting the round-two
mechanics (income per turn + silent rejection-sampling fallback instead of
forfeit), this probe answers two questions:

  --mode zero    Game zero: NO players at all. Both sides are the silent
                 fallback itself (rejection-sample Daydream at the default
                 config up to a cap, then a uniform-random legal move).
                 Shows the destination: are completed Daydream games
                 decisive chess or 200-ply shuffle draws? Also extends the
                 legality-by-depth curve past the forfeit wall (~ply 40)
                 into plies no round-one game ever reached.

  --mode round2  The round-two loop with mock players: bankable income per
                 turn, player attempts cost 1 token each, and when the bank
                 runs dry the silent fallback plays the move (the player is
                 never told -- from its side, unspent failure just ends the
                 turn). Measures control rate (player-landed vs fallback
                 moves) and whether mock:adaptive still beats mock:random
                 when nobody can die.

Probe scope: regular tier only. Legality and game termination come from
python-chess rather than the shared engine_client arbiter -- identical rules
for standard chess, and it adds the draw detection (threefold repetition,
fifty-move) that the perft-based arbiter cannot see and that completed games
need. A real round-two harness would extend engine_client instead.

Run from the worktree root:
    uv run python tools/token-chess/round2_probe.py --mode zero --games 3
    uv run python tools/token-chess/round2_probe.py --mode round2 --games 4 \
        --income 4 --log_dir tools/token-chess/evidence/round2-probe
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "projects", "daydream"))
sys.path.insert(0, HERE)

import chess  # noqa: E402
from harness import DaydreamPlayer  # noqa: E402

from players import FALLBACK_CONFIG, AdaptivePlayer, RandomPlayer  # noqa: E402


def make_player(spec: str, seed: int = 0):
    """mock:adaptive | mock:random | lmstudio:<model-id> -- same specs as
    game.py's make_player, minus the reserved anthropic: kind."""
    kind, _, arg = spec.partition(":")
    if kind == "mock":
        return AdaptivePlayer() if arg == "adaptive" else RandomPlayer(seed=seed)
    if kind == "lmstudio":
        from steer import OpenAICompatClient  # noqa: PLC0415

        from players import LLMPlayer  # noqa: PLC0415
        return LLMPlayer(OpenAICompatClient(arg))
    raise ValueError(f"unknown player spec: {spec}")

MAX_PLIES = 300
FALLBACK_RESAMPLE_CAP = 30  # silent-fallback rejection budget before forcing uniform-random


def _sample(daydream: DaydreamPlayer, moves: list, config: dict) -> str:
    game_prefix = (" ".join(moves) + " ") if moves else "\n"
    return daydream.sample_candidate_move(
        game_prefix, temperature=config["temperature"], soft_cap=config["soft_cap"]
    )


def _fallback(daydream: DaydreamPlayer, moves: list, legal: list, rng: random.Random) -> dict:
    """The silent fallback: rejection-sample at the default config until a
    legal move lands or the cap is hit, then force uniform-random legal."""
    for i in range(1, FALLBACK_RESAMPLE_CAP + 1):
        candidate = _sample(daydream, moves, FALLBACK_CONFIG)
        if candidate in legal:
            return {"move": candidate, "source": "fallback_sampled", "fallback_samples": i}
    return {"move": rng.choice(legal), "source": "fallback_random", "fallback_samples": FALLBACK_RESAMPLE_CAP}


def play_game(mode: str, daydream: DaydreamPlayer, players: dict, income: int,
              starting_bank: int, rng: random.Random) -> dict:
    board = chess.Board()
    moves = []
    banks = {"white": starting_bank, "black": starting_bank}
    move_records = []
    termination, winner = "ply_cap", None

    for ply in range(MAX_PLIES):
        outcome = board.outcome(claim_draw=True)
        if outcome is not None:
            termination = outcome.termination.name.lower()
            winner = {True: "white", False: "black", None: None}[outcome.winner]
            break
        side = "white" if ply % 2 == 0 else "black"
        legal = [m.uci() for m in board.legal_moves]
        record = {"ply": ply, "side": side, "attempts": 0}

        landed = None
        if mode == "round2":
            banks[side] += income
            player = players[side]
            transcript_this_turn = []
            while banks[side] > 0:
                config = player.choose_config(banks[side], transcript_this_turn)
                banks[side] -= 1
                record["attempts"] += 1
                candidate = _sample(daydream, moves, config)
                is_legal = candidate in legal
                transcript_this_turn.append({**config, "move": candidate, "legal": is_legal})
                if is_legal:
                    landed = candidate
                    break

        if landed is not None:
            record.update({"move": landed, "source": "player"})
        else:
            record.update(_fallback(daydream, moves, legal, rng))
        if mode == "round2":
            record["bank_after"] = banks[side]

        moves.append(record["move"])
        board.push_uci(record["move"])
        move_records.append(record)

    return {
        "mode": mode,
        "termination": termination,
        "winner": winner,
        "plies": len(moves),
        "final_fen": board.fen(),
        "banks_final": dict(banks) if mode == "round2" else None,
        "moves": move_records,
    }


def _band(ply: int) -> str:
    lo = (ply // 10) * 10
    return f"{lo:03d}-{lo + 9:03d}"


def summarize(result: dict) -> str:
    lines = [f"  {result['termination']}, winner={result['winner']}, plies={result['plies']}"]
    bands = {}
    for m in result["moves"]:
        b = bands.setdefault(_band(m["ply"]), {"moves": 0, "samples": 0, "legal_hits": 0,
                                               "player": 0, "fallback_sampled": 0, "fallback_random": 0})
        b["moves"] += 1
        b[m["source"] if m["source"] != "player" else "player"] += 1
        # every fallback sample is a draw at the default config; a
        # fallback_sampled move means exactly one of them landed legal
        if m["source"] in ("fallback_sampled", "fallback_random"):
            b["samples"] += m["fallback_samples"]
            b["legal_hits"] += 1 if m["source"] == "fallback_sampled" else 0
    for band in sorted(bands):
        b = bands[band]
        legality = f"{b['legal_hits'] / b['samples']:.0%}" if b["samples"] else "  --"
        lines.append(
            f"    plies {band}: {b['moves']:2d} moves | player {b['player']:2d} "
            f"| fb-sampled {b['fallback_sampled']:2d} | fb-random {b['fallback_random']:2d} "
            f"| default-config legality {legality}"
        )
    return "\n".join(lines)


def control_stats(result: dict) -> dict:
    stats = {}
    for side in ("white", "black"):
        ms = [m for m in result["moves"] if m["side"] == side]
        stats[side] = {
            "moves": len(ms),
            "player_controlled": sum(1 for m in ms if m["source"] == "player"),
            "tokens_spent": sum(m["attempts"] for m in ms),
        }
        stats[side]["control_rate"] = (
            stats[side]["player_controlled"] / len(ms) if ms else 0.0
        )
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["zero", "round2"])
    ap.add_argument("--games", type=int, default=3)
    ap.add_argument("--out_dir", default="projects/daydream/runs/regular-r1")
    ap.add_argument("--income", type=int, default=4, help="tokens added to a player's bank each of its turns")
    ap.add_argument("--starting_bank", type=int, default=0)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--log_dir", default=None, help="write per-game JSON records here")
    ap.add_argument("--white", default="mock:adaptive", help="round2 player spec (see make_player)")
    ap.add_argument("--black", default="mock:random")
    args = ap.parse_args()

    daydream = DaydreamPlayer(args.out_dir, device=args.device)
    rng = random.Random(args.seed)

    for g in range(args.games):
        if args.mode == "round2":
            # Alternate colors so neither spec owns white.
            specs = (args.white, args.black) if g % 2 == 0 else (args.black, args.white)
            players = {"white": make_player(specs[0], seed=g), "black": make_player(specs[1], seed=g)}
            spec = {"white": specs[0], "black": specs[1]}
        else:
            players, spec = None, {"white": "fallback", "black": "fallback"}

        result = play_game(args.mode, daydream, players, args.income, args.starting_bank, rng)
        result["players"] = spec
        print(f"game {g + 1}/{args.games} [{spec['white']} vs {spec['black']}]")
        print(summarize(result))
        if args.mode == "round2":
            for side, s in control_stats(result).items():
                print(f"    {side} ({spec[side]}): control {s['player_controlled']}/{s['moves']} "
                      f"({s['control_rate']:.0%}), spent {s['tokens_spent']} tokens")
            result["control_stats"] = control_stats(result)

        if args.log_dir:
            os.makedirs(args.log_dir, exist_ok=True)
            path = os.path.join(args.log_dir, f"{args.mode}-game-{g + 1:03d}.json")
            with open(path, "w") as f:
                json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
