# pona-nanogpt-1: weight-space edit notes

**Verdict: no isolable failure found. final.pt is a byte-identical copy of base.pt.** Used 6 of 50 passes.

## Diagnosis
- **The model is badly undertrained, and its errors are diffuse.** It ran 1,500 iters. When I compare each matrix's singular values with the Marchenko-Pastur edge for its known init std (0.02, or 0.02/sqrt(12) for c_proj), most of the weights are still sitting at their random init:
  - attn V: 87–100% of the energy is in the random bulk (h.0 V has 0 singular values above the edge).
  - mlp c_fc: 70–93% bulk.
  - The median c_fc row norm is 0.294, against 0.277 at init.
  - The learned structure lives in q/k (about 16 spikes each, bulk around 40%), attn/mlp c_proj (19–51% bulk) and lm_head (13% bulk). In effect it is a random-features network, and the output-side matrices have adapted to random V and c_fc projections.
- **Calibration is fine.** On the acts dump (8 windows), mean entropy is 2.544 vs NLL 2.571, and top-1 confidence is 0.405 vs accuracy 0.390, both inside noise. Testing temperature in both directions confirmed it (below).
- **Grammar rules are learned.** After sentence-initial mi/sina, P(li) is 0.001–0.005 every time, and the right verbs/preverbs (wile, ken, pilin) rank top-3.
- **No looping or degeneration.** A 300-token sample at t=0.8 is fluent, varied prose plus chat turns.
- **Loss spreads over the grammar words** (`.`, lon, li, jan, pi, ni, ona, mi, tawa). No single token or position dominates. Predicted mass vs counts per token matches within sampling noise. first_eighth runs higher (2.695) only because there is no context at a window's start.

## Edits tested (none kept)
| cand | tensors | weights changed | share | reasoning | probe loss |
|---|---|---|---|---|---|
| base | – | 0 | 0% | – | **2.47237** |
| temp097 | ln_f.weight ×0.97 | 192 | 0.007% | tests the slight overconfidence seen in the acts dump | 2.47470 (+0.0023) |
| temp103 | ln_f.weight ×1.03 | 192 | 0.007% | tests the opposite hypothesis: dropout 0.1 is removed at eval, so maybe it's underconfident | 2.47277 (+0.0004) |
| cproj_denoise | all 12 attn+mlp c_proj: hard-threshold SVD at 1.05× the MP edge (LASER-style) | 1,105,920 | 40.5% | removes the init-noise bulk that writes into the residual | 2.54743 (+0.075) |

I chose the temperature values a priori (±3%), not by sweeping. Both directions got worse, so the model is calibrated near T=1. Removing the bulk hurt badly, which shows the random-init components carry load: downstream weights co-adapted to them. That fits the paper's caveat that edits fail when errors are diffuse. More capacity here has to come from training, not surgery.

## Pass log
1. loss base → 2.47237
2. acts base → acts_2.npz
3. loss cands/temp097.pt → 2.47470
4. loss cands/cproj_denoise.pt → 2.54743
5. loss cands/temp103.pt → 2.47277
6. sample base → fluent, no loops
