# daydream-chess-nanogpt-1: weight-space edit notes

**Verdict: no isolable failure found. final.pt is a byte-identical copy of base.pt (0 weights changed, 0% of the model).**

## The model and the task
Character-level UCI chess (`e2e4 e7e5 ...`, one game per line), 21-token vocab, 2.66M params. Each move is 5 characters: from-file, from-rank, to-file, to-rank, then a separator (space, a newline at game end, or a promotion letter).

## Diagnosis (evidence)
Probe loss for base is **0.8475** (first eighth 1.055, to half 0.830, second half 0.809). The top-loss targets are all file letters (d, e, c, f, g, b, h, a), each at 1.2 to 1.7 nats, followed by rank digits at 0.6 to 0.8 nats.

Logit lens on the final residual (`acts_2.npz`, 8 windows, 2040 targets), split by each character's role in the move:

| role | n | NLL | entropy |
|---|---|---|---|
| from-file (which piece moves) | 408 | 1.693 | 1.561 |
| from-rank | 406 | 0.712 | 0.675 |
| to-file (where it goes) | 402 | 1.065 | 1.072 |
| to-rank | 401 | 0.689 | 0.688 |
| separator | 400 | 0.115 | 0.167 |

- **The format is solved.** The probability mass put on the wrong character class (a digit where a file belongs, and so on) is 0.06 to 0.11% at every role. A space after a move gets p=0.976, and the observed rate in the dump is 391/400 = 0.977. The separator role's whole cost is 46 of 1761 nats (2.6%), and 36 of those come from the 8 game-ending newlines. Those sit at the base rate (p(newline)≈0.011), and when a game ends is close to unpredictable from the moves alone.
- **The model is calibrated.** Mean NLL is 0.863 against a mean entropy of 0.839. Confidence matches accuracy in every bucket (conf>0.8: 0.955 vs 0.943; >0.9: 0.974 vs 0.974; >0.95: 0.981 vs 0.983; >0.99: 0.996 vs 1.000). As a diagnostic I divided the logits on the dump by 0.9 and 1.1, and both came out worse (0.870 and 0.864 against 0.863), so a single logit-scale edit (ln_f gain) has nothing to recover. I chose no scale from this. It only rules the hypothesis out.
- **The loss is move choice, and the errors are diffuse.** About 95% of the nats fall on the four square characters, mostly on which piece moves. A sample (seed 0, temperature 0.8) shows board-state tracking failing within about 6 moves: after `c4d5` (the bishop takes on d5) the model plays `d5e4` for Black. Later it shows a rare format slip (`d5d4g1`). Board state is spread across the whole network, the paper's "diffuse errors" case, and no single direction or layer produces it.
- **The weights look healthy.** There are no dead MLP neurons: the smallest c_proj column norm is above 0.02 in every layer. The residual stream grows sharply from block 3 on (rms 0.64 → 11.5 → 56.5, peak coordinate 407), and block 5's c_fc has one large singular value (18.6 against 2.5 for the next). That is the usual massive-activation pattern. The mean direction carries only about 20% of the energy, and the logit lens improves at every layer (17.4 → 8.2 → 2.75 → 1.35 → 1.03 → 0.93 → 0.86), so no layer overshoots or does harm.

I found nothing to subtract or rescale with a principled reason behind it. Spending passes to sweep knobs (ln_f scale, head ablations) would be the blind search the rules forbid, and any gain it found on 64 probe windows would likely not hold on held-out data.

## Edits
None. `final.pt` = `base.pt` (checked byte-identical with `cmp`).

## Pass log (3 of 50 used)
1. `loss base` → 0.84753 (positions 1.0549 / 0.8295 / 0.8092; worst targets d, e, c, f, g, b, h, a)
2. `acts base` → acts_2.npz (the logit-lens analysis above: `analyze_acts.py`, `lens.py`)
3. `sample base "\n"` → an illegal move by ply 11 (`d5e4` from a square White's bishop holds); a format slip `d5d4g1` later on. Saved in `sample_base.json`.
