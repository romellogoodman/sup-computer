# glyph-nanogpt-1: weight-space edit notes

## Diagnosis

**There is no isolable failure here. The loss is diffuse and mostly the data's own entropy.** One small, systematic miscalibration turned up, and it is the only thing I edited.

### Weights (no passes)
- Almost every matrix sits close to its init norm: c_fc has Frobenius norm about 23, and N(0, 0.02) at 2304x576 gives 23.0. The RMSNorm gains are all between 0.98 and 1.05. This model is undertrained (3,000 steps at lr 1e-4).
- The one strong learned structure is a rank-1 mode in `h.11.mlp`. In c_fc, s0 is 19.4 against s1 of 3.6. In c_proj, s0 is 9.9 against s1 of 2.7. The two modes share the same neurons (overlap -0.98), spread across about 220 neurons (participation ratio).
- That mode reads the Q/L embedding direction and writes +Q/L/Z, -low coordinates. It is the verb-vs-coordinate grammar gate. It works and is not a bug.

### Grammar (from the acts dump: 8 windows, logits from resid_12 via ln_f and lm_head)
I parsed each position into the grammar state that predicts the next token and measured probability mass on illegal token classes:

| state | n | mean CE | illegal mass |
|---|---|---|---|
| after `\n` (letter) | 40 | 3.26 (≈ ln 26, letters are shuffled) | 0.006 |
| after letter (advance width) | 40 | 3.31 | 0.001 |
| after advance (forced `M`) | 40 | 0.0002 | 0.0002 |
| coordinate | 2765 | 1.141 | 0.0003 |
| segment end (L/Q/Z) | 865 | 0.465 | 0.010 |
| after Z (M or `\n`) | 43 | 0.266 | 0.0002 |

Grammar leakage costs about 0.003 nats per token in total. Coordinates carry 83% of the nats. The "worst tokens" list from the loss probe is flat across coordinate buckets. That is diffuse, inherent uncertainty, not a circuit failure.

### Calibration (the one systematic signal)
Coordinate positions are **overconfident** on the held-out families: CE 1.141 against predictive entropy 0.967, and accuracy 0.577 against mean max-prob 0.627. The pattern is consistent across confidence bins, 3 to 7 points too confident in every bin below 0.99. Segment-end positions lean slightly the other way (CE 0.465 against H 0.541). Coordinates dominate, so the overall gap is CE 1.010 against H 0.895. Per window it is mixed: 6 of 8 windows are overconfident and 2 are slightly underconfident.

## Edit
- **Tensor:** `transformer.ln_f.weight` divided by 1.1, which is a softmax temperature of 1.1 on the output logits. lm_head and the embedding are untouched, so the tie stays clean. Only the output temperature changes.
- **Size:** 576 weights changed out of 47,863,296 (0.0012%).
- **Reasoning:** a uniform temperature is the minimal correction for the systematic overconfidence measured above. I picked T=1.1 in advance as the hypothesis, then tested T=1.2 only to bracket it. That is two principled values, not a sweep.
- **Not edited:** the h.11 grammar gate, because it is not failing. A coordinate-only temperature would need the tied embedding rescaled, a risky change for a gain of at most a few thousandths. The after-Z and advance-width overconfidence covers about 2% of tokens, so it is not worth an edit.

## Pass log (4 of 50 used)
| # | op | candidate | result |
|---|---|---|---|
| 1 | loss | base | 0.95607 (first eighth 1.1454 / to half 0.9084 / second half 0.9445) |
| 2 | acts | base | acts_2.npz, used for the grammar and calibration analysis |
| 3 | loss | cands/temp1.1.pt | **0.95268** (-0.00339) |
| 4 | loss | cands/temp1.2.pt | 0.95866 (+0.00259, overshoots) |

A parabola through the three points puts the probe optimum at T ≈ 1.09, so 1.1 is essentially there. I did not chase it further.

`final.pt` = `cands/temp1.1.pt`.

## Held-out read
The probe gain is about 0.0034 nats (0.35%). The test split is the same family-held-out distribution, and the gain comes from a systematic miscalibration, not from fitting probe content. I expect the sign to hold, with roughly 0.002 to 0.004 nats of gain. It is real but tiny. The honest headline is that the model has no isolable failure for a weight edit to fix: its errors are diffuse, which is the regime where the paper says edits fail.
