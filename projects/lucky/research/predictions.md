# Predictions, registered before the first training run

Written and committed before any model in this project was trained. The git
history is the notary: this file's commit precedes the first run log.

The pre-check on the draws themselves (`precheck.py` → `precheck.json`) is also
run and committed before the first run.

## The floors, known in advance

| Game | Outcomes | Floor |
|---|---|---|
| Pick 3 | 1,000 | log₂ 1,000 = 9.966 bits/draw |
| Powerball (5 of 69, 1 of 26) | 292,201,338 | log₂ 292,201,338 = 28.122 bits/draw |

Held-out bits/draw counts every token of the draw, including the separator
and the newline, which a trained model predicts for free. Powerball is scored
at set level: the model's probability summed over the 120 orderings of the
five whites.

## What is predicted

1. **Both models land on the floor.** Each early-stopped model's held-out
   bits/draw sits within 1% of its floor: 9.966 ± 0.100 for Lucky, 28.122 ±
   0.281 for Lucky Power. The band is this file's operational reading of
   "lands on the floor"; it was fixed here, before the runs. A model cannot
   sit below the floor except by test-split noise.
2. **A − B ≈ 0.** For both games, the no-history control (A) and the history
   version (B) finish at the same held-out loss: the 95% interval of the
   paired per-draw gap contains zero.
3. **Lucky Power drifts above the floor with continued training.** About
   1,400 draws is few enough to memorize, so its held-out loss at the last
   step is higher than at the early-stopped step, and the curve that lands
   and stays is the one up to the stopping step.

Expected curve shapes: Lucky drops within the first evals (it only has to
learn that a draw is three digits and a newline) and is flat after. Lucky
Power falls further while it learns the ranges and the no-repeat rule, then
flattens, then drifts.

No number is predicted for the valid-ticket rate or the memorization check.
They are measured and reported.

## What would count as a failure

- A model more than 1% above its floor at its stopping step: it did not learn
  the format.
- An A − B interval that excludes zero. If B wins, the first suspects are a
  leak across the split or an unfair era in the pre-check, in that order,
  before anything is said about the lottery.
- Lucky Power's held-out loss flat or falling through the last step: the
  memorization prediction was wrong.
