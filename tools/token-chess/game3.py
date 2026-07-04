"""game3.py -- Token Chess, round three: batches, choice, adjudication.

Round one (game.py, mechanics locked there) priced sampler-config skill
under existential scarcity and found every game ends in forfeit. The
round-two probe (round2_probe.py) removed death and found the refund
economy erases discrimination. The round-three probes (round3_probe.py)
found the two levers that survive: the legality floor is config-dependent
(~8-30%, so knob skill is real), and best-of-N candidate picking wins
every decisive game (so judgment is real). This harness prices both.

Round-three mechanics (locked -- relitigate in the README first):
  - Daydream-exclusive: every move is a Daydream sample. No self-authored
    moves; the player only chooses configs and picks among legal samples.
  - A token buys a BATCH: the player picks {temperature, soft_cap}, the
    harness draws 3 samples at it. All 3 are shown; the legal ones join
    the turn's candidate pool (deduped).
  - Picking is free: the player may play any pooled candidate, or spend
    another token on another batch (any config). Economy vs quality.
  - Per-turn transcript scoping: pool and attempt log clear when the turn
    ends. Unchanged from round one.
  - Budgets are hidden from the opponent. Unchanged from round one.
  - Exhaustion = ADJUDICATION, not forfeit: a player to move with no
    tokens and no candidates ends the game, and Fairy-Stockfish evaluates
    the final position (|cp| >= ADJUDICATION_CP decides a winner, mate
    scores decide outright, anything closer is a draw). The board gets
    the last word; the clock only decides when it's spoken.
  - Headline metric: color-balanced score (win=1, draw=0.5). Reported
    with tokens spent, batches and candidates per move, and adjudication
    vs on-board endings. Per-game JSONs carry LLM usage stats (calls,
    tokens, parse failures) -- the round-one logging gap, closed.

Regular tier only for now: python-chess is the legality arbiter and draw
judge (identical rules to the shared perft arbiter for standard chess,
plus the repetition/fifty-move endings completed games need);
Fairy-Stockfish is the adjudicator.

Run from the repo root:
    uv run python tools/token-chess/game3.py --budget 40 --games 4 \
        --white lmstudio:olmo-3-7b-instruct --black mock:heuristic \
        --log_dir tools/token-chess/evidence/<run>
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
sys.path.insert(0, os.path.join(HERE, ".."))  # tools/ -- the shared steer layer

import chess  # noqa: E402
from engine_client import Engine  # noqa: E402
from harness import DaydreamPlayer  # noqa: E402

from players import _validate_config  # noqa: E402

BATCH_SIZE = 3
MAX_PLIES = 300
ADJUDICATION_CP = 100
ADJUDICATION_DEPTH = 10
DEFAULT_CONFIG3 = {"temperature": 0.9, "soft_cap": None}  # the profile sweep's best floor config
PIECE_VALUE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


# ---------------------------------------------------------------- players

class Player3:
    """One round-three player. Sees its own budget, the position, and this
    turn's batches/pool; returns one decision per step:
      {"action": "sample", "temperature": float, "soft_cap": float|None}
      {"action": "pick", "move": "<uci from the pool>"}
    """

    def decide(self, own_budget: int, turn_state: dict) -> dict:
        raise NotImplementedError


class RandomPicker3(Player3):
    """Floor baseline: random configs, picks the moment anything is legal,
    picks uniformly."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def decide(self, own_budget: int, turn_state: dict) -> dict:
        pool = turn_state["candidates"]
        if pool:
            return {"action": "pick", "move": self.rng.choice(pool)}
        return {"action": "sample",
                "temperature": self.rng.uniform(0.3, 1.5),
                "soft_cap": self.rng.choice([None, 5.0, 10.0, 20.0])}


