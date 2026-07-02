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

import random
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
