# steer — the shared shape for a big model steering a small one

Two pieces, deliberately tiny ([ADR-0026](../../docs/adr/0026-steer-shared-orchestration-layer.md)):

- **`OpenAICompatClient`** (`client.py`) — transport: one stateless chat call
  against any OpenAI-compatible server. LM Studio on `localhost:1234` by
  default; `STEER_BASE_URL` overrides. An Anthropic sibling would match the
  same two-method surface.
- **`Orchestrator`** (`orchestrator.py`) — the loop seam: rendered state in,
  one validated JSON decision out, with parse-retry, a safe fallback, and
  token-usage accounting.

Domain harnesses own their vocabulary and mechanics —
[`token-chess`](../token-chess/) has players and budgets,
[`linewell`](../linewell/) has judges and lines — and meet here only for the
steering call itself. Extracted when linewell became the second consumer of
what token-chess built (the monorepo's second-consumer rule).

```python
from steer import OpenAICompatClient, Orchestrator
```

Run consumers from the repo root; they `sys.path`-insert `tools/`.

Known consolidation candidate: [`synthgen`](../synthgen/) predates steer and
carries its own urllib transport to the same server (`SYNTHGEN_BASE_URL`,
its own retry policy, `reasoning_effort` suppression). Fold them together
the next time either transport changes — not before.