class HeuristicPicker3(Player3):
    """The qualifying bar: best-known config, a little patience (shop for a
    second candidate when the budget allows), and the round3-probe pick
    heuristic (mate > biggest capture > check > random)."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def decide(self, own_budget: int, turn_state: dict) -> dict:
        pool = turn_state["candidates"]
        batches = len(turn_state["batches"])
        if not pool:
            return {"action": "sample", **DEFAULT_CONFIG3}
        if len(pool) >= 2 or batches >= 2 or own_budget <= 2:
            return {"action": "pick", "move": self._pick(turn_state["fen"], pool)}
        return {"action": "sample", **DEFAULT_CONFIG3}

    def _pick(self, fen: str, pool: list) -> str:
        board = chess.Board(fen)
        best, best_score = [], -1.0
        for uci in pool:
            move = chess.Move.from_uci(uci)
            board.push(move)
            mate = board.is_checkmate()
            board.pop()
            if mate:
                return uci
            score = 0.0
            if board.is_capture(move):
                captured = board.piece_at(move.to_square)
                score += 10.0 * (PIECE_VALUE.get(captured.piece_type, 1) if captured else 1)
            if board.gives_check(move):
                score += 1.0
            if score > best_score:
                best, best_score = [uci], score
            elif score == best_score:
                best.append(uci)
        return self.rng.choice(best)


LLM_SEED3 = """You are playing Token Chess. You cannot author chess moves yourself. \
The only move source is Daydream, a 2.7M-parameter character-level GPT trained on \
chess game text (it learned move TEXT, not the rules -- its samples are often \
illegal). You steer its sampler and choose among what it produces.

Mechanics:
- Spending 1 token draws a BATCH of 3 Daydream samples at sampler settings you choose:
  - temperature (float, 0.1-2.0): lower = Daydream's most-confident move text; \
higher = more varied, more error-prone.
  - soft_cap (float > 0, or null): logit soft-capping; lower caps flatten \
confidence spikes, null disables.
- Samples that are LEGAL in the current position join your candidate pool this turn.
- Picking is FREE: play any pooled candidate, or spend another token for another batch.
- Your pool and this log clear when your turn ends.
- If you must move with no tokens and no candidates, the game ends and a chess \
engine adjudicates the final position -- the side with the better position wins.
- Your budget is hidden from your opponent. Tokens you save now are batches you \
can afford in harder positions later.

Respond with ONLY one JSON object, either:
{"action": "sample", "temperature": <float>, "soft_cap": <float or null>}
or {"action": "pick", "move": "<a uci move from your candidate pool>"}"""

FALLBACK_DECISION3 = {"action": "sample", **DEFAULT_CONFIG3}

# Round-4 memory conditions. "ledger" is harness telemetry (own per-move spend
# history); "notepad" is model-authored memory (an optional note on any
# decision, the last 3 shown back each turn). Both are deliberately narrower
# than the per-turn attempt log, which still clears every turn -- the ledger
# carries only economics, and the notepad carries only what the model chooses
# to write. The notepad knowingly opens a channel the scoping rule closed;
# that's the experiment.
NOTE_MAX_CHARS = 200
NOTEPAD_SEED_SUFFIX = """

