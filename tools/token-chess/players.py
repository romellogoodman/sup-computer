"""
players.py -- the Player adapter interface for Token Chess, plus mock
implementations used to exercise the harness without any live frontier
model API (no credentials exist in this environment -- see the Token Chess
design plan's "harness only, no real matches" scope for this build).

A real adapter (Claude, Gemini, whichever) would implement the same
interface: given the transcript of attempts made *this turn only* and its
own remaining budget, choose sampler settings for the next Daydream query.
Swapping a mock for a real API-backed adapter should require zero changes
to game.py.
"""
from __future__ import annotations

import json
import random
import re
from abc import ABC, abstractmethod


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


class LLMPlayer(Player):
    """A real player: an instruction-following LLM (local or hosted) chooses
    the sampler settings. One stateless chat call per attempt -- the per-turn
    transcript scoping lives in the harness, not in conversation state.

    Malformed output gets one free re-prompt, then FALLBACK_CONFIG, so a game
    token is always spent on a real Daydream query; parse failures are counted
    (instruction-following under pressure is worth measuring, not crashing on).
    """

    def __init__(self, client, own_temperature: float = 0.7):
        self.client = client
        self.own_temperature = own_temperature
        self.stats = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0, "parse_failures": 0}

    def choose_config(self, own_budget: int, transcript_this_turn: list) -> dict:
        user = self._render_state(own_budget, transcript_this_turn)
        for attempt in range(2):  # one free re-prompt on unparseable output
            text = self._chat(user if attempt == 0 else user + self._reprompt_suffix())
            config = self._parse(text)
            if config is not None:
                return config
            self.stats["parse_failures"] += 1
        return dict(FALLBACK_CONFIG)

    def _chat(self, user: str) -> str:
        text, usage = self.client.chat(LLM_SEED, user, temperature=self.own_temperature)
        self.stats["calls"] += 1
        self.stats["prompt_tokens"] += usage.get("prompt_tokens", 0)
        self.stats["completion_tokens"] += usage.get("completion_tokens", 0)
        return text

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

    @staticmethod
    def _reprompt_suffix() -> str:
        return '\n\nYour previous reply was not a parseable JSON object. Reply with ONLY: {"temperature": <float>, "soft_cap": <float or null>}'

    @staticmethod
    def _parse(text: str):
        m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
            temperature = float(obj["temperature"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
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
