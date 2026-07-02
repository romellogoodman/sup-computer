# Token Chess

A benchmark, not a model: two players share a chess board, but neither can
play a move from its own reasoning. Every move must come from
[Daydream](../../projects/daydream/README.md), queried as a tool, under a
fixed per-game token budget. The benchmark measures how economically a
player orchestrates Daydream's sampler under scarcity — not chess
strength. Full design rationale: `~/Desktop/token-chess-benchmark-plan.md`.

## Status

Harness built and self-tested. **No real frontier-model matches have been
run** — this environment has no API credentials for any provider, so
`players.py` ships two mock players (`RandomPlayer`, `AdaptivePlayer`) used
only to prove the harness's mechanics are correct. Swapping in a real
API-backed `Player` should require zero changes to `game.py`.

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
