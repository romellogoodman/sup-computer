"""
dreaminess_sweep.py -- EVAL-ONLY temperature x soft_cap sweep over the three
frozen daydream checkpoints. Reuses the shared harness machinery
(DaydreamPlayer, Engine) but adds:

  * per-cell sweep over temperature x soft_cap (the "dreaminess" knobs),
  * per-ply first-try legality tracking (legality-by-ply curve),
  * captured dream transcripts (accepted move + the REJECTED illegal
    attempts, which ARE the dream texture -- kept, not discarded),
  * a free-generation sampler (model dreams a whole game unconstrained,
    no legality arbiter in the loop) to show raw hallucinated squares.

Fairy-Stockfish is the legality arbiter (FULL mode). Nothing here trains,
checkpoints, or mutates models/. Writes evidence under runs/.

Run from repo root:
    uv run python projects/daydream/dreaminess_sweep.py --tier micro
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from engine_client import Engine  # noqa: E402
from harness import DaydreamPlayer, TIERS, MAX_GAME_PLIES  # noqa: E402

TEMPS = [0.6, 0.8, 1.0, 1.2]
CAPS = [2.0, 4.0, 8.0, None]  # tight, mid, loose, off
RUN_DIR = {
    "micro": "projects/daydream/runs/micro-r1",
    "regular": "projects/daydream/runs/regular-r1",
    "grand": "projects/daydream/runs/grand-r1",
}


def play_game_instrumented(player, tier_cfg, resample_cap, opponent_skill, rng,
                           model_plays_white, capture_dream=False):
    """Like harness.play_verification_game but records per-model-ply data:
    (absolute_ply, first_try_legal, forced_random, n_attempts). If
    capture_dream, also keeps the accepted move + the rejected candidates."""
    engine = Engine(tier_cfg["variant"], tier_cfg["variants_ini"], skill_level=opponent_skill)
    moves = []
    per_ply = []            # list of dicts, one per model ply
    dream_moves = []        # optional captured transcript entries
    result = "in_progress"
    try:
        for ply in range(MAX_GAME_PLIES):
            white_to_move = ply % 2 == 0
            daydream_turn = white_to_move == model_plays_white
            legal = engine.legal_moves(moves)
            if not legal:
                result = "clean_completion"
                break
            if daydream_turn:
                proposal = player.propose_move(moves, engine, resample_cap, rng)
                first_try = proposal["accepted_attempt"] == 1
                per_ply.append({
                    "ply": ply,
                    "first_try_legal": first_try,
                    "forced_random": proposal["forced_random"],
                    "n_attempts": len(proposal["attempts"]),
                })
                if capture_dream:
                    dream_moves.append({
                        "ply": ply,
                        "played": proposal["move"],
                        "forced_random": proposal["forced_random"],
                        # rejected candidates = the dream texture
                        "rejected": proposal["attempts"][:-1] if not proposal["forced_random"] else proposal["attempts"],
                    })
                if proposal["move"] is None:
                    result = "crashed_no_legal_move"
                    break
                moves.append(proposal["move"])
            else:
                mv = engine.best_move(moves, depth=4)
                if mv is None:
                    result = "clean_completion"
                    break
                moves.append(mv)
        else:
            result = "clean_completion"
    except Exception as e:
        result = f"crashed: {e}"
    finally:
        engine.close()
    return {"result": result, "plies": len(moves), "moves": moves,
            "per_ply": per_ply, "dream_moves": dream_moves}


def free_dream(player, tier_cfg, n_chars, seed_char="\n"):
    """Pure unconstrained self-generation: no engine, no resampling. The
    model dreams a whole game string; we split into whitespace-separated
    UCI-ish tokens. Then we replay against the engine to classify each
    token legal/illegal in the position reached by the model's own LEGAL
    moves so far -- once an illegal token appears we mark the game as
    'diverged' and stop advancing the reference position (subsequent tokens
    are pure dream, off any real board)."""
    idx = torch.tensor([player.encode(seed_char)], dtype=torch.long, device=player.device)
    out = []
    for _ in range(n_chars):
        nxt = player._sample_one_char(idx, player.temperature, player.soft_cap)
        ch = player.itos[nxt]
        if ch == "\n" and out:  # end of a dreamed game
            break
        out.append(ch)
        idx = torch.cat([idx, torch.tensor([[nxt]], device=player.device)], dim=1)
    text = "".join(out).strip()
    tokens = [t for t in re.split(r"\s+", text) if t]

    # classify against engine
    engine = Engine(tier_cfg["variant"], tier_cfg["variants_ini"])
    played, diverged = [], False
    annotated = []
    try:
        for tok in tokens:
            if diverged:
                annotated.append((tok, "dream"))       # off-board, unverifiable
                continue
            legal = engine.legal_moves(played)
            if tok in legal:
                annotated.append((tok, "legal"))
                played.append(tok)
            else:
                annotated.append((tok, "illegal"))
                diverged = True
    finally:
        engine.close()
    return {"raw": text, "annotated": annotated}


def run_sweep(tier, games, resample_cap, opponent_skill, device, seed, out_json, capture_dir):
    tier_cfg = TIERS[tier]
    player = DaydreamPlayer(RUN_DIR[tier], device=device)
    rng = random.Random(seed)
    t0 = time.time()

    cells = {}
    ply_legal = {}  # (temp,cap) -> {ply: [n_legal, n_total]}
    for temp in TEMPS:
        for cap in CAPS:
            player.temperature = temp
            player.soft_cap = cap
            key = f"t{temp}_c{cap}"
            clean = 0
            n_legal = n_moves = n_forced = 0
            pl = {}
            for g in range(games):
                r = play_game_instrumented(player, tier_cfg, resample_cap,
                                           opponent_skill, rng, model_plays_white=(g % 2 == 0))
                if r["result"] == "clean_completion":
                    clean += 1
                for rec in r["per_ply"]:
                    n_moves += 1
                    if rec["first_try_legal"]:
                        n_legal += 1
                    if rec["forced_random"]:
                        n_forced += 1
                    bucket = pl.setdefault(rec["ply"], [0, 0])
                    bucket[1] += 1
                    if rec["first_try_legal"]:
                        bucket[0] += 1
            cells[key] = {
                "temp": temp, "cap": cap, "games": games,
                "clean_completion": clean,
                "clean_rate": clean / games,
                "first_try_legal": n_legal,
                "model_moves": n_moves,
                "legal_rate": (n_legal / n_moves) if n_moves else 0.0,
                "forced_random": n_forced,
            }
            ply_legal[key] = pl
            print(f"[{tier}] {key}: clean {clean}/{games}, "
                  f"legal {n_legal}/{n_moves} ({100*(n_legal/n_moves if n_moves else 0):.1f}%), "
                  f"forced {n_forced}  ({time.time()-t0:.0f}s)")

    result = {"tier": tier, "games_per_cell": games, "temps": TEMPS,
              "caps": [str(c) for c in CAPS], "cells": cells,
              "ply_legal": {k: {str(p): v for p, v in d.items()} for k, d in ply_legal.items()},
              "elapsed_s": time.time() - t0}
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[{tier}] wrote {out_json} in {time.time()-t0:.0f}s")

    # capture representative dream transcripts at 3 corners
    corners = {
        "sharp (temp 0.6, cap off)": (0.6, None),
        "mid (temp 1.0, cap 4)": (1.0, 4.0),
        "flat (temp 1.2, cap 2)": (1.2, 2.0),
    }
    lines = [f"## {tier} -- dream transcripts\n"]
    for label, (temp, cap) in corners.items():
        player.temperature = temp
        player.soft_cap = cap
        lines.append(f"### {label}\n")
        # one instrumented game with full attempts
        r = play_game_instrumented(player, tier_cfg, resample_cap, opponent_skill,
                                   rng, model_plays_white=True, capture_dream=True)
        lines.append(f"*Harness game vs Fairy-Stockfish (model = White), "
                     f"{r['result']}, {r['plies']} plies. "
                     f"Each model ply shows the played move and the rejected "
                     f"illegal dream-attempts before it:*\n")
        for dm in r["dream_moves"][:8]:
            rej = " ".join(dm["rejected"][:8]) if dm["rejected"] else "(first-try legal)"
            forced = " [FORCED-RANDOM]" if dm["forced_random"] else ""
            lines.append(f"- ply {dm['ply']}: **{dm['played']}**{forced}  "
                         f"— dreamed & rejected: `{rej}`")
        lines.append("")
        # two free-generation dreams (no engine in the loop)
        lines.append("*Free self-generation (no arbiter in the loop; "
                     "legal / illegal / dream classified afterward):*\n")
        for _ in range(2):
            fd = free_dream(player, tier_cfg, n_chars=300)
            marks = {"legal": "o", "illegal": "x", "dream": "~"}
            annotated = " ".join(f"{tok}[{marks[s]}]" for tok, s in fd["annotated"][:24])
            lines.append(f"- `{annotated}`")
        lines.append("")

    cap_path = os.path.join(capture_dir, f"{tier}-transcripts.md")
    with open(cap_path, "w") as f:
        f.write("\n".join(lines))
    print(f"[{tier}] wrote {cap_path}")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", required=True, choices=list(TIERS.keys()))
    ap.add_argument("--games", type=int, default=10)
    ap.add_argument("--resample-cap", type=int, default=20)
    ap.add_argument("--opponent-skill", type=int, default=3)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()
    scratch = os.path.join(HERE, "runs", "dreaminess-sweep")
    os.makedirs(scratch, exist_ok=True)
    out_json = os.path.join(scratch, f"{args.tier}-sweep.json")
    run_sweep(args.tier, args.games, args.resample_cap, args.opponent_skill,
              args.device, args.seed, out_json, scratch)


if __name__ == "__main__":
    main()
