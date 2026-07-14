# CLAUDE.md — conventions for agents working in daydream

`daydream` is a chess-move GPT that hallucinates chess rather than plays it
well: legal moves snap into focus, illegal moves render as dim near-misses
instead of being masked away. Start with [`README.md`](README.md).

## The core idea (don't relitigate these)

- **Render illegal moves, don't discard them.** Most chess-model work treats
  illegal output as failure to be masked or rejection-sampled away. Daydream
  inverts that — the sampler choice is the aesthetic decision, not a
  correctness filter. Anything that resamples-until-legal and throws away
  the rejected attempts is missing the point of this project.
- **UCI, not SAN.** A UCI string (`e2e4`) is well-formed even when illegal in
  the current position; SAN bakes legality into the notation itself and
  can't produce that "syntactically valid, semantically impossible" state.
  Never switch a tier's corpus or tokenizer to SAN.
- **Three tiers, three everything.** Micro (5×5), Regular (8×8), Grand (12
  files × 10 ranks) each have their own corpus, tokenizer, config, and
  trained model — never share a vocab or checkpoint across tiers. UCI square
  names depend on board dimensions, so a Micro-trained model's vocabulary is
  meaningless on Grand's board and vice versa.
- **Char-level, on the shared `core`.** Same `meta.pkl` contract as every
  other project (ADR-0012) — `prepare.py` builds `stoi`/`itos` over each
  tier's own UCI character set (file letters, rank digits, promotion
  letters, space, newline) the same way kenosha-kid/shakespeare build theirs
  over English text. **Do not fork or vendor an engine to support this** —
  it's char-level tokenization over a different alphabet, nothing more.
- **Fairy-Stockfish is a build/dev-time binary dependency, not a Python
  package.** Installed via Homebrew, invoked as a subprocess (`fairy-stockfish`
  on `PATH`). It plays both roles: self-play corpus generator for Micro/Grand,
  and the legality arbiter in `harness.py`. See
  [ADR-0021](../../docs/adr/0021-daydream-fairy-stockfish-dependency.md).
- **Grand's board is 12 files × 10 ranks, not 12×12.** The installed
  Fairy-Stockfish build caps the `Rank` option type at 10 even though `File`
  goes to 12 — a real engine constraint discovered during the build, not a
  design choice. Don't "fix" this by trying to force a taller board; extend
  files, not ranks, if Grand ever needs to grow further.

## Pipeline & conventions

- Regular: `data/regular/fetch_filtered.py` streams a Lichess monthly
  `.pgn.zst` dump directly (zstandard decompression, no full download to
  disk), filters by Elo band + game-length in the same pass via
  python-chess (no `pgn-extract` dependency needed), stops once it has
  enough qualifying games, and writes UCI move lines straight to
  `data/regular/games.txt` — gitignored like shakespeare's downloaded data,
  not committed like kenosha-kid's synthetic `raw.txt` (Regular's corpus is
  real third-party game data, not code-owned/deterministic). Regenerate by
  rerunning the script. `prepare.py` then char-tokenizes that file →
  `train.bin`/`val.bin`/`meta.pkl` (also gitignored).
- Micro / Grand: the shared `data/selfplay.py --variant <gardner|grand12>`
  (Fairy-Stockfish self-play under the tier's variant rules) →
  `data/prepare.py --tier <tier>` → same `.bin`/`.pkl` shape.
- All three feed `core/nanogpt_core/train.py` identically — the engine
  never knows it's training on chess.
- `harness.py` is shared across all three tiers, parameterized by which
  variant config / board size to use. It plays the checkpoint against
  Fairy-Stockfish (skill-limited), resamples the model's move on illegal
  output, and forces a uniformly-random legal move once a resample cap is
  hit (game always completes) rather than aborting.
- **Verification is a two-part automated gate, nothing more**: games
  complete without crashing, and legal-move rate clears a threshold. Win
  rate against the opponent and dream-rendering quality are explicitly
  *not* automated gates — the former isn't the point of this project, the
  latter is a manual/aesthetic judgment call.
- Run everything from the **repo root** via `uv run`.
- **Document as you go.** Update `research/log.md` and `leaderboard.md`
  per run, same as every other project.
- **Credit the researcher** — root rule, ADR-0013.

## Releases

Each tier releases independently as its own frozen snapshot under
`models/daydream-chess-nanogpt-<tier>-N/` (Regular is unsuffixed:
`daydream-chess-nanogpt-1`), pinned to its own git tag. The release
checklist lives in one place: [`docs/releasing.md`](../../docs/releasing.md).
Frozen folders are never refactored to share `core/` or each other.
