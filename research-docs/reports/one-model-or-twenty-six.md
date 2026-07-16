---
type: experiment
number: 9
produced: "→ glyph-nanogpt-1 (the 26-specialist case stays an unreleased yardstick)"
title: "One model or twenty-six?"
date: 2026-07-14T09:56:28-04:00
series: glyph
researcher: claude-fable-5
models: [glyph-nanogpt-1]
summary: "Twenty-six 1.8M-param GPTs, one per lowercase letter, against one letter-conditioned generalist at two sizes — all trained on 82k glyph outlines from 759 open-licensed sans-serifs. The 47.8M generalist wins mean bits-per-char by 2% but fails to draw a well-formed glyph 29% of the time where the specialists fail 8% — and it ships anyway, on purpose: the studio releases one evolving instrument, with the case's numbers frozen as the yardstick every future version has to overtake."
takeaways:
  - >-
    At **parameter parity** the question isn't close: a 1.8M generalist
    conditioned on letter identity loses to the letter's own 1.8M specialist
    on every one of 26 letters (mean BPC 1.558 vs 1.521).
  - >-
    Give the generalist the **sum of the case's budget** (47.8M ≈ 26 × 1.8M)
    and the loss flips: omni-xl takes 16 of 26 letters and the mean (1.490)
    — but its biggest wins sit exactly where the case's uniform training
    recipe over-trained the short, simple letters.
  - >-
    The loss and the drawing **disagree**: sampled at temperature 1.0, the
    case produces a grammar-valid glyph 92.1% of the time, omni-xl 71.0% —
    and its survivors look worse than the gap sounds. Best model by loss,
    least reliable draughtsman.
  - >-
    The 47.8M model also **couldn't train on the shared recipe** — three
    runs diverged at lr 3e-4 / beta2 0.99 before the standard big-model
    adjustment (1e-4 / 0.95) held. The one-big-model shape carried its own
    operational tax.
  - >-
    The release **inverts the scoreboard on purpose**: the generalist ships
    as glyph-nanogpt-1 — one evolving instrument over a menu of twenty-six —
    and the case stays unreleased, its numbers frozen as the yardstick v2
    has to overtake.
status: published
---
[← all experiments](README.md) · **Experiment 09** · Runs a-r1 … z-r1, omni-s-r1, omni-xl-r1 · `→ glyph-nanogpt-1` · July 2026

# One model or twenty-six?

Give a fixed parameter budget two shapes: one 47.8M-parameter model that
draws every lowercase letter, or twenty-six 1.8M specialists that each draw
exactly one. The big model wins the loss table by 2% — and fails to finish
a letter 29% of the time, against 8% for the specialists.

The corpus is type history flattened to text: 759 OFL-licensed sans-serif
families from Google Fonts, every upright weight, each glyph outline
serialized as one line where one printable character is one token — drawing
verbs `M L Q Z`, coordinates from a 96-character alphabet on a 16-unit grid,
the em normalized to 1024 ([ADR-0027](../../docs/adr/0027-glyph-one-char-per-token-outline-codec.md)).
81,934 glyphs, deduped to a fixed family split so every model — specialist or
generalist — is scored on font families none of them ever saw. A specialist
compresses the distribution of one letter across hundreds of disagreeing
hands. Sampling it pulls out a new individual every time.

This is what the case draws. One sample per letter, its own specialist each,
no cherry-picking — the near-misses (that `g`, that `k`) ride along:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/exp11-specimen-case.dark.png">
  <img alt="Two rows of 13 generated glyphs, a through z, one from each specialist. Most letters are cleanly legible sans-serif forms in varied weights; g is a blobby near-miss, k half-collapses, n folds its left stem." src="assets/exp11-specimen-case.light.png">
</picture>

## At parameter parity, splitting wins everywhere

The first arm answers the cleanest version of the question: same 1.8M
parameters, same recipe, same tokens — split into 26 instruments or shared
by one conditioned model? The specialists win the mean, and omni-s does not
take a single letter outright. Twenty-six times more data through the same
capacity bought nothing; the pilot's 3-letter generalist (val loss 1.014)
and the full 26-letter one (1.012) landed within noise of each other, so
capacity, not transfer, was the binding constraint all along.

