# CLAUDE.md — rules for agents working in daydream

Facts live in [`README.md`](README.md) — the project, tiers, pipeline, version
index (§ Versions), and scoreboard (§ Leaderboard). This file is only the
rules (ADR-0030).

## Don't relitigate

- **Render illegal moves, don't discard them.** The sampler choice is the
  aesthetic decision, not a correctness filter. Anything that
  resamples-until-legal and throws away the rejected attempts is missing the
  point of this project.
- **UCI, not SAN.** A UCI string is well-formed even when illegal in the
  current position; SAN bakes legality into the notation and can't produce
  that state. Never switch a tier's corpus or tokenizer to SAN.
- **Three tiers, three everything.** Micro, Regular, and Grand each have
  their own corpus, tokenizer, config, and trained model — never share a
  vocab or checkpoint across tiers (UCI square names depend on board
  dimensions).
- **Char-level, on the shared `core`** (`meta.pkl` contract, ADR-0012). **Do
  not fork or vendor an engine** — it's char-level tokenization over a
  different alphabet, nothing more.
- **Fairy-Stockfish is a dev-time binary dependency, not a Python package**
  (Homebrew, subprocess — ADR-0021). It is both the self-play corpus
  generator and the legality arbiter.
- **Grand's board is 12 files × 10 ranks, not 12×12** — the installed
  Fairy-Stockfish caps `Rank` at 10. Extend files, not ranks, if Grand ever
  grows.

## Conventions

- **Verification is a two-part automated gate, nothing more**: games complete
  without crashing, and legal-move rate clears a threshold. Win rate and
  dream-rendering quality are explicitly *not* automated gates.
- Run everything from the **repo root** via `uv run`.
- **Document as you go**: `research/log.md` (why) and the README's
  Leaderboard section (per-run scoreboard), committed with the run.
- **Releases**: each tier releases independently as a frozen snapshot under
  `models/` (Regular is unsuffixed), per
  [`docs/handbook.md`](../../docs/handbook.md#releasing-a-version).
- **Credit the researcher** — root [`CLAUDE.md`](../../CLAUDE.md), ADR-0013.
