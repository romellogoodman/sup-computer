---
license: mit
language:
  - en
library_name: nanogpt
pipeline_tag: text-generation
tags:
  - glyph
  - nanogpt
  - char-level
  - gpt
  - fonts
  - vector-graphics
---

# Model Card — `glyph-nanogpt-1` (v1, the generalist)

The full experiment — one model or twenty-six, and why the studio released
the one — is
[experiment 09](../reports/one-model-or-twenty-six.md).

## What it is

A letter-conditioned generalist: prompt it with a newline plus a lowercase
letter and it continues with an advance-width character and `M`/`L`/`Q`/`Z`
drawing verbs whose coordinates are single characters on a 16-unit grid in a
1024-unit em. Every line is one glyph; the strict decoder in the frozen
folder's `codec.py` turns a line back into an SVG path. Trained from scratch
on outlines from 759 open-licensed sans-serif families (google/fonts,
commit-pinned manifest with per-file hashes), all upright weights, variable
fonts contributing one sample per named weight.

## Numbers that matter

| Metric | glyph-nanogpt-1 | the case (26 specialists, unreleased yardstick) |
|---|---|---|
| mean held-out BPC (26 letters) | **1.490** | 1.521 |
| letters won on BPC | 16 | 10 |
| grammar-valid samples, temp 1.0 | 71.0% | **92.1%** |
| worst letters (valid rate) | j 51.6%, g 59.4% | g 81% |
| exact-train memorization | 2/1,664 | 3/1,664 |
| params | 47.86M | 26 × 1.80M |

Held-out means held out by font *family* — the same 10% of families is
unseen by every arm, per letter. The unigram floor is ≈5.2 BPC.

## Sampling: use temperature 0.8

A three-point sweep (1,664 samples per point, all 26 letters) picked the
shipped default before release:

| temp | valid glyphs | never-terminated | memorized exact |
|---|---|---|---|
| 0.6 | 83.8% | 201 | 18/1,664 |
| **0.8** | **84.7%** | 151 | 8/1,664 |
| 1.0 | 71.0% | 64 | 2/1,664 |

At 0.8 the model's valid-glyph rate rises 13.7 points over the temp-1.0
number in the benchmark table, at negligible memorization cost — the first
step toward the yardstick, taken before v2 exists. The player runtime's
default is already 0.8, so the released demo runs at this setting. Two
honesty notes: the benchmark table above is measured at temp 1.0 for both
arms and stays that way (the case was never swept, so 92.1% is not its
ceiling either); and `j` inverts the curve — it parses best at temp 1.0
(51.6%) and collapses into unterminated repetition loops at lower
temperatures (40.6% at 0.8, 18.8% at 0.6). One global knob does not fit
all twenty-six letters, which is quiet evidence for the case's thesis.

## Training

12 layers, 8 heads, 576 embed, block 512, dropout 0.2, batch 32; 3,000
steps at lr 1e-4 (beta2 0.95, warmup 300) on an M4 Mac (MPS), ~2.2s/step.
Best-val checkpointing — the shipped weights are the run's lowest validation
loss, not its final step. The recipe deviation from the studio's small
models is deliberate and documented in the report: the shared recipe
diverged three times at this parameter count.

## Limitations

- **It finishes only ~71% of what it starts** at temp 1.0 — contours that
  never close or sequences that never emit a glyph boundary; worst on `j`
  and `g`. This is the number v2 exists to fix.
- **Valid ≠ beautiful.** Its grammar-valid glyphs are visibly rougher than
  the specialists' — see the specimen figures in experiment 09.
- One seed, one run; per-letter BPC differences under ~0.01 are unresolved.
- Lowercase sans-serif only, 16-unit grid — thin strokes wobble by design
  (the codec keeps the ensemble, not any one designer's optical corrections).

## Reproduce

The frozen folder (`projects/glyph/models/glyph-nanogpt-1/`) rebuilds
everything in place: `fetch_fonts.py → encode_corpus.py → prepare.py →
train.py config.py`, then `harness.py` for validity numbers and specimen
sheets. Weights ship via the artifact URLs in `registry.json`, never in the
tree.