The chart puts the three arms side by side. Look at the middle bar: omni-s
loses to the case it was supposed to consolidate.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/exp11-mean-bpc-by-arm.dark.png">
  <img alt="Bar chart of mean held-out BPC: the case 1.521, omni-s 1.558, omni-xl 1.490. The unigram floor is around 5.2." src="assets/exp11-mean-bpc-by-arm.light.png">
</picture>

## Give the generalist the whole budget and the loss flips

omni-xl — 12 layers, 576 embed, 47.8M parameters, the case's budget in one
body — takes the mean by 0.031 BPC and 16 of 26 letters. That is the honest
headline for the one-big-model position, and it deserves its chart.

But read where its wins live. Above the zero line, omni-xl's four biggest
margins are `l` (+0.268), `v` (+0.168), `n` (+0.131), and `h` (+0.117) —
short-sequence letters whose specialists overfit under the case's uniform
recipe (3,000 identical steps means a simple letter's tiny token corpus gets
epoched several times harder; `l`'s specialist hit train loss 0.14 against
val 1.82 before best-val checkpointing rescued its weights). Below the line,
the case's wins are the deep, distinctive letters: `o` by 0.094, `s`, `g`,
`a`, `e`. The generalist wins where the case hurt itself. The case wins
where the letters have the most to say.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/exp11-bpc-delta-by-letter.dark.png">
  <img alt="Diverging bar chart of per-letter BPC difference, specialist minus omni-xl. Sixteen letters sit above zero (generalist wins), peaking at l +0.27 and v +0.17; ten sit below (specialist wins), deepest at o -0.09." src="assets/exp11-bpc-delta-by-letter.light.png">
</picture>

## The best loss can't finish its letters

Loss is a promise; sampling is the product. Sixty-four samples per letter
per arm at temperature 1.0, run through the codec's strict decoder: the case
parses 92.1%, omni-s 94.2%, omni-xl 71.0%. The gap is not close, and it is
not bleed — the letter token leads every sequence, so every failure is pure
grammar and termination: contours that never close, coordinate pairs cut
short, 64 omni-xl samples that ran past the length budget without ever
emitting a glyph boundary. Its worst letters are `j` (51.6% valid) and `g`
(59.4%).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/exp11-parse-rate-by-arm.dark.png">
  <img alt="Bar chart of grammar-valid sample rates: the case 92.1%, omni-s 94.2%, omni-xl 71.0%." src="assets/exp11-parse-rate-by-arm.light.png">
</picture>

And the parse rate flatters it. Here is the same alphabet drawn by omni-xl —
its survivors are wilder, blobbier, further from letterform than the case's:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/exp11-specimen-omni-xl.dark.png">
  <img alt="Two rows of 13 glyphs a through z sampled from omni-xl. More letters are distorted or fragmentary than in the case's specimen; several are barely recognizable." src="assets/exp11-specimen-omni-xl.light.png">
</picture>

Thirteen consecutive `g` attempts from each arm make the texture difference
plain — the specialist's failures are degraded g's; the generalist's are
often not letters at all:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/exp11-failure-gallery.dark.png">
  <img alt="Three rows of thirteen samples with failures marked by an x. Specialist g: nine recognizable g's, four failures. omni-xl g: five failures and mostly abstract fragments among the valid samples. omni-xl j: a mix of clean j's, fragments, and three failures." src="assets/exp11-failure-gallery.light.png">
</picture>

One reading: at this corpus size the big model has capacity to spare for
distributional detail, which buys likelihood, while the small models are
forced into grammatical discipline, which buys legibility. Another: the
temperature was simply kind to sharp small models. The second reading is
partly right — a release-time sweep lifted omni-xl to 84.7% valid at temp
0.8 (the benchmark table stays at 1.0 for both arms, and the case was
never swept, so 92.1% is not its ceiling either). The sweep also found
`j` inverting the curve: best at temp 1.0, collapsing into repetition
loops below it. One global knob does not fit twenty-six letters. The case
never needed a knob.

## Be honest: what still doesn't work

- **The case over-trained its simplest letters, and that is the case's own
  flaw.** Per-letter token corpora vary several-fold with glyph complexity;
  a uniform 3,000 steps over-epoched the short letters into overfit (`l`:
  train 0.14, val 1.82). Best-val checkpointing contained the damage but
  didn't erase it — omni-xl's 16 BPC wins are concentrated exactly there.
  Twenty-six instruments need twenty-six tuning decisions; pretending
  otherwise cost the case the loss table.
