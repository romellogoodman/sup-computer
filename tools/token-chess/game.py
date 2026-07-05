"""
game.py -- Token Chess: two players share the board, but neither can play a
move from its own reasoning. Every move must come from Daydream, queried as
a tool, under a fixed per-game token budget. The benchmark measures how
economically a player orchestrates Daydream's sampler under scarcity --
not chess strength (see the Token Chess design plan, ~/Desktop/token-chess-
benchmark-plan.md, for the full rationale).

Locked mechanics (do not relitigate without updating that plan first):
  - Daydream-exclusive: the only way to move is a Daydream query that lands
    legal. No self-authored moves.
  - Every query costs exactly 1 token, regardless of settings or outcome.
  - Per-turn transcript scoping: a player sees every attempt made THIS turn,
    cleared when the turn passes -- no persistent cross-game sampler model.
  - Budget exhaustion (spend the last token, still no legal move) is an
    IMMEDIATE FORFEIT, not graceful degradation.
  - Budgets are hidden: each player sees only its own remaining tokens.
  - Headline metric: games won per token spent. Reported alongside plain
    win rate, legality hit rate, and turn-level sampling adaptation.

This build has real Daydream (reusing projects/daydream/harness.py's
DaydreamPlayer and the shared engine_client legality arbiter) but only
MOCK frontier-model players (players.py) -- no API credentials exist in
this environment. Swapping in a real API-backed Player is meant to be the
only change needed to run an actual match.

Run from the repo root:
    uv run python tools/token-chess/game.py --tier regular \
        --out_dir projects/daydream/runs/regular-r1 --budget 40
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "projects", "daydream"))
from engine_client import Engine  # noqa: E402
from harness import TIERS, DaydreamPlayer  # noqa: E402

from players import AdaptivePlayer, Player, RandomPlayer  # noqa: E402

MAX_PLIES = 200


class TokenChessGame:
    def __init__(self, tier: str, daydream: DaydreamPlayer, white: Player, black: Player,
                 budget: int, opponent_free_engine: bool = False):
        """opponent_free_engine exists only for harness self-tests: when
        True, skip Daydream/budget mechanics for a side and just play the
        engine's own best move, to isolate bugs in the other side's
        accounting. Real games never set this."""
        self.tier_cfg = TIERS[tier]
        self.daydream = daydream
        self.players = {"white": white, "black": black}
        self.budgets = {"white": budget, "black": budget}
        self.calls_spent = {"white": 0, "black": 0}
        self.legal_first_try = {"white": 0, "black": 0}
        self.moves_made = {"white": 0, "black": 0}
        self.opponent_free_engine = opponent_free_engine
        self.attempt_log = []  # every attempt, for post-game budget analysis

    def _query_daydream(self, moves: list, config: dict, engine: Engine) -> dict:
        legal = engine.legal_moves(moves)
        game_prefix = (" ".join(moves) + " ") if moves else "\n"
        candidate = self.daydream.sample_candidate_move(
            game_prefix, temperature=config["temperature"], soft_cap=config["soft_cap"]
        )
        return {**config, "move": candidate, "legal": candidate in legal, "legal_moves_this_position": legal}

    def play(self) -> dict:
        engine = Engine(self.tier_cfg["variant"], self.tier_cfg["variants_ini"])
        moves = []
        result = None
        try:
            for ply in range(MAX_PLIES):
                side = "white" if ply % 2 == 0 else "black"
                player = self.players[side]

                legal_now = engine.legal_moves(moves)
                if not legal_now:
                    result = {"outcome": "chess_result", "winner": None if self._is_draw_like() else _other(side)}
                    break

                transcript_this_turn = []  # cleared every turn -- the locked per-turn scoping
                accepted_move = None
                while True:
                    if self.budgets[side] <= 0:
                        result = {"outcome": "forfeit", "winner": _other(side), "loser": side}
                        break
                    config = player.choose_config(self.budgets[side], transcript_this_turn)
                    self.budgets[side] -= 1
                    self.calls_spent[side] += 1
                    attempt = self._query_daydream(moves, config, engine)
                    transcript_this_turn.append(attempt)
                    self.attempt_log.append({
                        "ply": ply, "side": side, "budget_after": self.budgets[side],
                        "temperature": attempt["temperature"], "soft_cap": attempt["soft_cap"],
                        "move": attempt["move"], "legal": attempt["legal"],
                        "n_legal_moves": len(attempt["legal_moves_this_position"]),
                    })
                    if attempt["legal"]:
                        accepted_move = attempt["move"]
                        if len(transcript_this_turn) == 1:
                            self.legal_first_try[side] += 1
                        break
                if result is not None:
                    break
                moves.append(accepted_move)
                self.moves_made[side] += 1
            else:
                result = {"outcome": "ply_cap", "winner": None}
        finally:
            engine.close()

        return self._summarize(result, moves)

    def _is_draw_like(self) -> bool:
        return False  # stalemate vs. checkmate distinction not needed for scoring here

    def _summarize(self, result: dict, moves: list) -> dict:
        winner = result.get("winner")
        return {
            "outcome": result["outcome"],
            "winner": winner,
            "plies": len(moves),
            "calls_spent": dict(self.calls_spent),
            "legal_first_try": dict(self.legal_first_try),
            "moves_made": dict(self.moves_made),
            "legal_hit_rate": {
                side: (self.legal_first_try[side] / self.calls_spent[side]) if self.calls_spent[side] else 0.0
                for side in ("white", "black")
            },
            "attempts": self.attempt_log,
        }


def _other(side: str) -> str:
    return "black" if side == "white" else "white"


def make_player(spec: str, seed: int = 0) -> Player:
    """Build a player from a CLI spec:
      mock:adaptive | mock:random      -- the harness self-test stand-ins
      lmstudio:<model-id>              -- local model via LM Studio's
                                          OpenAI-compatible server (or any
                                          compatible server via
                                          STEER_BASE_URL)
      anthropic:<model-id>             -- reserved; needs API credentials
    """
    kind, _, arg = spec.partition(":")
    if kind == "mock":
        if arg == "adaptive":
            return AdaptivePlayer()
        if arg == "random":
            return RandomPlayer(seed=seed)
        raise ValueError(f"unknown mock player: {arg}")
    if kind == "lmstudio":
        from steer import OpenAICompatClient
        from players import LLMPlayer  # noqa: PLC0415
        return LLMPlayer(OpenAICompatClient(arg))
    if kind == "anthropic":
        raise NotImplementedError("anthropic: players need API credentials; the LLMPlayer seam is client-agnostic")
    raise ValueError(f"unknown player spec: {spec}")


def run_match(tier: str, out_dir: str, budget: int, games: int, device: str = "mps",
              white_spec: str = "mock:adaptive", black_spec: str = "mock:random",
              log_dir: str = None) -> dict:
    daydream = DaydreamPlayer(out_dir, device=device)
    game_results = []
    llm_stats = {}
    for g in range(games):
        # Alternate colors each game so neither spec owns white.
        specs = (white_spec, black_spec) if g % 2 == 0 else (black_spec, white_spec)
        white, black = make_player(specs[0], seed=g), make_player(specs[1], seed=g)
        game = TokenChessGame(tier, daydream, white, black, budget)
        r = game.play()
        r["white_player"], r["black_player"] = specs
        game_results.append(r)
        for spec, player in ((specs[0], white), (specs[1], black)):
            if hasattr(player, "stats"):
                agg = llm_stats.setdefault(spec, {k: 0 for k in player.stats})
                for k, v in player.stats.items():
                    agg[k] += v
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, f"game-{g + 1:03d}.json"), "w") as f:
                json.dump(r, f, indent=2)
        print(f"  game {g + 1}/{games}: {r['outcome']}, winner={r['winner']}, plies={r['plies']}, "
              f"calls={r['calls_spent']}")

    summary = score(game_results)
    for spec, agg in llm_stats.items():
        summary.setdefault(spec, {})["llm_usage"] = agg
    return summary


def score(game_results: list) -> dict:
    """Headline: games won per token spent. Breakdown: win rate, legality
    hit rate, per player-type (aggregated across the mock roster)."""
    by_type = {}
    for r in game_results:
        for side in ("white", "black"):
            ptype = r[f"{side}_player"]
            by_type.setdefault(ptype, {"wins": 0, "games": 0, "tokens_spent": 0, "legal_attempts": 0, "legal_hits": 0})
            entry = by_type[ptype]
            entry["games"] += 1
            entry["tokens_spent"] += r["calls_spent"][side]
            entry["legal_attempts"] += r["calls_spent"][side]
            entry["legal_hits"] += r["legal_first_try"][side]
            if r["winner"] == side:
                entry["wins"] += 1

    summary = {}
    for ptype, e in by_type.items():
        summary[ptype] = {
            "games": e["games"],
            "win_rate": e["wins"] / e["games"] if e["games"] else 0.0,
            "wins_per_token_spent": e["wins"] / e["tokens_spent"] if e["tokens_spent"] else 0.0,
            "legal_hit_rate": e["legal_hits"] / e["legal_attempts"] if e["legal_attempts"] else 0.0,
        }
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", required=True, choices=list(TIERS.keys()))
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--budget", type=int, default=40, help="per-player token budget for the whole game")
    ap.add_argument("--games", type=int, default=6)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--white", default="mock:adaptive", help="player spec (see make_player)")
    ap.add_argument("--black", default="mock:random")
    ap.add_argument("--log_dir", default=None, help="write per-game JSON records here")
    args = ap.parse_args()

    summary = run_match(args.tier, args.out_dir, args.budget, args.games, args.device,
                        white_spec=args.white, black_spec=args.black, log_dir=args.log_dir)
    print("\n=== Token Chess ===")
    for ptype, stats in summary.items():
        print(f"  {ptype}: games={stats['games']} win_rate={stats['win_rate']:.2f} "
              f"wins/token={stats['wins_per_token_spent']:.4f} legal_hit_rate={stats['legal_hit_rate']:.2f}")
        if "llm_usage" in stats:
            u = stats["llm_usage"]
            print(f"    llm: {u['calls']} calls, {u['prompt_tokens']}+{u['completion_tokens']} tokens, "
                  f"{u['parse_failures']} parse failures")


if __name__ == "__main__":
    main()
