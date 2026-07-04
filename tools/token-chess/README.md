# Token Chess

A benchmark, not a model: two players share a chess board, but neither can
play a move from its own reasoning. Every move must come from
[Daydream](../../projects/daydream/README.md), queried as a tool, under a
fixed per-game token budget. The benchmark measures how economically a
player orchestrates Daydream's sampler under scarcity — not chess
strength. Full design rationale: `~/Desktop/token-chess-benchmark-plan.md`.

## Status

**Live matches run on local models.** `players.py` ships `LLMPlayer`, which
rides the shared [`tools/steer`](../steer/) layer
([ADR-0026](../../docs/adr/0026-steer-shared-orchestration-layer.md)) to any
OpenAI-compatible server — LM Studio by default (`STEER_BASE_URL`
overrides). Player specs on the CLI:

```bash
uv run python tools/token-chess/game.py --tier regular \
    --out_dir projects/daydream/runs/regular-r1 --budget 40 --games 4 \
    --white "lmstudio:qwen/qwen3.6-27b" --black lmstudio:olmo-3-7b-instruct \
    --log_dir /tmp/tc-logs        # per-game JSON with the full attempt log
```

The mocks (`mock:adaptive`, `mock:random`) remain as harness self-tests, and
`anthropic:<model>` is reserved for when API credentials exist. Early
calibration findings (olmo-3-7b vs itself): Daydream Regular's legality
collapses with game depth (≈49% in plies 0–9 → ≈14% by plies 30–39), so
forfeits dominate at every budget tried up to 120 — the discriminative
budget zone is ~15–40, and the Micro tier is a *harder* tool (≈10%
legality), not a cheaper one.

## Locked mechanics

- **Daydream-exclusive**: the only way to move is a Daydream query that
  lands legal. No self-authored moves.
- **Every query costs exactly 1 token**, regardless of sampler settings or
  outcome.
- **Per-turn transcript scoping**: a player sees every attempt made *this
  turn*, cleared when the turn passes — no persistent cross-game sampler
  model.
- **Budget exhaustion = immediate forfeit.**
- **Budgets are hidden** — each player sees only its own remaining tokens.
- **Headline metric**: games won per token spent. Reported alongside plain
  win rate, legality hit rate, and turn-level sampling adaptation.

## Self-test result

Against the in-progress `daydream-chess-nanogpt-1` checkpoint (Regular,
8×8), 4 games, budget 15: the adaptive mock player beat the random mock
0.75 vs 0.25 win rate, with a higher wins-per-token and legal-hit-rate —
confirming the budget/forfeit/transcript-scoping mechanics reward better
sampler orchestration, as designed.

## Run it

```bash
uv run python tools/token-chess/game.py \
    --tier regular --out_dir projects/daydream/runs/regular-r1 \
    --budget 40 --games 6
```

Requires Fairy-Stockfish on `PATH` (reuses Daydream's legality-check
primitive as the arbiter) and a trained Daydream checkpoint for the given
tier.
