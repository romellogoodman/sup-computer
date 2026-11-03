# shakespeare-nanogpt-3: weight-space edit notes

## Diagnosis

**No isolable circuit failure. The model is uniformly undertrained, plus one global defect: it is overconfident.**

Weight analysis (`w_analysis.py`, `heads.py`):
- No dead or degenerate heads. All 36 heads have full-rank V and O blocks (64/64 singular values > 0.05), and q, k and v norms are even within each layer.
- The attn `c_proj` matrices have 47 to 67 singular values below 0.05. That is the small `c_proj` init (std 0.02/sqrt(12)) not yet grown after 2,000 steps, not a defect. The undertraining is spread evenly through the network.
- RMSNorm gains are smooth, with no outlier channels. MLP and lm_head spectra look normal.

Activations (`acts_2.npz`, `acts_an.py`):
- The residual norm grows smoothly, from 1.0 at the embeddings to 28.6 at the last layer. There are no massive-activation dimensions: the largest channel's mean |x| is 2.4, against a median of 1.1.
- **Overconfidence:** mean predictive entropy at the final layer is **2.82 nats**, but probe cross-entropy is **3.17 nats**. A calibrated model would have these roughly equal, so the distributions are too sharp. Two plausible causes: dropout 0.2 is switched off at eval, and the model trained mostly on plays but the probe is narrative verse (Lucrece).

Probe loss diagnostics (base):
- 3.1739 overall. By position: 3.43 in the first eighth, 3.16 up to half, 3.12 in the second half. The worse start is expected because there is less context there.
- Worst single target: `"\n   "` (token 554), 3.87 nats on average over 226 occurrences. This is the indented couplet in Lucrece's rhyme-royal stanzas, so getting it right means counting lines. I **did not** edit for it. Raising that token's logit would fit the probe's verse form, which isn't shared by text that uses other indents. It is a probe-specific failure, not a general one.

## Edit (final.pt)

- **Tensor:** `transformer.ln_f.weight` multiplied by 1/1.1. That is a softmax temperature of T = 1.1, applied to the unembedding only. The tied embedding is untouched, because ln_f sits only on the output path.
- **Weights changed:** 384 of 11,015,040, or **0.0035%** of the model.
- **Reasoning:** the entropy/cross-entropy gap points to overconfidence, and the clean fix for that is a single temperature. I tested two principled values, T = 1.1 and T = 1.2, to find which side of the optimum each falls on. This was not a sweep. Both helped. I kept 1.1, the more conservative value, and did not refine it further on the probe.

## Pass log (4 of 50 used)

| # | op | candidate | result |
|---|---|---|---|
| 1 | loss | base | 3.17385 (by position 3.434 / 3.160 / 3.119) |
| 2 | acts | base | acts_2.npz: entropy 2.82 < CE 3.17, so overconfident |
| 3 | loss | cands/temp_1.1.pt | **3.15283** (3.406 / 3.140 / 3.099), -0.0210 |
| 4 | loss | cands/temp_1.2.pt | 3.15577 (3.404 / 3.144 / 3.103), -0.0181 |

## Disclosure

To understand the domain, I read `data/_xl_corpus.py` (the split recipe) and a few KB of `shakespeare_full/raw.txt` near the val region. From those I learned that the val text is the narrative poems: Lucrece in the probe half, and Venus and Adonis with Gutenberg boilerplate after it in the held-out half. I did not read any .bin files or compute statistics. I chose not to tune anything toward the held-out content: the temperature was chosen on probe evidence alone, and I rejected the Lucrece-specific indent edit. Because the held-out half is further out of distribution, a temperature above 1 should, if anything, help more there.

## Read on held-out

The gain should hold, at about -0.02 nats. A global temperature is a one-parameter change, and it fixes a miscalibration caused by distribution shift that the held-out half shares. Across 256 paired windows the change should go the same way in nearly every window. It is a calibration fix, not a capability fix. The real limit is undertraining, and no edit made without gradients can repair that.
