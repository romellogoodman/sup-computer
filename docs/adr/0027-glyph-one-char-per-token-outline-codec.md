# ADR 0027: glyph serializes outlines as one-char-per-token text

- **Status:** Accepted
- **Date:** 2026-07-13
- **Deciders:** Romello Goodman (with Claude)

## Context

The glyph project trains 26 per-letter specialists and a letter-conditioned
generalist on lowercase glyph outlines from ~760 OFL sans-serif families.
The serialization is the project's hard-to-reverse decision: every dataset,
every model, the eval story, and the eventual browser type tester all consume
it. Three forces shaped it:

1. **The engine contract.** Every project rides `core/` through the
   char-level `meta.pkl` contract (ADR-0012) — daydream's "move tokenizer"
   is really char-level text over UCI. Anything that keeps one glyph = one
   text line with one char = one token needs zero engine changes.
2. **Coordinates must not decompose into digits.** The lesson from Eli
   Heuer's Virtua Grotesk work: a model that never sees digits can't
   mis-compose a number; one token per grid position makes geometry local
   next-token prediction.
3. **The comparison must be fair.** Specialists and the generalist have to
   score the same held-out file identically, so the vocabulary cannot be
   derived per-dataset from `set(data)` — it must be fixed and explicit.

## Decision

We will serialize each glyph as one text line —
`<letter><advance> M <x><y> [L <x><y> | Q <cx><cy> <x><y>]* Z …` with every
symbol exactly one character — over a fixed 127-char alphabet: `a–z` (glyph
identity, the generalist's conditioning token, constant for a specialist),
verbs `M L Q Z`, 96 coordinate characters from the Braille block
(U+2800–U+285F), and newline as the glyph boundary.

Geometry: em normalized to 1024, coordinates quantized to a 16-unit grid
spanning −512…1008 (bucket ↔ `-512 + 16·b`), cubics converted to quadratics
(cu2qu) so one curve verb suffices, advance width carried as one coordinate
char so downstream renderers can set real text.

Canonical form, applied after quantization: overlaps removed at extraction
(skia-pathops), all contours wound clockwise and rendered even-odd, each
contour starting at its lowest-then-leftmost on-curve point, contours ordered
largest-first. `decode()` is a strict grammar parser and doubles as the
validity check for model output.

## Consequences

- The corpus is a greppable, diffable text file; `prepare.py` is daydream's
  pattern with a fixed alphabet; train/sample/eval/export all work unmodified,
  and the player's `CharTokenizer` covers the browser for free.
- The 16-unit grid is lossy by design — we keep the ensemble's shape, not any
  one designer's optical corrections. The round-trip sheet
  (`projects/glyph/research/roundtrip-sheet.html`, regenerate via
  `data/roundtrip_sheet.py`) is the standing gate: worst case is Thin weights,
  whose ~20-unit stems wobble visibly against the grid but stay legible.
  Halving the grid to 8 units (192 coordinate chars, vocab 223) is the
  documented fallback and only changes the alphabet, not the format.
- Overlap removal is load-bearing, not cosmetic: found fonts — variable fonts
  especially — draw glyphs as overlapping contours (stem over bowl), and
  under even-odd fill every overlap renders as a hole (discovered on the
  first sheet: Teko grew stencil gaps). Removing overlaps makes contours
  disjoint, which is what licenses both the even-odd rule and normalizing
  winding direction away entirely.
- Points outside −512…1008 clip to the boundary (0.4% of lines in the frozen
  pool, logged in `encode-stats.json`) — accepted, monitored.

## Alternatives considered

- **Digit-based coordinates** (e.g. `M 128,0`): smaller alphabet, but the
  model must learn to compose numbers and can emit out-of-grid values —
  exactly the failure class the one-char-per-coordinate design eliminates.
- **A real token vocabulary** (verb+point merged tokens, or x/y pair tokens,
  vocab ≈ 9k): richer tokens, but breaks the `meta.pkl` char contract,
  requires engine/tokenizer work, and buys nothing at this corpus size.
- **Preserving winding direction as fill information** (nonzero rule, no
  direction normalization): keeps found fonts' inconsistent conventions as
  spurious variation the models would have to learn; overlap removal +
  even-odd removes the entire degree of freedom instead.
- **Cubic curves kept alongside quadratic** (`C` verb): doubles curve
  grammar for no representational gain the grid doesn't already erase;
  cu2qu error is far below one grid unit.
- **Per-dataset vocab via `set(data)`** (house default): silently breaks
  cross-arm BPC comparability — the one place this project must deviate
  from the daydream pattern.
