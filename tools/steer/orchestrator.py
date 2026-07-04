"""The steering seam: rendered state in, one validated JSON decision out."""
from __future__ import annotations

import json
import re

REPROMPT_SUFFIX = (
    "\n\nYour previous reply was not the requested JSON object. "
    "Reply with ONLY that JSON object, no prose."
)


class Orchestrator:
    """An instruction-following LLM making one JSON decision per step.

    The domain harness supplies the system prompt (what game is being
    played), a validate() that turns a parsed dict into a normalized
    decision (or None to reject it), and a fallback decision. Malformed
    output gets one free re-prompt, then the fallback -- a step is always
    decided, never crashed; parse failures are counted, since
    instruction-following under pressure is itself worth measuring.
    """

    def __init__(self, client, system: str, validate, fallback: dict, own_temperature: float = 0.7):
        self.client = client
        self.system = system
        self.validate = validate
        self.fallback = fallback
        self.own_temperature = own_temperature
        self.stats = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0, "parse_failures": 0}

    def decide(self, state: str) -> dict:
        for attempt in range(2):  # one free re-prompt on unusable output
            text = self._chat(state if attempt == 0 else state + REPROMPT_SUFFIX)
            obj = _extract_json(text)
            decision = self.validate(obj) if obj is not None else None
            if decision is not None:
                return decision
            self.stats["parse_failures"] += 1
        return dict(self.fallback)

    def _chat(self, user: str) -> str:
        text, usage = self.client.chat(self.system, user, temperature=self.own_temperature)
        self.stats["calls"] += 1
        self.stats["prompt_tokens"] += usage.get("prompt_tokens", 0)
        self.stats["completion_tokens"] += usage.get("completion_tokens", 0)
        return text


def _extract_json(text: str):
    # LAST object wins: reasoning models think out loud before answering, and
    # the thinking may contain example JSON -- the decision is what they end
    # with, not what they mused about.
    matches = re.findall(r"\{[^{}]*\}", text, re.DOTALL)
    for candidate in reversed(matches):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None
