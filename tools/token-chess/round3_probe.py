"""round3_probe.py -- three exploratory probes for the Token Chess round-three
direction, all reusing the silent-fallback apparatus that round two proved out
(report: if-nobody-can-die-can-anybody-win.md).

  --mode choice      Path A, the curation gate. Sampler configs can't separate
                     players at the legality floor -- can CHOICE? Each turn the
                     harness rejection-samples Daydream until it holds K
                     distinct legal candidates (or a sample cap), and a picker
                     chooses: 'heuristic' (mate > capture value > check >
                     random) vs 'random' (uniform). If the heuristic picker
                     wins consistently, Daydream's legal moves vary enough in
                     quality for picking to be a skill, and round three has an
                     engine. Regular tier, python-chess arbiter + draw claims.

  --mode profile     Path C, the tool profiler. Zero-style games (fallback
                     plays both sides at ONE fixed config) through the shared
                     engine_client arbiter, so Micro and Grand variants work.
                     Ply-capped, no draw claims (perft can't see repetition) --
                     the product is the legality-by-depth curve per tier and
                     per config: book depth, floor height, config response.

  --mode realprefix  Path D-lite, depth vs distribution shift. The floor was
                     measured on the benchmark's own wandering positions. Here
                     Daydream samples from REAL corpus game prefixes truncated
                     at increasing depths. If legality on real positions stays
                     high where the benchmark's floor sits at 8-12%, the floor
                     is distribution shift (the random-walk games leave the
                     data manifold), not depth -- and retraining on more games
                     would not raise it.

Run from the worktree root, e.g.:
    uv run python tools/token-chess/round3_probe.py --mode choice --games 4 \
        --log_dir tools/token-chess/evidence/round3-probe
    uv run python tools/token-chess/round3_probe.py --mode profile --tier grand \
        --temperature 0.5 --soft_cap 5.0 --log_dir tools/token-chess/evidence/round3-probe
    uv run python tools/token-chess/round3_probe.py --mode realprefix --device cpu \
        --log_dir tools/token-chess/evidence/round3-probe
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
from engine_client import Engine  # noqa: E402
from harness import TIERS, DaydreamPlayer  # noqa: E402

from players import FALLBACK_CONFIG  # noqa: E402

MAX_PLIES = 300
PIECE_VALUE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def _sample(daydream: DaydreamPlayer, moves: list, config: dict) -> str:
    game_prefix = (" ".join(moves) + " ") if moves else "\n"
    return daydream.sample_candidate_move(
        game_prefix, temperature=config["temperature"], soft_cap=config["soft_cap"]
    )


# ---------------------------------------------------------------- choice mode

def _heuristic_pick(board: chess.Board, candidates: list, rng: random.Random) -> str:
    """Mate > biggest capture > check > random. The cheapest possible chess
    judgment -- if even this separates from uniform-random picking, choice is
    a skill worth benchmarking."""
    best, best_score = [], -1.0
    for uci in candidates:
        move = chess.Move.from_uci(uci)
        board.push(move)
        mate = board.is_checkmate()
        board.pop()
        if mate:
            return uci
        score = 0.0
        if board.is_capture(move):
            captured = board.piece_at(move.to_square)
            score += 10.0 * (PIECE_VALUE.get(captured.piece_type, 1) if captured else 1)  # en passant -> pawn
        if board.gives_check(move):
            score += 1.0
        if score > best_score:
            best, best_score = [uci], score
        elif score == best_score:
            best.append(uci)
    return rng.choice(best)


def _collect_candidates(daydream, moves, legal, k, sample_cap):
    candidates, samples = [], 0
    while len(candidates) < k and samples < sample_cap:
        cand = _sample(daydream, moves, FALLBACK_CONFIG)
        samples += 1
        if cand in legal and cand not in candidates:
            candidates.append(cand)
    return candidates, samples


def play_choice_game(daydream, pickers: dict, k: int, sample_cap: int, rng) -> dict:
    board = chess.Board()
    moves, move_records = [], []
    termination, winner = "ply_cap", None
    for ply in range(MAX_PLIES):
        outcome = board.outcome(claim_draw=True)
        if outcome is not None:
            termination = outcome.termination.name.lower()
            winner = {True: "white", False: "black", None: None}[outcome.winner]
            break
        side = "white" if ply % 2 == 0 else "black"
        legal = [m.uci() for m in board.legal_moves]
        candidates, samples = _collect_candidates(daydream, moves, legal, k, sample_cap)
        if not candidates:
            picked, source = rng.choice(legal), "forced_random"
        else:
            source = "picked"
            picked = (_heuristic_pick(board, candidates, rng) if pickers[side] == "heuristic"
                      else rng.choice(candidates))
        move_records.append({"ply": ply, "side": side, "samples": samples,
                             "candidates": candidates, "picked": picked, "source": source})
        moves.append(picked)
        board.push_uci(picked)
    return {"mode": "choice", "termination": termination, "winner": winner,
            "plies": len(moves), "pickers": dict(pickers), "k": k,
            "final_fen": board.fen(), "moves": move_records}


# --------------------------------------------------------------- profile mode

def play_profile_game(daydream, tier: str, config: dict, ply_cap: int,
                      resample_cap: int, rng) -> dict:
    tier_cfg = TIERS[tier]
    engine = Engine(tier_cfg["variant"], tier_cfg["variants_ini"])
    moves, move_records = [], []
    termination = "ply_cap"
    try:
        for ply in range(ply_cap):
            legal = engine.legal_moves(moves)
            if not legal:
                termination = "no_legal_moves"  # mate or stalemate; perft can't say which
                break
            samples, landed = 0, None
            for _ in range(resample_cap):
                cand = _sample(daydream, moves, config)
                samples += 1
                if cand in legal:
                    landed = cand
                    break
            move_records.append({"ply": ply, "samples": samples, "legal_landed": landed is not None})
            moves.append(landed if landed is not None else rng.choice(legal))
    finally:
        engine.close()
    return {"mode": "profile", "tier": tier, "config": dict(config),
            "termination": termination, "plies": len(moves),
            "moves_uci": moves,  # deep-band legality can be inflated by repetition loops; the move list makes that checkable
            "moves": move_records}


# ------------------------------------------------------------ realprefix mode

def run_realprefix(daydream, games_path: str, n_games: int, depths: list,
                   samples_per_pos: int, rng, log_dir) -> None:
    with open(games_path) as f:
        lines = [ln.split() for ln in f if ln.strip()]
    lengths = sorted(len(ln) for ln in lines)
    pct = lambda p: lengths[int(p * (len(lengths) - 1))]  # noqa: E731
    print(f"corpus: {len(lines)} games, ply length p10/p50/p90/p99 = "
          f"{pct(.10)}/{pct(.50)}/{pct(.90)}/{pct(.99)}, max {lengths[-1]}")

    picked = rng.sample(lines, min(n_games, len(lines)))
    by_depth = {d: {"hits": 0, "samples": 0, "positions": 0} for d in depths}
    for game in picked:
        board = chess.Board()
        ok = True
        for d in depths:
            if d > len(game) - 1:
                break
            try:
                while board.ply() < d:
                    board.push_uci(game[board.ply()])
            except ValueError:
                ok = False  # corpus line the arbiter disagrees with; skip rest of game
            if not ok:
                break
            legal = [m.uci() for m in board.legal_moves]
            if not legal:
                break
            e = by_depth[d]
            e["positions"] += 1
            for _ in range(samples_per_pos):
                cand = _sample(daydream, game[:d], FALLBACK_CONFIG)
                e["samples"] += 1
                e["hits"] += 1 if cand in legal else 0

    print("\nreal-prefix legality at depth (default config):")
    results = {}
    for d in depths:
        e = by_depth[d]
        rate = e["hits"] / e["samples"] if e["samples"] else None
        results[d] = {**e, "legality": rate}
        shown = f"{rate:.1%}" if rate is not None else "--"
        print(f"  ply {d:3d}: {e['hits']}/{e['samples']} = {shown}  ({e['positions']} positions)")
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "realprefix.json"), "w") as f:
            json.dump({"mode": "realprefix", "games_sampled": len(picked),
                       "samples_per_pos": samples_per_pos,
                       "corpus_length_pct": {"p10": pct(.10), "p50": pct(.50), "p90": pct(.90), "p99": pct(.99)},
                       "by_depth": results}, f, indent=2)


# ------------------------------------------------------------------- summary

def _band_table(move_records, key_samples, key_hit, width=50):
    bands = {}
    for m in move_records:
        lo = (m["ply"] // width) * width
        b = bands.setdefault(f"{lo:03d}-{lo + width - 1:03d}", {"s": 0, "h": 0})
        b["s"] += m[key_samples]
        b["h"] += 1 if m[key_hit] else 0
    return bands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["choice", "profile", "realprefix"])
    ap.add_argument("--games", type=int, default=4)
    ap.add_argument("--tier", default="regular", choices=list(TIERS.keys()))
    ap.add_argument("--out_dir", default=None, help="checkpoint dir; defaults to projects/daydream/runs/<tier>-r1")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--log_dir", default=None)
    # choice mode
    ap.add_argument("--k", type=int, default=3, help="target candidate count per turn")
    ap.add_argument("--sample_cap", type=int, default=40, help="max Daydream draws per turn")
    # profile mode
    ap.add_argument("--temperature", type=float, default=FALLBACK_CONFIG["temperature"])
    ap.add_argument("--soft_cap", type=float, default=FALLBACK_CONFIG["soft_cap"], help="<=0 disables")
    ap.add_argument("--ply_cap", type=int, default=200)
    ap.add_argument("--resample_cap", type=int, default=30)
    # realprefix mode
    ap.add_argument("--games_path", default="projects/daydream/data/regular/games.txt")
    ap.add_argument("--prefix_games", type=int, default=30)
    ap.add_argument("--depths", default="0,20,40,60,80,100,120")
    ap.add_argument("--samples_per_pos", type=int, default=10)
    args = ap.parse_args()

    out_dir = args.out_dir or f"projects/daydream/runs/{args.tier}-r1"
    daydream = DaydreamPlayer(out_dir, device=args.device)
    rng = random.Random(args.seed)

    if args.mode == "realprefix":
        run_realprefix(daydream, args.games_path, args.prefix_games,
                       [int(d) for d in args.depths.split(",")], args.samples_per_pos, rng, args.log_dir)
        return

    for g in range(args.games):
        if args.mode == "choice":
            pickers = ({"white": "heuristic", "black": "random"} if g % 2 == 0
                       else {"white": "random", "black": "heuristic"})
            result = play_choice_game(daydream, pickers, args.k, args.sample_cap, rng)
            print(f"game {g + 1}/{args.games} [white={pickers['white']} black={pickers['black']}]: "
                  f"{result['termination']}, winner={result['winner']}, plies={result['plies']}")
            tag = f"choice-game-{g + 1:03d}"
        else:
            config = {"temperature": args.temperature,
                      "soft_cap": args.soft_cap if args.soft_cap and args.soft_cap > 0 else None}
            result = play_profile_game(daydream, args.tier, config, args.ply_cap, args.resample_cap, rng)
            print(f"game {g + 1}/{args.games} [{args.tier} t={config['temperature']} cap={config['soft_cap']}]: "
                  f"{result['termination']}, plies={result['plies']}")
            for band, b in sorted(_band_table(result["moves"], "samples", "legal_landed").items()):
                print(f"    plies {band}: legality {b['h']}/{b['s']} = {b['h'] / b['s']:.1%}" if b["s"] else "")
            cap_tag = "none" if config["soft_cap"] is None else f"{config['soft_cap']:g}"
            tag = f"profile-{args.tier}-t{config['temperature']:g}-cap{cap_tag}-game-{g + 1:03d}"
        if args.log_dir:
            os.makedirs(args.log_dir, exist_ok=True)
            with open(os.path.join(args.log_dir, f"{tag}.json"), "w") as f:
                json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
