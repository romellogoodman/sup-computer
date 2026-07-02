"""
harness.py (FROZEN release copy, Grand/12x10 only) -- plays this
checkpoint against a skill-limited Fairy-Stockfish opponent, resampling on
illegal moves until one lands or a resample cap forces a random legal move.
Doubles as the verification tool (legal-move rate, clean-completion rate).

Unlike the working copy at projects/daydream/harness.py (which is
parameterized across all three tiers), this frozen copy only supports
Grand -- Regular and Micro each have their own frozen folder with their own
copy. Imports point at the vendored model.py in this folder, not
core/nanogpt_core, so this runs with zero dependency on the project root.
Also vendors variants.ini, the custom board config -- unlike Micro (which
uses Fairy-Stockfish's built-in gardner variant directly), Grand needs it.

Run from inside this folder:
    python harness.py --games 30
"""
from __future__ import annotations

import argparse
import os
import pickle
import random

import torch
import torch.nn.functional as F

from engine_client import Engine
from model import GPT, GPTConfig

VARIANT = "grand12"
VARIANTS_INI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "variants.ini")
MOVE_TERMINATORS = (" ", "\n")
MAX_MOVE_CHARS = 8
MAX_GAME_PLIES = 200


class DaydreamPlayer:
    def __init__(self, out_dir: str, device: str = "mps", temperature: float = 0.9, soft_cap: float = None):
        ckpt_path = os.path.join(out_dir, "ckpt.pt")
        checkpoint = torch.load(ckpt_path, map_location=device, weights_only=True)
        gptconf = GPTConfig(**checkpoint["model_args"])
        self.model = GPT(gptconf)
        state_dict = checkpoint["model"]
        unwanted_prefix = "_orig_mod."
        for k, v in list(state_dict.items()):
            if k.startswith(unwanted_prefix):
                state_dict[k[len(unwanted_prefix):]] = state_dict.pop(k)
        self.model.load_state_dict(state_dict)
        self.model.eval()
        self.model.to(device)
        self.device = device
        self.block_size = gptconf.block_size
        self.temperature = temperature
        self.soft_cap = soft_cap

        dataset = checkpoint["config"]["dataset"]
        data_root = checkpoint["config"]["data_root"]
        meta_path = os.path.join(data_root, dataset, "meta.pkl")
        with open(meta_path, "rb") as f:
            meta = pickle.load(f)
        self.stoi, self.itos = meta["stoi"], meta["itos"]

    def encode(self, s: str) -> list:
        return [self.stoi[c] for c in s]

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


def play_verification_game(player: DaydreamPlayer, resample_cap: int, opponent_skill: int, rng, model_plays_white: bool):
    engine = Engine(VARIANT, VARIANTS_INI, skill_level=opponent_skill)
    moves = []
    first_try_legal = 0
    total_daydream_moves = 0
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
                total_daydream_moves += 1
                if proposal["accepted_attempt"] == 1:
                    first_try_legal += 1
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
            result = "clean_completion"
    except Exception as e:
        result = f"crashed: {e}"
    finally:
        engine.close()
    return {"result": result, "plies": len(moves), "daydream_moves": total_daydream_moves, "first_try_legal": first_try_legal}


def verify(out_dir: str, games: int, resample_cap: int, opponent_skill: int, device: str, seed: int):
    player = DaydreamPlayer(out_dir, device=device)
    rng = random.Random(seed)
    results = []
    for g in range(games):
        r = play_verification_game(player, resample_cap, opponent_skill, rng, g % 2 == 0)
        results.append(r)
        print(f"  game {g + 1}/{games}: {r['result']}, {r['plies']} plies, "
              f"first-try legal {r['first_try_legal']}/{r['daydream_moves']}")
    clean = sum(1 for r in results if r["result"] == "clean_completion")
    total = sum(r["daydream_moves"] for r in results)
    hits = sum(r["first_try_legal"] for r in results)
    print(f"\ngames: {games}, clean completion: {clean}/{games} ({100 * clean / games:.1f}%)")
    print(f"legal-move rate (first try): {hits}/{total} ({100 * hits / total:.1f}%)" if total else "no moves attempted")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", default=".")
    ap.add_argument("--games", type=int, default=30)
    ap.add_argument("--resample-cap", type=int, default=20)
    ap.add_argument("--opponent-skill", type=int, default=3)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()
    verify(args.out_dir, args.games, args.resample_cap, args.opponent_skill, args.device, args.seed)
