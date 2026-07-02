# Research log — daydream

## 2026-07-02 — first build, all three tiers

Built the full pipeline from the locked design plan
(`~/Desktop/daydream-chess-project-plan.md`) in one pass: Fairy-Stockfish
installed via Homebrew (ADR-0021), project scaffolded riding `core/`
directly (ADR-0022), Grand's variant config corrected against the live
engine rather than trusted from web research (real Grand Chess has one
Chancellor + one Archbishop per side, not two; the installed build's board
caps at 12 files × 10 ranks, not 12×12 — both discovered via
`setoption name UCI_Variant` + `d` and `stockfish check`, not documentation).

- **Regular**: 15,000 Lichess games, ~1400-1800 Elo, streamed and filtered
  from the January 2018 monthly dump without storing the full ~5.5GB
  compressed file (zstd streaming decode + early stop once the target game
  count was reached). Vocab size 21.
- **Micro**: Fairy-Stockfish self-play under the built-in `gardner` variant.
  First attempt produced fully deterministic, identical games (fixed-depth
  search has no exploration on its own) — fixed with randomized opening
  plies (sourced from `go perft 1`'s legal-move list) plus a simple
  repetition-window cutoff for games that fell into shuffling loops.
- **Grand**: Fairy-Stockfish self-play under the custom `grand12` variant
  (12 files × 10 ranks, 2 Chancellor + 2 Archbishop per side, mirrored
  symmetrically — corrected from an initially-wrong "2+4" piece count that
  came from trusting a web search summary over the actual engine).
- **Harness**: board-size-parameterized, resamples the model on illegal
  moves, forces a random legal move on hitting the resample cap (locked
  fallback), tracks first-try legality for the verification gate. Verified
  functional against Regular's in-progress checkpoint (produces UCI-shaped
  output early in training, not yet reliably legal — expected at low
  iteration counts, not a bug: confirmed via raw `sample.py` output showing
  structurally correct but not-yet-legal moves).
- **Token Chess**: harness built at `tools/token-chess/`, mock players only
  (no frontier-model API credentials in this environment). Self-test against
  the in-progress Regular checkpoint showed the adaptive mock player
  clearly outperforming the random mock (0.75 vs 0.25 win rate, higher
  wins-per-token and legal-hit-rate) — the budget/forfeit/transcript-scoping
  mechanics all behave as designed.

See `leaderboard.md` for per-run numbers and the model cards in
`research-docs/model-cards/` for the released write-up of each tier.
