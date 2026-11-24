# Predictions and kill criteria

Registered before the first training run. The commit that adds this file
precedes every checkpoint.

The four predictions and the four kill criteria are Romello Goodman's, quoted
from the project's design brief of 2026-09-22. The settings under them are
the values the brief left open. Claude Fable 5.2 chose those, also before
training, and each one says why.

## The question

Is oblique a temperature?

An aphorism model at low temperature produces platitudes, at high
temperature produces noise, and somewhere between, a band of the sampler's
settings may produce lines a human reader rates as useful and strange at
once. If that band exists and is stable across seeds, oblique is a sampler
setting. If strangeness and usefulness never peak together, the answer is
no, and that is the finding.

## Predictions

**P1 — the register token takes.** The corpus-trained classifier labels
model samples by their own token at above 85% accuracy at temperature 1.0.
Below 70% and the model learned one register with noise.

**P2 — keepers peak in the middle.** For `[s]` samples, the keeper rate
(strange ≥ 4 *and* usable ≥ 4) peaks at an interior temperature, and the
peak is **at least twice** the keeper rate at both the lowest and the
highest setting. That peak is "oblique." The prediction is that it exists,
that it sits between 0.8 and 1.2, and that the second seed's peak lands
within 0.2 of the first.

Why not the product of the two means: if *strange* rises and *usable*
falls, their product almost always peaks somewhere in the middle, so the
prediction couldn't fail. The keeper rate can: if strange lines are never
also usable, it stays near zero at every temperature and the answer is no.

**P3 — fortunes are the floor.** At every temperature, `[f]` samples rate
lower on *strange* than `[s]` samples, and at low temperature they rate
*higher* on *usable*. If `[s]` never beats `[f]` on strangeness, the corpus
didn't contain the difference.

**P4 — memorization arrives before oblique.** The best-loss checkpoint has
an exact-match rate above 10% (kenosha did this); the checkpoint that wins
the dial is earlier. The report says which step and why. If the best-loss
checkpoint is also the dial winner, the corpus was bigger than it needed
to be.

## Kill criteria

1. **No cell under 10% exact memorization produces well-formed lines** —
   the corpus is too small for this model to generalize; double the corpus
   once, then stop.
2. **P1 fails** — the token didn't take. Try the gatsby loudness fix (token
   repeated three times); if it still fails, the two registers were not
   distinguishable in the corpus, which is a finding about the generators,
   and the report becomes "you can't tell a fortune from a strategy."
3. **P2 fails** — the keeper rate is flat, peaks at an end of the sweep,
   or never reaches twice its end values. Oblique is not a temperature.
   That is the honest negative and it publishes at full volume; the model
   can still release with the dial set wherever the keeper rate is highest,
   labeled as such.
4. **Deck leakage** — any line matching a published card after filtering
   means the generators reproduced it; the corpus is regenerated with that
   generator dropped.

## Settings fixed before training

The brief names the measurements and leaves these values open.

| Setting | Value | Why |
|---|---|---|
| Dial temperatures | 0.6, 0.8, 1.0, 1.2, 1.4 | P2 places the peak between 0.8 and 1.2 and needs an end on each side of that band to fail against. Steps of 0.2 match the tolerance P2 gives the second seed. |
| Soft-cap grid | off, 8, 4, 2 | daydream's grid. Off is the default the dial sheet is sampled at. |
| Lines per cell | 500 per register | The brief's number. |
| Training length | 12,000 steps, a checkpoint every 500 | About 70 passes over the 1.38M-character training split, well past where kenosha's validation loss turned. 24 checkpoints. |
| Seeds | 1337, then 1338 | core's default, and the next one. |
| Exact memorization | the sampled line is a training line, character for character | The brief's 10% bar is read on this number. |
| 8-gram overlap | share of a line's character 8-grams found in the training set | The model writes characters. Held-out corpus lines are scored the same way, because ordinary English shares most of its 8-grams. |
| Well-formed | a newline inside 120 characters, a terminal mark, 2–11 words, 8–80 characters, no token bracket, no garbled word | The corpus filter's band. A garble is a word 3 or more edits from every corpus word, kenosha's line between a near-miss and a garble. |
| Register classifier | logistic regression, one weight per word, trained on the training split | The brief's "trivial classifier". Its accuracy on held-out corpus lines is the ceiling P1 is read against. |
| P1 cell | temperature 1.0, soft-cap off, all 1,000 samples | The brief gives the temperature. Malformed samples count: a line the classifier can't place is a line the token didn't shape. |

## How the dial checkpoint is chosen

Fixed here so the choice can't follow the results.

A checkpoint is eligible when both hold in the five dial cells (the five
temperatures, soft-cap off):

- exact memorization is under 10% in every cell, for each register;
- mean well-formedness over the cells at temperature 1.0 and below is at
  least 90%.

Among eligible checkpoints the dial uses the one with the lowest validation
loss. The automatic harness runs on steps 500, 1,000, 2,000, 3,000, 4,000,
6,000, 8,000 and 12,000, plus the step with the lowest validation loss.

P4 is then a comparison of two steps. It holds if the lowest-loss checkpoint
is ineligible on memorization and the chosen one is earlier. It fails if
they are the same step.

If no checkpoint is eligible, kill criterion 1 applies.
