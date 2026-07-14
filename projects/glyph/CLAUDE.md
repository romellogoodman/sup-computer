# CLAUDE.md — rules for agents working in glyph

Facts live in [`README.md`](README.md) — the experiment, codec, pipeline,
version index (§ Versions), and scoreboard (§ Leaderboard). This file is only
the rules (ADR-0030).

## Don't relitigate

- **The comparison is the finding; the release is singular.** (Decided by
  Romello 2026-07-13.) The studio releases ONE glyph-nanogpt per round; the
  losing arm is never a released model — it survives as evidence and the
  yardstick.
- **One codec, one alphabet, every arm.** The 127-char vocab is fixed and
  explicit (`data/codec.py`, NOT derived via `set(data)`), so all arms share
  one `meta.pkl` shape and score the same test files identically. Never let a
  dataset grow its own vocab.
- **Char-level, on the shared `core`** — one printable character = one token;
  coordinates never decompose into digits (`meta.pkl` contract, ADR-0012;
  codec rationale, ADR-0027). **Do not fork or vendor an engine**, and do not
  add a "real" tokenizer.
- **Lowercase a–z only, sans-serif only, upright only, OFL only.** Uppercase
  is a future round, not scope creep; italics flip shape class. Every font
  used must be traceable in `data/manifest.json`.
- **Splits are by font family, never by glyph** — one family-hash assignment
  shared across every letter and arm, or specialist-vs-omni BPC is not
  apples-to-apples.
- **Quality checks stay out of the loss metric.** BPC is the headline;
  parse/closure/render rates and the memorization check live in the harness
  and are recorded, not folded into loss.

## Conventions

- `data/codec.py` owns the alphabet and both directions; after any codec
  change, regenerate the round-trip sheet and *look at it*.
- Train/sample/eval through `core/` from the **repo root** via `uv run`;
  configs in `config/`, runs in `runs/` (gitignored).
- **Document as you go**: `research/log.md` per run and the README's
  Leaderboard section, committed with the run.
- **Releases** are frozen snapshots under `models/`, per
  [`docs/handbook.md`](../../docs/handbook.md#releasing-a-version).
- **Credit the researcher** — root [`CLAUDE.md`](../../CLAUDE.md), ADR-0013.
