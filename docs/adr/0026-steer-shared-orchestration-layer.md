# ADR 0026: `tools/steer` — the shared shape for a big model steering a small one

- **Status:** Accepted
- **Date:** 2026-07-04
- **Deciders:** Romello Goodman (with Claude)

## Context

Token Chess grew a real LLM player (local models via LM Studio's
OpenAI-compatible API), and the linewell composition harness
(`tools/linewell/`) immediately wanted the same machinery:
an instruction-following LLM that, each step, reads rendered state and
returns one JSON decision, with parse-retry, a safe fallback, and token
accounting. That made poetry the second consumer — the monorepo's standing
trigger for extracting an abstraction (see TODO's second-consumer rule).

The explicit constraint from the studio lead: do **not** let Token Chess's
domain shape leak — `Player` is chess vocabulary (a seat in a two-player
game), and the poem harness must not inherit it or any other chess artifact.

## Decision

**`tools/steer/`** holds exactly two pieces, and nothing domain-shaped:

- `OpenAICompatClient` — transport. One stateless chat call against any
  OpenAI-compatible server (LM Studio default via `STEER_BASE_URL`, Ollama's
  `/v1` unchanged; an Anthropic sibling implements the same two-method
  surface when credentials exist).
- `Orchestrator` — the steering seam. Constructed with a system prompt, a
  domain `validate()` (parsed dict → normalized decision, or None), and a
  fallback decision; `decide(state)` guarantees a usable decision (one free
  re-prompt, then fallback) and counts parse failures as a first-class
  metric.

Domain harnesses keep their own vocabulary and mechanics and meet only at
this seam: Token Chess's `Player`/`LLMPlayer` (players, budgets, forfeits)
stay inside `tools/token-chess/`; the poem loop's `LineWell` and judges
(`BandJudge`, `LLMJudge`, `HumanJudge`) stay inside
`tools/linewell/`. Neither imports the other.

## Consequences

- One place fixes JSON-coaxing quirks for every harness; usage accounting is
  uniform, so "inference tokens burned per unit of work" is comparable
  across chess and poetry.
- The steering LLM's decision protocol (system prompt + validate + fallback)
  is now three constructor arguments — a new harness is those three things
  plus its own loop, which is the right amount of ceremony.
- `steer` is deliberately not a home for domain state (transcripts, budgets,
  poems). If a third consumer wants shared *state* handling, that's a new
  decision, not creep into this one.
- Token Chess's `clients.py` is gone; anything scripted against
  `TOKEN_CHESS_BASE_URL` must use `STEER_BASE_URL`.

## Alternatives considered

- **Porting Token Chess's `Player` shape to the poem harness.** Rejected by
  direction: a poem has no seats, opponents, or hidden budgets; `Player`
  everywhere would be chess leaking into every future harness's API.
- **A full generic "benchmark kit" (state, budgets, transcripts, scoring).**
  Rejected as premature: two consumers share the steering call, not their
  mechanics. Extracting more than is shared would force chess shapes onto
  poems anyway — the exact failure the constraint names.
- **Duplicate the ~90 lines in both harnesses.** Rejected: the parse-retry/
  fallback/usage logic is the part that accumulates fixes; two drifting
  copies of it is how subtle metric skew happens.
