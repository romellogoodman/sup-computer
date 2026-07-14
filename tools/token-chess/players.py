"""
players.py -- the Player adapter interface for Token Chess. Three kinds of
adapter behind one interface: mock:* (random / adaptive / heuristic
self-tests), lmstudio:<model> (LIVE matches on any OpenAI-compatible local
server via the shared tools/steer layer, ADR-0026 -- this is how every
round-three-and-later result was produced), and anthropic:<model>
(reserved for when API credentials exist).

Every adapter implements the same contract: given the transcript of
attempts made *this turn only* and its own remaining budget, choose
sampler settings for the next Daydream query. Swapping adapters requires
zero changes to game.py / game3.py.
"""
from __future__ import annotations

import os
import random
import sys
from abc import ABC, abstractmethod

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from steer import Orchestrator  # noqa: E402


class Player(ABC):
    """One Token Chess player. Sees only its own remaining budget (never the
    opponent's -- budgets are hidden, per the locked design) and the
    transcript of attempts made so far *this turn* (cleared each turn)."""

    @abstractmethod
    def choose_config(self, own_budget: int, transcript_this_turn: list) -> dict:
        """Return {'temperature': float, 'soft_cap': float or None} for the
        next Daydream query. transcript_this_turn is a list of dicts:
        {'temperature', 'soft_cap', 'move', 'legal'} for every attempt made
        this turn so far (empty on the first attempt of a turn)."""
        raise NotImplementedError


class RandomPlayer(Player):
    """Picks uniformly random settings every attempt -- a floor baseline,
    ignores the transcript entirely (no learning within or across turns)."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def choose_config(self, own_budget: int, transcript_this_turn: list) -> dict:
        return {
            "temperature": self.rng.uniform(0.3, 1.5),
            "soft_cap": self.rng.choice([None, 5.0, 10.0, 20.0]),
        }


class AdaptivePlayer(Player):
    """A simple heuristic mock that DOES react to the transcript: starts
    cool and tightly capped (favoring legality), and on repeated failure
    within a turn, progressively loosens temperature and soft-cap --
    approximating "if tight settings keep failing, this position might need
    more exploration." Exists mainly to give the harness's sampling-
    adaptation metric something non-trivial to measure against RandomPlayer."""

    def __init__(self, base_temperature: float = 0.5, base_soft_cap: float = 5.0):
        self.base_temperature = base_temperature
        self.base_soft_cap = base_soft_cap

    def choose_config(self, own_budget: int, transcript_this_turn: list) -> dict:
        failures = len(transcript_this_turn)
        temperature = min(self.base_temperature + 0.15 * failures, 2.0)
        soft_cap = None if failures >= 3 else self.base_soft_cap + 3.0 * failures
        return {"temperature": temperature, "soft_cap": soft_cap}


# The seeding the locked design prescribes: conceptual knowledge of the
# mechanics and the sampler knobs up front; the empirical legality curve has
# to be learned live, turn by turn.
LLM_SEED = """You are playing Token Chess. You cannot author chess moves yourself. \
The only move source is Daydream, a 2.7M-parameter character-level GPT trained on \
chess games (it learned move TEXT from games, not the rules -- its samples are \
often illegal). Each turn you must land a LEGAL move by querying Daydream.

Mechanics:
- Every Daydream query costs exactly 1 token from your budget, legal or not.
- If you spend your last token and still have no legal move, you FORFEIT immediately.
- Each query you choose two sampler settings:
  - temperature (float, 0.1-2.0): lower = Daydream's most-confident move text; \
higher = more varied, more error-prone.
  - soft_cap (float > 0, or null): Gemma-style logit soft-capping. Lower caps \
flatten Daydream's confidence spikes; null disables it.
- You see only the attempts made THIS turn. The log clears when your turn ends.

Respond with ONLY a JSON object, no prose: {"temperature": <float>, "soft_cap": <float or null>}"""

FALLBACK_CONFIG = {"temperature": 0.5, "soft_cap": 5.0}


def _validate_config(obj) -> dict:
    """Normalize a parsed sampler-config decision; None rejects it."""
    try:
        temperature = float(obj["temperature"])
    except (KeyError, TypeError, ValueError):
        return None
    soft_cap = obj.get("soft_cap")
    if soft_cap is not None:
        try:
            soft_cap = float(soft_cap)
        except (TypeError, ValueError):
            return None
        if soft_cap <= 0:
            soft_cap = None
    return {"temperature": min(max(temperature, 0.05), 3.0), "soft_cap": soft_cap}


class LLMPlayer(Player):
    """A real player: an instruction-following LLM chooses the sampler
    settings, via the shared steer.Orchestrator (one stateless decision per
    attempt -- the per-turn transcript scoping lives in the harness, not in
    conversation state). This class owns only the chess vocabulary: the seed
    prompt, the config validator, and how a turn is rendered."""

    def __init__(self, client, own_temperature: float = 0.7):
        self.orchestrator = Orchestrator(client, LLM_SEED, _validate_config, FALLBACK_CONFIG, own_temperature)

    @property
    def stats(self) -> dict:
        return self.orchestrator.stats

    def choose_config(self, own_budget: int, transcript_this_turn: list) -> dict:
        return self.orchestrator.decide(self._render_state(own_budget, transcript_this_turn))

    @staticmethod
    def _render_state(own_budget: int, transcript_this_turn: list) -> str:
        lines = [f"Your remaining budget: {own_budget} tokens."]
        if transcript_this_turn:
            lines.append("Attempts this turn so far:")
            for a in transcript_this_turn:
                cap = "null" if a["soft_cap"] is None else a["soft_cap"]
                verdict = "LEGAL" if a["legal"] else "ILLEGAL"
                lines.append(f'- temperature={a["temperature"]:.2f} soft_cap={cap} -> "{a["move"]}" {verdict}')
        else:
            lines.append("First attempt of this turn.")
        lines.append("Choose settings for the next query.")
        return "\n".join(lines)
