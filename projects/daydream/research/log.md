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

## 2026-07-02 — dreaminess sweep (eval-only, no new models)

Finished the soft-cap sweep the thesis report flagged as unfinished. Eval
only — the three frozen `runs/<tier>-r1/ckpt.pt` unchanged, nothing trained.
FULL mode (Fairy-Stockfish as legality arbiter). Grid: temperature
{0.6,0.8,1.0,1.2} × soft_cap {2.0,4.0,8.0,None}, 10 games/cell, 480 games
total. New eval script `dreaminess_sweep.py` (uncommitted); raw data under
`runs/dreaminess-sweep/`, write-up at `runs/dreaminess-sweep-samples.md`.

- **soft_cap is the dominant dreaminess dial, and it's monotonic.** Sweeping
  cap tight→off moves first-try legal-rate across the whole achievable range
  (~0% → 30–55%) on all three tiers; temperature at fixed cap moves it only
  ~10–25 points. Tight cap (2.0) = near-total dream (0–3% legal, output
  degrades into malformed non-UCI glyph-salad); cap off = legality snaps back
  and the sharpest cells produce coherent opening theory (a real Ruy Lopez
  Exchange line for ~13 legal plies before drifting). The direction is the
  Gemma-tanh mechanic: a tight cap compresses the logit spread toward
  uniform. Legality here is a *descriptive* dream-proxy, not a goal.
- **Clean completion 10/10 in all 48 cells** (forced-random fallback holds).
- **Legality decays with ply depth** (Regular 64%→9%, Grand 64%→24% from
  opening to move 30+) — the dream is a late-game phenomenon; openings lucid.
- Reproduces the report's single-config snapshot (35–39%) as the cap-off,
  temp≈0.9 special case. Did NOT touch models/, registry.json, research-docs,
  or leaderboard released rows.
