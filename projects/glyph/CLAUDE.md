# CLAUDE.md — conventions for agents working in glyph

`glyph` trains small GPTs on lowercase glyph outlines from OFL sans-serif
fonts. The project IS a comparison: 26 per-letter specialists vs a
letter-conditioned generalist (two sizes). Start with [`README.md`](README.md).

## The core idea (don't relitigate these)

- **The comparison is the finding; the release is singular.** (Decided by
  Romello 2026-07-13, supersedes the earlier "both arms ship" lock.) The
  report documents both arms with numbers AND actual rendered glyphs from
  every stage — pilot and matrix, successes and failures — and the whole
  experiment stays recreatable from the repo. But sup computer releases ONE
  glyph-nanogpt: either the case of 26 specialists or one generalist,
  decided by the matrix results. The losing arm is never a released model —
  it survives as evidence.
- **One codec, one alphabet, every arm.** The serialization is identical for
  all models — the letter-identity char leads every line and is simply
  constant for a specialist. The 127-char vocab is fixed and explicit
  (defined in `data/codec.py`, NOT derived via `set(data)`), so all arms
  share one `meta.pkl` shape and score the same test files identically.
  Never let a dataset grow its own vocab.
- **Char-level, on the shared `core`.** One printable character = one token;
  coordinates never decompose into digits. This is the same `meta.pkl`
  contract as daydream/shakespeare (ADR-0012) — **do not fork or vendor an
  engine**, and do not add a "real" tokenizer. The codec's design rationale
  is ADR-0027.
- **Lowercase a–z only, sans-serif only, upright only, OFL only.** 'a' and
  'A' are different models — uppercase is a future round, not scope creep.
  Italics are excluded because the italic flag flips shape class (many
  italic a's go single-story). Provenance lives in `data/manifest.json`;
  every font used must be traceable there.
- **Splits are by font family, never by glyph.** One family-hash assignment
  (80/10/10 train/val/test) shared across every letter and every arm —
  val/test families are unseen everywhere or specialist-vs-omni BPC is not
  apples-to-apples.
- **Quality checks stay out of the loss metric.** BPC (via `core/eval`) is
  the headline number; parse/closure/render rates and the memorization check
  live in the project harness and are recorded, not folded into loss.

## Pipeline & conventions

- `data/fetch_fonts.py` → sparse-clones google/fonts (`ofl/` only), selects
  SANS_SERIF families, writes gitignored `data/gfonts/` + committed
  `data/manifest.json` pinned to an upstream commit sha.
- `data/codec.py` owns the alphabet and both directions (font → tokens,
  tokens → SVG path). `data/encode_corpus.py` runs it over the manifest into
  `data/corpus/<letter>.txt`. `data/roundtrip_sheet.py` renders the
  original-vs-roundtrip legibility sheet — regenerate and *look at it* after
  any codec change.
- `data/prepare.py` → dedup, family split, per-letter datasets
  `data/<letter>/{train,val}.bin` + `data/omni/`, committed
  `test/<letter>.txt`, unigram baselines in `research/baselines.json`.
- Train/sample/eval through `core/` from the **repo root** via `uv run`,
  configs in `config/`, runs in `runs/` (gitignored).
- **Document as you go**: `research/log.md` per run, `leaderboard.md` once
  training starts. Credit the researcher — root rule, ADR-0013.

## Releases

Each model releases as its own frozen snapshot under
`models/glyph-nanogpt-<x>-N/`, pinned to a git tag, per
[`docs/releasing.md`](../../docs/releasing.md). Frozen folders are never
refactored to share `core/` or each other.