Memory: you may add an optional "note" field (a string, max 200 characters) to ANY \
decision. Your 3 most recent notes are shown back to you every turn -- they are your \
ONLY memory that survives across turns. Example: \
{"action": "pick", "move": "e2e4", "note": "down a knight; spend hard for captures"}"""


class LLMPlayer3(Player3):
    """A real player: one stateless JSON decision per step via tools/steer.
    Config choice AND candidate picking both belong to the LLM."""

    def __init__(self, client, own_temperature: float = 0.7, memory: str = "none"):
        from steer import Orchestrator

        self._pool = []
        self.memory = memory
        seed = LLM_SEED3 + (NOTEPAD_SEED_SUFFIX if memory == "notepad" else "")
        self.orchestrator = Orchestrator(client, seed, self._validate,
                                         FALLBACK_DECISION3, own_temperature)

    @property
    def stats(self) -> dict:
        return self.orchestrator.stats

    def _validate(self, obj) -> dict:
        if not isinstance(obj, dict):
            return None
        decision = None
        if obj.get("action") == "pick":
            move = obj.get("move")
            decision = {"action": "pick", "move": move} if move in self._pool else None
        elif obj.get("action") == "sample":
            config = _validate_config(obj)
            decision = {"action": "sample", **config} if config else None
        if decision is not None and self.memory == "notepad":
            note = obj.get("note")
            if isinstance(note, str) and note.strip():
                decision["note"] = note.strip()[:NOTE_MAX_CHARS]
        return decision

    def decide(self, own_budget: int, turn_state: dict) -> dict:
        self._pool = list(turn_state["candidates"])
        return self.orchestrator.decide(self._render(own_budget, turn_state))

    @staticmethod
    def _render(own_budget: int, turn_state: dict) -> str:
        lines = [f"Position (FEN): {turn_state['fen']}"]
        recent = turn_state["recent_moves"]
        lines.append("Recent moves: " + (" ".join(recent) if recent else "(game start)"))
        lines.append(f"Your remaining tokens: {own_budget}.")
        ledger = turn_state.get("ledger")
        if ledger is not None and ledger:
            recent = ",".join(str(n) for n in ledger[-10:])
            lines.append(f"Your spend so far this game: {sum(ledger)} tokens over {len(ledger)} moves "
                         f"(per-move, most recent last: {recent}).")
        elif ledger is not None:
            lines.append("Your spend so far this game: 0 tokens (first move).")
        notes = turn_state.get("notes")
        if notes is not None and notes:
            lines.append("Your notes from earlier turns (most recent last):")
            lines.extend(f'- (ply {n["ply"]}) {n["note"]}' for n in notes)
        elif notes is not None:
            lines.append("Your notepad is empty.")
        if turn_state["batches"]:
            lines.append("Batches drawn this turn:")
            for b in turn_state["batches"]:
                cap = "null" if b["soft_cap"] is None else b["soft_cap"]
                shown = ", ".join(f'"{s["move"]}" {"LEGAL" if s["legal"] else "illegal"}' for s in b["samples"])
                lines.append(f"- temperature={b['temperature']:.2f} soft_cap={cap}: {shown}")
        else:
            lines.append("No batches drawn yet this turn.")
        pool = turn_state["candidates"]
        if pool:
            lines.append("Candidate pool (legal, pickable): " + ", ".join(pool))
            lines.append("Pick one, or spend a token on another batch.")
        else:
            lines.append("Candidate pool is empty -- you must sample.")
        return "\n".join(lines)


def make_player3(spec: str, seed: int = 0) -> tuple:
    """mock:heuristic | mock:random | lmstudio:<model-id>, each with an
    optional +none/+ledger/+notepad memory suffix (round 4). Memory rides the
    spec, not the seat, so it follows the player through color alternation.
    Returns (player, memory)."""
    base, _, memory = spec.partition("+")
    memory = memory or "none"
    if memory not in ("none", "ledger", "notepad"):
        raise ValueError(f"unknown memory condition: {memory}")
    kind, _, arg = base.partition(":")
    if kind == "mock":
        if arg == "heuristic":
            return HeuristicPicker3(seed=seed), memory
        if arg == "random":
            return RandomPicker3(seed=seed), memory
        raise ValueError(f"unknown mock player: {arg}")
    if kind == "lmstudio":
        from steer import OpenAICompatClient
        return LLMPlayer3(OpenAICompatClient(arg), memory=memory), memory
    raise ValueError(f"unknown player spec: {spec}")


# ---------------------------------------------------------------- the game

class TokenChess3Game:
    def __init__(self, daydream: DaydreamPlayer, white: Player3, black: Player3,
                 budget: int, rng: random.Random, memory: dict = None):
        """memory maps side -> "none" | "ledger" | "notepad" (round 4).
        Ledger shows a side its own per-move spend history; notepad carries
        the side's own decision notes forward. The per-turn attempt log
        (configs + legality) still clears every turn regardless."""
        self.daydream = daydream
        self.players = {"white": white, "black": black}
        self.budgets = {"white": budget, "black": budget}
        self.memory = memory or {"white": "none", "black": "none"}
        self.spend_history = {"white": [], "black": []}
        self.notes = {"white": [], "black": []}
        self.stats = {side: {"tokens_spent": 0, "batches": 0, "moves": 0, "samples_legal": 0,
                             "samples_total": 0, "candidates_at_pick": 0, "forced_picks": 0}
                      for side in ("white", "black")}
        self.rng = rng
        self.turn_log = []

    def _draw_batch(self, moves: list, config: dict, legal: list) -> dict:
        game_prefix = (" ".join(moves) + " ") if moves else "\n"
        samples = []
        for _ in range(BATCH_SIZE):
            cand = self.daydream.sample_candidate_move(
                game_prefix, temperature=config["temperature"], soft_cap=config["soft_cap"])
            samples.append({"move": cand, "legal": cand in legal})
        return {**config, "samples": samples}

    def play(self) -> dict:
        board = chess.Board()
        moves = []
        result = None
        for ply in range(MAX_PLIES):
            outcome = board.outcome(claim_draw=True)
            if outcome is not None:
                result = {"outcome": outcome.termination.name.lower(),
                          "winner": {True: "white", False: "black", None: None}[outcome.winner]}
                break
            side = "white" if ply % 2 == 0 else "black"
            player = self.players[side]
            legal = [m.uci() for m in board.legal_moves]
            mem = self.memory[side]
            turn = {"ply": ply, "side": side, "batches": [], "candidates": [],
                    "fen": board.fen(), "recent_moves": moves[-8:],
                    "ledger": list(self.spend_history[side]) if mem == "ledger" else None,
                    "notes": list(self.notes[side][-3:]) if mem == "notepad" else None}
            picked = None
            turn_spend = 0
            turn_notes = []
            while True:
                if not turn["candidates"] and self.budgets[side] <= 0:
                    result = self._adjudicate(moves, "adjudication_exhausted", side)
                    break
                decision = player.decide(self.budgets[side], turn)
                if mem == "notepad" and decision.get("note"):
                    entry = {"ply": ply, "note": decision["note"]}
                    self.notes[side].append(entry)
                    turn_notes.append(entry)
                    turn["notes"] = list(self.notes[side][-3:])
                if decision["action"] == "pick" and decision.get("move") in turn["candidates"]:
                    picked = decision["move"]
                    break
                if decision["action"] == "pick":
                    # invalid pick from a mock/fallback path; treat as a forced random pick
                    if turn["candidates"]:
                        picked = self.rng.choice(turn["candidates"])
                        self.stats[side]["forced_picks"] += 1
                        break
                    continue
                if self.budgets[side] <= 0:  # wants to sample, can't afford it
                    if turn["candidates"]:
                        picked = self.rng.choice(turn["candidates"])
                        self.stats[side]["forced_picks"] += 1
                        break
                    result = self._adjudicate(moves, "adjudication_exhausted", side)
                    break
                config = {"temperature": decision["temperature"], "soft_cap": decision["soft_cap"]}
                self.budgets[side] -= 1
                self.stats[side]["tokens_spent"] += 1
                self.stats[side]["batches"] += 1
                turn_spend += 1
                batch = self._draw_batch(moves, config, legal)
                turn["batches"].append(batch)
                self.stats[side]["samples_total"] += BATCH_SIZE
                for s in batch["samples"]:
                    if s["legal"]:
                        self.stats[side]["samples_legal"] += 1
                        if s["move"] not in turn["candidates"]:
                            turn["candidates"].append(s["move"])
            if result is not None:
                break
            self.stats[side]["moves"] += 1
            self.stats[side]["candidates_at_pick"] += len(turn["candidates"])
            self.spend_history[side].append(turn_spend)
            self.turn_log.append({"ply": ply, "side": side, "picked": picked,
                                  "n_candidates": len(turn["candidates"]),
                                  "notes": turn_notes,
                                  "batches": turn["batches"], "budget_after": self.budgets[side]})
            moves.append(picked)
            board.push_uci(picked)
        else:
            result = self._adjudicate(moves, "adjudication_plycap", None)
        return self._summarize(result, moves, board)

    def _adjudicate(self, moves: list, outcome: str, exhausted_side) -> dict:
        engine = Engine("chess", "")
        try:
            score = engine.evaluate(moves, depth=ADJUDICATION_DEPTH)
        finally:
            engine.close()
        side_to_move = "white" if len(moves) % 2 == 0 else "black"
        # score is from the side-to-move's perspective; normalize to white's
        white_value = score["value"] if side_to_move == "white" else -score["value"]
        if score["kind"] == "mate":
            winner = ("white" if white_value > 0 else "black")
        elif abs(white_value) >= ADJUDICATION_CP:
            winner = "white" if white_value > 0 else "black"
        else:
            winner = None
        return {"outcome": outcome, "winner": winner, "exhausted_side": exhausted_side,
                "adjudication": {**score, "perspective": side_to_move,
                                 "white_cp": white_value if score["kind"] == "cp" else None,
                                 "depth": ADJUDICATION_DEPTH}}

    def _summarize(self, result: dict, moves: list, board: chess.Board) -> dict:
        for side, s in self.stats.items():
            s["legality_rate"] = s["samples_legal"] / s["samples_total"] if s["samples_total"] else 0.0
            s["mean_candidates_at_pick"] = s["candidates_at_pick"] / s["moves"] if s["moves"] else 0.0
        return {**result, "plies": len(moves), "final_fen": board.fen(),
                "budgets_left": dict(self.budgets), "memory": dict(self.memory),
                "spend_history": self.spend_history, "notes": self.notes,
                "stats": self.stats, "turns": self.turn_log}


# ---------------------------------------------------------------- matches

def run_match(out_dir: str, budget: int, games: int, white_spec: str, black_spec: str,
              device: str = "mps", log_dir: str = None) -> dict:
    daydream = DaydreamPlayer(out_dir, device=device)
    by_spec = {}
    for g in range(games):
        specs = (white_spec, black_spec) if g % 2 == 0 else (black_spec, white_spec)
        (white, wmem), (black, bmem) = make_player3(specs[0], seed=g), make_player3(specs[1], seed=g)
        rng = random.Random(1000 + g)
        game = TokenChess3Game(daydream, white, black, budget, rng,
                               memory={"white": wmem, "black": bmem})
        r = game.play()
        r["white_player"], r["black_player"] = specs
        for spec, player in ((specs[0], white), (specs[1], black)):
            if hasattr(player, "stats") and hasattr(player, "orchestrator"):
                r.setdefault("llm_usage", {})[spec] = dict(player.stats)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, f"game-{g + 1:03d}.json"), "w") as f:
                json.dump(r, f, indent=2)
        adj = r.get("adjudication")
        adj_note = f" adj cp(white)={adj['white_cp']}" if adj and adj.get("white_cp") is not None else ""
        print(f"  game {g + 1}/{games}: {r['outcome']}, winner={r['winner']}, plies={r['plies']},"
              f" spent={{w:{r['stats']['white']['tokens_spent']},b:{r['stats']['black']['tokens_spent']}}}{adj_note}",
              flush=True)
        for side in ("white", "black"):
            spec, s = r[f"{side}_player"], r["stats"][side]
            e = by_spec.setdefault(spec, {"games": 0, "score": 0.0, "wins": 0, "draws": 0,
                                          "tokens": 0, "moves": 0, "cand": 0.0, "legal": [0, 0]})
            e["games"] += 1
            e["tokens"] += s["tokens_spent"]
            e["moves"] += s["moves"]
            e["cand"] += s["candidates_at_pick"]
            e["legal"][0] += s["samples_legal"]
            e["legal"][1] += s["samples_total"]
            if r["winner"] == side:
                e["score"] += 1.0
                e["wins"] += 1
            elif r["winner"] is None:
                e["score"] += 0.5
                e["draws"] += 1

    summary = {}
    for spec, e in by_spec.items():
        summary[spec] = {
            "games": e["games"], "wins": e["wins"], "draws": e["draws"],
            "score_rate": e["score"] / e["games"],
            "tokens_spent": e["tokens"],
            "wins_per_token": e["wins"] / e["tokens"] if e["tokens"] else 0.0,
            "mean_candidates_at_pick": e["cand"] / e["moves"] if e["moves"] else 0.0,
            "sample_legality": e["legal"][0] / e["legal"][1] if e["legal"][1] else 0.0,
        }
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", default="projects/daydream/runs/regular-r1")
    ap.add_argument("--budget", type=int, default=40)
    ap.add_argument("--games", type=int, default=4)
    ap.add_argument("--white", default="mock:heuristic")
    ap.add_argument("--black", default="mock:random")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--log_dir", default=None)
    args = ap.parse_args()

    summary = run_match(args.out_dir, args.budget, args.games,
                        args.white, args.black, args.device, args.log_dir)
    print("\n=== Token Chess 3 ===", flush=True)
    for spec, s in summary.items():
        print(f"  {spec}: games={s['games']} score={s['score_rate']:.2f} "
              f"(w{s['wins']}/d{s['draws']}) tokens={s['tokens_spent']} "
              f"cand/pick={s['mean_candidates_at_pick']:.2f} legality={s['sample_legality']:.2f}",
              flush=True)


if __name__ == "__main__":
    main()
