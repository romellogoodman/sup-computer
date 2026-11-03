# gatsby-nanogpt-3: weight-space edit notes

## Diagnosis: the model is overconfident everywhere, not broken in one place

**Weights look healthy.** Every embedding row has a norm between 0.88 and 1.76, so no dead or decayed token rows. No layer has a singular value far out of line. The residual stream grows smoothly, from a norm of 11 after block 0 to 52 after block 5. Dims 279, 280 and 28 carry a mean direction worth about a third of the norm, and that direction is aligned with lm_head's top singular vector (cos -0.77). It is the usual unigram-prior direction and does no harm. The base sample (temp 0.8) is fluent, with only one stutter ("a little a little"). There is no looping circuit or other isolable defect like the ones in the paper's examples.

**The top-loss tokens are spread thin.** The biggest totals come from common function words (".", " the", " a", " The", "\n", " and"), each at a modest mean loss. The high means on " s" (3.5) and " c" (2.9) are word-start BPE pieces for rare words, so that loss is inherent. None of this points to a single error.

**What I did find is miscalibration.** I took the residual stream after the last block from the `acts` dump (8 probe windows) and computed the model's own mean predictive entropy. This step uses no targets. The entropy is **1.046 nats**, while the measured probe cross-entropy is **1.269**. A calibrated model has E[H] ≈ E[CE], so this one is too sure of itself by about 0.22 nats. Two mechanisms predict this, and neither depends on which windows you look at:
1. **Dropout 0.2 train/eval mismatch.** With dropout on, the branch noise inflates the residual norm, and the final RMSNorm divides it back out. At eval the noise is gone, so the normalised signal and the logits come out larger. From the acts, counting one branch per block (a lower bound), the eval logits are about **1.055×** their train-time scale.
2. **About 25 epochs** (8,000 iters × 64 × 256 tokens over a corpus of roughly 5M tokens). Memorisation makes the model sharp on train text, and that sharpness does not carry over to unseen text.

## The edit
- **Tensor:** `transformer.ln_f.weight` multiplied by **0.9**. This is the same as a softmax temperature of 1.11 and changes nothing else.
- **Weights changed:** 384 of 11,015,040, which is **0.0035%** of the model.
- **Choosing the scale:** I tested two principled values, 0.9 and then 0.8 to bracket the minimum. I ran no sweep. The parabola through the 1.0, 0.9 and 0.8 points has its vertex at about 0.874. Entropy matching on the acts (E[H] = CE) independently puts the crossing at about 0.88: entropy is 1.213 at 0.9 against a loss of 1.252, and 1.440 at 0.8 against 1.257. I kept the tested value of 0.9 instead of fitting the vertex. The gap between the two is about 0.0007 nats.

## Results (probe split, 64 windows)
| cand | loss | first 1/8 | to half | second half |
|---|---|---|---|---|
| base | 1.26871 | 1.5437 | 1.2594 | 1.2070 |
| ln_f × 0.9 (final) | **1.25240** (−0.0163) | 1.5306 | 1.2433 | 1.1896 |
| ln_f × 0.8 | 1.25749 (−0.0112) | 1.5415 | 1.2486 | 1.1932 |

The gain shows up in every position bucket. A sample from the final model is fluent and keeps the control-line format; it even closes one story and starts the next with a well-formed header.

## Will it hold on held-out data?
Very likely, at around −0.015 nats. Both causes are systematic and the edit has one degree of freedom, so there is almost nothing in it to overfit to the probe windows. The scale was picked from 2 probe points on a smooth convex curve, and the entropy check confirms it without using the probe targets. The caveat is that this is calibration and nothing more: the model's ranking of tokens is unchanged, so argmax and greedy outputs are identical. Its errors are spread across the vocabulary, so I found no circuit-level failure to fix.

## Pass log (6 of 50 used)
1. loss base → 1.26871
2. sample base → fluent, with one "a little a little" stutter
3. acts base → acts_3.npz (residual stats, entropy 1.046 vs CE 1.269)
4. loss cands/lnf_0.9.pt → 1.25240
5. loss cands/lnf_0.8.pt → 1.25749 (brackets the minimum)
6. sample final.pt → fluent, format intact

Analysis scripts: an1.py (weight spectra and norms), an2.py (residual stats), an3.py (predictive entropy from acts, no targets), an4.py (dropout norm-ratio estimate), mk_temp.py (builds the candidates).
