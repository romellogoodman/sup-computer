"""
harness.py -- the board-size-parameterized harness, shared across all three
daydream tiers. Plays a trained checkpoint against a skill-limited
Fairy-Stockfish opponent, resampling the model's move on illegal output
(and rendering the rejected samples as the dream texture) until a legal
move lands or a resample cap is hit, at which point a uniformly random
legal move is forced so the game always completes.

This also doubles as the verification tool: run N games and report the two
automated gate metrics (legal-move rate, clean-completion rate) -- nothing
else is an automated gate; win rate and dream-rendering quality are
explicitly not (see the daydream design plan).

Run from the repo root:
    uv run python projects/daydream/harness.py \
        --tier regular --out_dir projects/daydream/runs/regular-r1 \
        --games 50
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys

import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_client import Engine  # noqa: E402
from nanogpt_core import load_model  # noqa: E402  (workspace-installed core)

TIERS = {
    "micro": {"variant": "gardner", "variants_ini": "", "data_dir": "data/micro"},
    "regular": {"variant": "chess", "variants_ini": "", "data_dir": "data/regular"},
    "grand": {
        "variant": "grand12",
        "variants_ini": os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine", "variants.ini"),
        "data_dir": "data/grand",
    },
}

MOVE_TERMINATORS = (" ", "\n")
MAX_MOVE_CHARS = 8  # longest possible UCI move (e.g. "k12l11q" on Grand) plus margin
MAX_GAME_PLIES = 200


class DaydreamPlayer:
    """Wraps a trained checkpoint; samples one candidate move at a time,
    resampling on illegal output up to a cap, then forcing a random legal
    move. Tracks every attempt (accepted or not) for the legal-move-rate
    metric and for future dream-rendering (the rejected samples ARE the
    dream texture -- this harness keeps them, it doesn't discard them)."""

    def __init__(self, out_dir: str, device: str = "mps", temperature: float = 0.9, soft_cap: float = None):
        self.model, checkpoint = load_model(out_dir, device)
        self.device = device
        self.block_size = self.model.config.block_size
        self.temperature = temperature
        self.soft_cap = soft_cap  # None = disabled; a float = Gemma-style logit soft-capping

        dataset = checkpoint["config"]["dataset"]
        data_root = checkpoint["config"]["data_root"]
        meta_path = os.path.join(data_root, dataset, "meta.pkl")
        with open(meta_path, "rb") as f:
            meta = pickle.load(f)
        self.stoi, self.itos = meta["stoi"], meta["itos"]

    def encode(self, s: str) -> list:
        return [self.stoi[c] for c in s]

    def decode(self, ids: list) -> str:
        return "".join(self.itos[i] for i in ids)

    def _sample_one_char(self, idx: torch.Tensor, temperature: float, soft_cap) -> int:
        idx_cond = idx if idx.size(1) <= self.block_size else idx[:, -self.block_size:]
        with torch.no_grad():
            logits, _ = self.model(idx_cond)
        logits = logits[:, -1, :]
        if soft_cap is not None:
            logits = soft_cap * torch.tanh(logits / soft_cap)
        logits = logits / max(temperature, 1e-5)
        probs = F.softmax(logits, dim=-1)
        return torch.multinomial(probs, num_samples=1).item()

    def sample_candidate_move(self, game_prefix: str, temperature: float = None, soft_cap=None) -> str:
        """Sample chars until a move terminator (space/newline) or the
        length safety cap, starting right after `game_prefix`. temperature/
        soft_cap default to this player's construction-time settings, but
        can be overridden per call -- Token Chess needs this, since each
        query there carries its own chosen sampler config."""
        temperature = self.temperature if temperature is None else temperature
        soft_cap = self.soft_cap if soft_cap is None else soft_cap
        idx = torch.tensor([self.encode(game_prefix)], dtype=torch.long, device=self.device)
        out_chars = []
        for _ in range(MAX_MOVE_CHARS):
            next_id = self._sample_one_char(idx, temperature, soft_cap)
            ch = self.itos[next_id]
            if ch in MOVE_TERMINATORS:
                break
            out_chars.append(ch)
            idx = torch.cat([idx, torch.tensor([[next_id]], device=self.device)], dim=1)
        return "".join(out_chars)

    def propose_move(self, moves: list, engine: Engine, resample_cap: int, rng) -> dict:
        """Returns {'move': str, 'accepted_attempt': int, 'forced_random': bool,
        'attempts': [candidate strings, in order]} -- everything the caller
        needs for both gameplay and the legal-move-rate metric."""
        # "\n" seeds the very first move of a game -- corpus lines are
        # newline-separated games, so the model learned "a fresh game's
        # first move follows a newline." An empty prefix would feed the
        # model a zero-length sequence, which crashes.
        game_prefix = (" ".join(moves) + " ") if moves else "\n"
        legal = engine.legal_moves(moves)
        attempts = []
        for attempt_i in range(1, resample_cap + 1):
            candidate = self.sample_candidate_move(game_prefix)
            attempts.append(candidate)
            if candidate in legal:
                return {"move": candidate, "accepted_attempt": attempt_i, "forced_random": False, "attempts": attempts}
        forced = rng.choice(legal) if legal else None
        return {"move": forced, "accepted_attempt": None, "forced_random": True, "attempts": attempts}


def play_verification_game(player: DaydreamPlayer, tier_cfg: dict, resample_cap: int, opponent_skill: int, rng, model_plays_white: bool):
    engine = Engine(tier_cfg["variant"], tier_cfg["variants_ini"], skill_level=opponent_skill)
    moves = []
    first_try_legal = 0
    total_daydream_moves = 0
    forced_random_count = 0
    result = "in_progress"
    try:
        for ply in range(MAX_GAME_PLIES):
            white_to_move = ply % 2 == 0
            daydream_turn = white_to_move == model_plays_white
            legal = engine.legal_moves(moves)
            if not legal:
                result = "clean_completion"  # checkmate or stalemate -- either way, a clean end
                break
            if daydream_turn:
                proposal = player.propose_move(moves, engine, resample_cap, rng)
                total_daydream_moves += 1
                if proposal["accepted_attempt"] == 1:
                    first_try_legal += 1
                if proposal["forced_random"]:
                    forced_random_count += 1
                if proposal["move"] is None:
                    result = "crashed_no_legal_move"
                    break
                moves.append(proposal["move"])
            else:
                move = engine.best_move(moves, depth=4)
                if move is None:
                    result = "clean_completion"
                    break
                moves.append(move)
        else:
            result = "clean_completion"  # hit the ply cap without crashing -- still a clean run
    except Exception as e:
        result = f"crashed: {e}"
    finally:
        engine.close()
    return {
        "result": result,
        "plies": len(moves),
        "daydream_moves": total_daydream_moves,
        "first_try_legal": first_try_legal,
        "forced_random_count": forced_random_count,
    }


def verify(tier: str, out_dir: str, games: int, resample_cap: int, opponent_skill: int, device: str, seed: int):
    import random

    tier_cfg = TIERS[tier]
    player = DaydreamPlayer(out_dir, device=device)
    rng = random.Random(seed)

    results = []
    for g in range(games):
        model_plays_white = g % 2 == 0
        r = play_verification_game(player, tier_cfg, resample_cap, opponent_skill, rng, model_plays_white)
        results.append(r)
        print(f"  game {g + 1}/{games}: {r['result']}, {r['plies']} plies, "
              f"first-try legal {r['first_try_legal']}/{r['daydream_moves']}")

    clean = sum(1 for r in results if r["result"] == "clean_completion")
    total_daydream_moves = sum(r["daydream_moves"] for r in results)
    total_first_try = sum(r["first_try_legal"] for r in results)
    legal_rate = total_first_try / total_daydream_moves if total_daydream_moves else 0.0

    print(f"\n=== verification: {tier} ===")
    print(f"games: {games}, clean completion: {clean}/{games} ({100 * clean / games:.1f}%)")
    print(f"legal-move rate (first try): {total_first_try}/{total_daydream_moves} ({100 * legal_rate:.1f}%)")
    return {"clean_completion_rate": clean / games, "legal_move_rate": legal_rate, "games": results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", required=True, choices=list(TIERS.keys()))
    ap.add_argument("--out_dir", required=True, help="checkpoint dir, e.g. projects/daydream/runs/regular-r1")
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--resample-cap", type=int, default=20)
    ap.add_argument("--opponent-skill", type=int, default=3, help="Fairy-Stockfish Skill Level, 0-20")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()
    verify(args.tier, args.out_dir, args.games, args.resample_cap, args.opponent_skill, args.device, args.seed)


if __name__ == "__main__":
    main()
