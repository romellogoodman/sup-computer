# CLAUDE.md — rules for agents working in pona

Facts live in [`README.md`](README.md) — the project, pipeline, corpus policy,
version index, and scoreboard. This file is only the rules (ADR-0030).

## Don't relitigate

- **The oracle is the arbiter, and it gets verified live.** telo misikeke
  (vendored, MIT) decides grammaticality; before trusting any new checker
  version, run `oracle/verify_oracle.py` against the known-good/known-bad
  set. Never report a grammaticality number from an unverified oracle.
- **The Discord corpus stays out.** The 6.39M-token `ma pona pi toki pona`
  scrape is excluded on consent and register-drift grounds (see README
  § Corpus). Don't add it, whatever the size temptation.
- **Every LLM-generated line goes through `tools/synthgen`** (ADR-0014) and
  then through the oracle filter before it can enter a corpus. No hand-rolled
  LM Studio clients, no unfiltered synthetic text.
- **Two arms, two tokenizers, never shared.** The char arm and word arm each
  own their vocab (`data/tokenized-char/`, `data/tokenized-word/`). The word
  arm's detokenizer lives in `data/pona_tok.py` — sampling a word-arm
  checkpoint goes through `harness.py` (or `pona_tok.detok`), never through
  `core/nanogpt_core/sample.py`'s raw join.
- **Report corpus-relative grammaticality next to raw.** The corpus's own
  oracle pass rate is the ceiling reference (README § Corpus baseline); a raw
  model number without it is a category error.
- **No digits in the corpus or vocab.** Toki Pona numbers are words; lines
  containing ASCII digits are dropped at build time, deliberately.

## Conventions

- Run everything from the **repo root** via `uv run`; node for the oracle.
- Corpus/tokenized/vendor dirs are gitignored and regenerate from the
  committed scripts; the audit JSONs (`data/*_audit.json`, `research/*.json`)
  are committed evidence.
- **Document as you go**: `research/log.md` (why) and README § Leaderboard
  (numbers), committed with the run.
- Training runs follow the `babysit-training` skill; matrices run sequential
  on MPS.
- **Credit the researcher** — root [`CLAUDE.md`](../../CLAUDE.md), ADR-0013.
