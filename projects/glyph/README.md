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
overtake. Version history in [Versions](#versions); run-by-run record in
[`research/log.md`](research/log.md) and the [Leaderboard](#leaderboard).

## Versions

One release per version, singular on purpose: the studio ships ONE
glyph-nanogpt per round (the generalist), with the 26-specialist case from
experiment 09 standing as the frozen, unreleased yardstick it is trying to
overtake. Version history:

| Version | Date | What it is | Yardstick gap at release |
|---|---|---|---|
| [`glyph-nanogpt-1`](models/glyph-nanogpt-1/) | 2026-07-14 | omni-xl — 47.8M letter-conditioned generalist, 12L/8H/576E, one-char-per-token outline codec (ADR-0027) | wins mean BPC (1.490 vs 1.521) but draws valid glyphs 71.0% vs the case's 92.1% at temp 1.0 |

The gap to close, stated so no future version can dodge it: **valid-glyph
rate at the case's 92.1%, without giving back the BPC lead.**

## Leaderboard

Held-out-family BPC per letter (lower is better), via `core/eval/eval.py`
against `test/<letter>.txt`. The unigram floor is the per-letter dumb
baseline every model must clearly beat (`research/baselines.json`).

### Pilot (2026-07-13, config `specialist_pilot.py`, 1.80M params each)

| letter | unigram floor | specialist | omni-aeg (param parity) |
|---|---|---|---|
| a | 4.955 | **1.397** | 1.488 |
| e | 4.944 | **1.386** | 1.464 |
| g | 5.170 | **1.471** | 1.557 |

Harness at temp 1.0 (64 samples/letter): parse 73–88%, memorized-exact 0/320.
Runs: `runs/pilot-{a,e,g,omni-aeg}-r1` (gitignored); sheets in
`research/samples/`.

### Matrix (2026-07-14, 26 specialists + omni-s + omni-xl, 3000 iters)

Bold = best BPC for that letter. Specialists win 10/26; omni-xl wins 16/26;
omni-s wins none. Mean BPC: case 1.5210 / omni-s 1.5580 /
omni-xl 1.4899. Mean parse rate at temp 1.0: case 92.1% /
omni-s 94.2% / omni-xl 71.0%. omni-xl required its own
optimizer recipe (lr 1e-4, beta2 0.95) after the shared one diverged 3x.
Full data: `research/matrix-results.json`.

| letter | specialist | omni-s | omni-xl | spec parse | xl parse |
|---|---|---|---|---|---|
| a | **1.3597** | 1.4666 | 1.3962 | 88% | 64% |
| b | **1.3626** | 1.4438 | 1.3679 | 88% | 77% |
| c | **1.2878** | 1.3634 | 1.3004 | 94% | 80% |
| d | 1.3669 | 1.3802 | **1.3156** | 97% | 67% |
| e | **1.3516** | 1.4283 | 1.3780 | 89% | 72% |
| f | **1.4228** | 1.5212 | 1.4532 | 91% | 75% |
| g | **1.4081** | 1.5253 | 1.4550 | 81% | 59% |
| h | 1.5217 | 1.4457 | **1.4043** | 97% | 77% |
| i | 1.3271 | 1.4039 | **1.3098** | 92% | 70% |
| j | 1.5381 | 1.6141 | **1.5104** | 89% | 52% |
| k | 1.8780 | 1.9172 | **1.8440** | 97% | 77% |
| l | 1.9696 | 1.7091 | **1.7021** | 92% | 77% |
| m | 1.3646 | 1.4608 | **1.3601** | 97% | 72% |
| n | 1.5081 | 1.4306 | **1.3771** | 89% | 66% |
| o | **0.9936** | 1.1610 | 1.0877 | 91% | 66% |
| p | 1.3823 | 1.4296 | **1.3688** | 89% | 66% |
| q | 1.3924 | 1.4083 | **1.3543** | 95% | 67% |
| r | 1.5625 | 1.6005 | **1.5306** | 92% | 72% |
| s | **1.2563** | 1.3972 | 1.3158 | 91% | 66% |
| t | 1.4569 | 1.4927 | **1.4197** | 95% | 78% |
| u | 1.4797 | 1.4566 | **1.3834** | 98% | 77% |
| v | 2.0098 | 1.8862 | **1.8420** | 95% | 80% |
| w | **1.8333** | 1.9421 | 1.8411 | 91% | 78% |
| x | **1.6316** | 1.7699 | 1.6662 | 97% | 78% |
| y | 2.0039 | 2.0032 | **1.9403** | 95% | 67% |
| z | 1.8764 | 1.8514 | **1.8125** | 86% | 70% |