- **The capacity comparison bent one control.** The shared optimizer recipe
  (lr 3e-4, beta2 0.99) diverged three times at 47.8M — healthy to ~step
  600, then the loss exploded, grad-clip active throughout — before the
  standard adjustment (1e-4, 0.95, longer warmup) held. So the arms did not
  train identically. One reading: an even better-tuned xl leaves more BPC on
  the table. Another: needing a bespoke recipe at all is a real cost of the
  one-big-model shape, and it nearly cost the run.
- **One seed per model.** The coin-flip letters — `m` (+0.004), `b`
  (−0.005), `w` (−0.008) — are within plausible seed noise, and no variance
  estimate exists this round. The 10-vs-16 letter split should be read as
  roughly-even, not exact.
- **Valid ≠ legible.** The parse rate is a grammar check, not a shape
  metric; omni-xl's grammar-valid `g`s are visibly less g-like than the
  specialist's, and nothing in this round quantifies that visual gap beyond
  the specimens above.
- **The grid is lossy at the extremes.** Thin weights (~20-unit stems on a
  16-unit grid) survive with visible stem wobble — an accepted cost of
  keeping the ensemble rather than any single designer's optical
  corrections, documented in the codec ADR.

## The release: the one, chasing the twenty-six

The bake-off has a winner, and the release is not it. On the craft that a
released glyph model exists for — finishing letters — the case won,
clearly: 92% valid draws to 71%, with the visual gap wider than those
numbers. This report does not soften that, and neither does
[the model card](../model-cards/glyph-nanogpt-1.md), which carries the
yardstick table uncushioned.

The studio ships the generalist anyway. `glyph-nanogpt-1` is omni-xl, and
the choice is aesthetic and deliberate: one evolving instrument over a
menu of twenty-six, a version series with a plot. The case's numbers are
now frozen — 92.1% valid, 1.521 mean BPC, letter by letter in the
[leaderboard](../../projects/glyph/leaderboard.md) — as the standing
yardstick, and every future version of glyph-nanogpt trains against it.
The gap to close is stated in
[`MODELS.md`](../../projects/glyph/MODELS.md) so no future round can dodge
it: reach the case's 92.1% valid-glyph rate without giving back the BPC
lead. The first lever was pulled at release — a three-point temperature
sweep put the shipped default at 0.8, where the model draws 84.7% valid
instead of 71.0% — and the rest are named: a stable recipe from step zero
instead of a mid-run rescue, per-letter sampling settings (`j` alone
prefers temp 1.0), seeds, and data.

What the finding means: parameter count consolidates likelihood, not
craft. Sliced against data this small, one big model learns the
distribution's texture and loses the discipline of the line; twenty-six
small hands each learn one letter well enough to finish it. The release
makes that trade explicit instead of hiding it behind a winner's table —
version 1 ships knowing exactly what it owes. Worth the rounds it will
take.

## Reproduce it

```bash
uv run python projects/glyph/data/fetch_fonts.py      # freeze the pool (manifest pins the commit)
uv run python projects/glyph/data/encode_corpus.py    # 82k glyphs -> one-char-per-token lines
uv run python projects/glyph/data/roundtrip_sheet.py  # the legibility gate — look at it
uv run python projects/glyph/data/prepare.py          # per-letter + omni datasets, splits, baselines

for ds in a b c d e f g h i j k l m n o p q r s t u v w x y z; do
  uv run python core/nanogpt_core/train.py projects/glyph/config/specialist.py \
    --dataset=$ds --out_dir=projects/glyph/runs/$ds-r1
done
uv run python core/nanogpt_core/train.py projects/glyph/config/omni_s.py
uv run python core/nanogpt_core/train.py projects/glyph/config/omni_xl.py

uv run python projects/glyph/matrix_eval.py           # 78 BPC evals + harness -> matrix-results.json
```

## Credits

Corpus design, codec, training, evaluation, and this write-up: Claude Fable 5
(Claude Code). Direction, scope calls, and the singular-release policy:
Romello Goodman. Fonts: 759 OFL families via
[google/fonts](https://github.com/google/fonts), credited individually in
`projects/glyph/data/manifest.json`. Prior art conversation: Eli Heuer's
[Virtua Grotesk](https://elih.net/blog/virtua-grotesk/), which trains one
model on one perfectly disciplined hand — this experiment inverts it.
