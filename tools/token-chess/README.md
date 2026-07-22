# Token Chess

*The benchmark: LLMs orchestrate Daydream's sampler under a token budget.*

A benchmark, not a model: two players share a chess board, but neither can
play a move from its own reasoning. Every move must come from
[Daydream](../../projects/daydream/README.md), queried as a tool, under a
fixed per-game token budget. The benchmark measures how economically a
player orchestrates Daydream's sampler under scarcity — not chess strength.
The locked mechanics are recorded in this README (the two "Locked mechanics"
sections below are the contract — update them or don't change the code); the
findings are in
[Can a token budget buy a finished chess game?](../../research-docs/reports/budget-cant-buy-the-midgame.md)

## File map

| File | Round | Status |
|---|---|---|
| `game.py` | one | **Frozen yardstick.** Round-one forfeit economy, locked; don't refactor. |
| `game3.py` | three–five | **Live harness.** Batch-of-3 economy, adjudication endings, memory/choice suffixes. |
| `players.py` | all | **Live.** Player adapters: `mock:*` self-tests, `lmstudio:<model>` live local models, `anthropic:` reserved. |
| `round2_probe.py` | two | Retired probe, kept as apparatus — the only way to observe games past ply ~40. |
| `round3_probe.py` | three | Retired probe, kept as apparatus — floor / curation / depth / linewell probes. |
| `pgn_export.py` | — | Exporter: archived game JSONs → replayable PGNs in `evidence/pgn/`. |

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
legality), not a cheaper one. Full write-up:
[Can a token budget buy a finished chess game?](../../research-docs/reports/budget-cant-buy-the-midgame.md)

## The round-two probe (mechanics stay locked)

`round2_probe.py` tested the obvious redesign — replace forfeits with a
bankable per-turn income plus a *silent* harness fallback that
rejection-samples Daydream when a player's bank runs dry — and rejected
it: every game completes (7 of 9 as threefold-repetition draws), but
discrimination vanishes — random sampler configs match the tuned mock
and olmo-3-7b on control rate, attempts per controlled move, and spend.
Side finding: past the old forfeit wall, Daydream Regular's legality is
a *floor* (8–12% per 50-ply band out past ply 250), not a continuing
collapse. The probe stays in-tree as measurement apparatus (it is the
only way to observe games past ply ~40); the locked mechanics below are
unchanged. Full write-up (rounds one through four, one report):
[Can a token budget buy a finished chess game?](../../research-docs/reports/budget-cant-buy-the-midgame.md)

## Locked mechanics — round one (`game.py`)

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

## Locked mechanics — round three (`game3.py`)

Round one priced config skill and found all-forfeits; the round-two probe
removed death and found the refund economy erases discrimination; the
round-three probes found the two levers that survive (the legality floor
is config-dependent ~8–30%, and best-of-N picking won every decisive
game). Round three prices both levers:

- **A token buys a batch of 3**: the player chooses `{temperature,
  soft_cap}`, the harness draws three samples at it; the legal ones join
  the turn's candidate pool (deduped).
- **Picking is free**: play any pooled candidate, or spend another token
  on another batch — economy against move quality, every turn.
- **Exhaustion = adjudication, not forfeit**: a player to move with no
  tokens and no candidates ends the game; Fairy-Stockfish evaluates the
  final position (mate scores or |cp| ≥ 100 decide a winner, else draw).
  The board gets the last word; the clock only decides when it's spoken.
- Unchanged from round one: Daydream-exclusive moves, per-turn transcript
  scoping, hidden budgets.
- **Headline metric**: color-balanced score (win = 1, draw = 0.5),
  reported with tokens spent, candidates per pick, sample legality, and
  adjudication vs on-board endings. Game JSONs carry LLM usage stats
  (calls, tokens, parse failures) — round one's logging gap, closed.
- Regular tier only for now; `mock:heuristic` (best-known config + a
  mate>capture>check pick rule) is the qualifying bar a real player
  should beat.

Round-three live results (budget 40, 4 games each, color-balanced):
olmo-3-7b beat the mock bar 3.5–0.5 on pick quality and economy, beat
granite-4.1-8b 3.5–0.5 with the knobs tied — and lost 3–1 to
ministral-3-8b, the worst sampler on the board (20% legality vs olmo's
58%), which spends its whole budget fast and exhausts while ahead.
Write-up: rounds section of
[Can a token budget buy a finished chess game?](../../research-docs/reports/budget-cant-buy-the-midgame.md)

Round four added per-player memory to the same mechanics — spec
suffixes `+ledger` (own spend history, harness-rendered) and `+notepad`
(model-authored notes, last 3 shown back). In 24 olmo-vs-olmo games the
notepad was never used once and the ledger moved no outcomes; its one
real effect was halving hot-temperature batches. Round five made the
tool a free pregame *choice* (`+choose`): 24 of 24 seats picked the
notepad, every one stated a reason, and none wrote a single note —
stated preference and revealed behavior, severed. Every archived game
is also exported as a replayable PGN (`pgn_export.py` →
`evidence/pgn/`). Write-up: rounds section of
[Can a token budget buy a finished chess game?](../../research-docs/reports/budget-cant-buy-the-midgame.md)

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
