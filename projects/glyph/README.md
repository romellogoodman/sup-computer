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

# 5. train an arm (configs in config/: specialist, omni_s, omni_xl)
uv run python core/nanogpt_core/train.py projects/glyph/config/omni_xl.py \
    --out_dir=projects/glyph/runs/omni-xl-r1

# 6. measure what the loss can't (parse / unterminated / memorization + sheet)
uv run python projects/glyph/harness.py projects/glyph/runs/omni-xl-r1 \
    --letters abc --num 64 --temp 1.0

# 7. after all 28 runs: the full arms-comparison table -> research/matrix-results.json
uv run python projects/glyph/matrix_eval.py
```

`specimen.py` renders encoded glyph lines into the report-ready PNG grids
(specimens are artifacts, not charts — charts go through `tools/dataviz`).

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

Released: [`glyph-nanogpt-1`](models/glyph-nanogpt-1/) (2026-07-14) — the
omni-xl generalist, chosen on purpose over the winning case. The full 28-run
matrix ran both arms: the generalist wins mean BPC (1.490 vs 1.521) but draws
valid glyphs 71.0% vs the case's 92.1% at temp 1.0, so the unreleased
26-specialist case stands as the frozen yardstick the next version has to
overtake. Version history in [`MODELS.md`](MODELS.md); run-by-run record in
[`research/log.md`](research/log.md) and [`leaderboard.md`](leaderboard.md).
