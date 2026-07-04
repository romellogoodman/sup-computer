"""
steer -- the studio's shared shape for a big model steering a small one.

Two pieces, deliberately tiny:

  OpenAICompatClient  -- transport: one stateless chat call against any
                         OpenAI-compatible server (LM Studio, Ollama /v1;
                         an Anthropic sibling would match the same
                         two-method surface).
  Orchestrator        -- the loop seam: rendered state in, one validated
                         JSON decision out, with parse-retry, a safe
                         fallback, and token-usage accounting.

Domain harnesses own their vocabulary and mechanics -- token-chess has
players and budgets, the shakespeare poem loop has judges and lines --
and meet here only for the steering call itself. Extracted when the poem
harness became the second consumer of what token-chess built (the
monorepo's second-consumer rule).
"""
from .client import OpenAICompatClient
from .orchestrator import Orchestrator

__all__ = ["OpenAICompatClient", "Orchestrator"]
