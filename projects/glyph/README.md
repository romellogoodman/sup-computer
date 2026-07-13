# glyph

Small GPTs that draw lowercase letters. The corpus is OpenType glyph outlines
from OFL-licensed sans-serif families on Google Fonts, serialized as text —
one printable character per token, one glyph per line. The experiment:
**26 per-letter specialists** (`glyph-nanogpt-a` … `glyph-nanogpt-z`,
"the case") against a **letter-conditioned generalist** in two sizes
(`glyph-nanogpt-omni-s`, param-matched to one specialist; `glyph-nanogpt-omni-xl`,
matched to the sum of all 26). What does splitting cost, and what does it buy?
The comparison is documented in full — but the studio releases **one**
glyph-nanogpt: the case or the generalist, decided by the results.

Where Virtua Grotesk (Eli Heuer) trains one model on one designer's perfectly
disciplined hand, this inverts it: each specialist compresses hundreds of
disagreeing hands drawing a single letter — the distribution of *a-ness*
across type history, sampled one new individual at a time.

## Pipeline

```bash
# 1. pull the OFL sans pool (sparse clone of google/fonts) + write the manifest
uv run python projects/glyph/data/fetch_fonts.py

# 2. encode every font in the manifest into one-glyph-per-line text
uv run python projects/glyph/data/encode_corpus.py

# 3. round-trip legibility sheet (the pre-training gate — look at it)
uv run python projects/glyph/data/roundtrip_sheet.py

# 4. dedup, split by family, tokenize per-letter + omni datasets
uv run python projects/glyph/data/prepare.py
```

Everything downstream of the manifest is deterministic and regenerates; font
binaries and `.bin`/`.pkl` datasets are gitignored (no-weights rule). What is
committed: `data/manifest.json` (provenance — family, license, files, hashes,
pinned upstream commit), `test/<letter>.txt` (held-out-family test sets), and
the run evidence in `research/`.

## The codec, in one paragraph

Each glyph is one line: the letter itself, an advance-width character, then
`M`/`L`/`Q`/`Z` drawing verbs whose coordinates are single characters from a
96-bucket alphabet (Braille block, U+2800…) — the em normalized to 1024,
coordinates quantized to a 16-unit grid spanning −512…1008, cubics converted
to quadratics. Vocab is a fixed, explicit 127 characters shared by every
dataset, so a specialist and the generalist score the same test file
identically. It rides `core/` unmodified via the char-level `meta.pkl`
contract (ADR-0012). Full rationale: ADR-0027.

## Status

Corpus and codec built; **no models trained yet.** Next: the a/e/g pilot
(both arms, specialist-sized), then the 26-overnight matrix. See
`research/log.md`.
