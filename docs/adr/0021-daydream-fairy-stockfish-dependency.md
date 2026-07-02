# ADR 0021: Daydream depends on Fairy-Stockfish as an external engine binary

- **Status:** Accepted
- **Date:** 2026-07-02
- **Deciders:** Romello Goodman (with Claude)

## Context

`daydream` needs two things no existing project needs: a way to generate a
training corpus for board sizes no human game database covers (Micro's 5×5,
Grand's 12-file×10-rank), and a way to check whether a candidate chess move
is legal in an arbitrary position, on an arbitrary board, at inference time
(the harness's resample-on-illegal mechanic). `python-chess` — already a
dependency for Regular's Lichess PGN parsing — only understands standard
8×8 chess; it has no concept of Micro's or Grand's board geometry or piece
set, so it can't serve either need for those two tiers.

Every other project in this monorepo (`core`, shakespeare, gatsby,
kenosha-kid) is a pure Python + PyTorch stack with no external binary
dependency. This is the first project that needs one.

## Decision

We will depend on **Fairy-Stockfish**, a chess-variant engine built on
Stockfish's search/evaluation, installed as a system binary via Homebrew
(`brew install fairy-stockfish`) and driven over its UCI protocol via
subprocess — not as a pip package, because it isn't one.

Fairy-Stockfish plays two roles, both accessed through the single shared
`engine_client.Engine` class:

1. **Self-play corpus generation** for Micro and Grand (`data/selfplay.py`):
   two engine instances play each other under the tier's variant rules,
   with randomized opening plies for game-to-game diversity (fixed-depth
   search is otherwise fully deterministic).
2. **Legality arbiter** in `harness.py`: a candidate move from the trained
   model is legal if and only if it appears in Fairy-Stockfish's own
   `go perft 1` legal-move list for the current position. This is the same
   code path for all three tiers, so the "legal" answer for Micro, Regular,
   and Grand all come from the identical mechanism, not three
   reimplementations that could quietly disagree.

Micro uses Fairy-Stockfish's **built-in** `gardner` variant directly — no
custom config needed. Grand needs a custom variant, defined in
`engine/variants.ini`, inheriting from the built-in `grand` (real Grand
Chess, verified via the running engine, not assumed from documentation —
see below) and overriding board size and starting position.

## Consequences

**Easier:**
- Legality checking and self-play corpus generation share one
  battle-tested engine and one code path, instead of three tiers each
  needing bespoke rules logic.
- Fairy-Stockfish's variant system (`maxRank`/`maxFile`, inheritance,
  runtime-loaded `.ini` config) means Grand's custom board needed a dozen
  lines of config, not new engine code.

**Harder / debt accepted:**
- **A non-Python, non-pip build dependency now exists in this repo for the
  first time.** Anyone building `daydream` from scratch needs
  `brew install fairy-stockfish` before anything in this project runs — a
  step no other project requires, and one `uv sync` cannot do for them.
  This needs to be stated loudly in `projects/daydream/README.md` (it is).
- **The installed engine's real limits, not its documentation, are
  authoritative — and they surprised us twice during this build.** Web
  research (not the engine itself) suggested Grand Chess has two Chancellors
  and two Archbishops per side and that Fairy-Stockfish supports boards up
  to 36×36; querying the actual running binary (`setoption name UCI_Variant
  value grand` + `d`) showed the real base variant has only one of each
  compound piece, and `stockfish check` on a 12×12 config rejected it — the
  installed build's `Rank` option type caps at 10 even though `File` goes to
  12. Grand's design (12 files × 10 ranks, 2 Chancellor + 2 Archbishop per
  side) was corrected against the live engine, not the original plan. Future
  changes to Micro/Grand's board specs must be validated the same way
  (`stockfish check variants.ini`, then `setoption` + `d` to actually look
  at the board) rather than trusted from external sources.
- **Corpus generation quality is bounded by search depth, not skill
  settings.** Self-play uses bounded-depth search (fast, not
  strength-reduced) plus randomized openings for diversity; this is a
  deliberate choice (see the daydream design plan: "pure self-play, not
  strength-varied" — the dream texture should come from the trained model
  and sampler, not be pre-baked into the corpus), but it does mean Micro's
  and Grand's corpora are only as good as bounded-depth Fairy-Stockfish
  play, not tournament-strength play.

## Alternatives considered

- **Write a from-scratch legal-move generator per board size.** Rejected:
  duplicates well-tested logic for three different board geometries
  (including a genuinely new one, Grand's 12×10 with compound pieces) for
  no benefit over an existing, correct engine.
- **`python-chess` alone.** Rejected: no support for non-standard boards or
  piece types at all — it can't serve Micro or Grand under any
  configuration, only Regular.
- **Compile Fairy-Stockfish from source with expanded board-size limits**
  (to get true 12×12 for Grand). Rejected for this build: a materially
  bigger, riskier undertaking (modifying and building an unfamiliar C++
  codebase) than adjusting the board to fit the shipped Homebrew binary's
  real limits (12 files × 10 ranks instead of 12×12) — see the Consequences
  section above. Revisit only if 12×12 specifically (not just "bigger than
  10×10") turns out to matter for reasons that emerge later.
