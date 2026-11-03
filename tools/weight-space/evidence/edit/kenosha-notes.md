# kenosha-kid-nanogpt-2: weight-space edit notes

## Diagnosis: no isolable failure, just a small overconfidence from dropout

The corpus comes from a known stochastic generator (`generate.py`, read as code only). Its separators, terminal punctuation, word order, capitalization (Kenosha/Kid are capitalized with p=0.75) and the per-letter drift channel (rate 0.06) are all random draws. So most of the loss is entropy built into the corpus, not error.

Evidence:
- Base probe loss is **0.63338**. By position it is 0.762, then 0.654, then 0.586. Early positions cost more because a window starts mid-line with little context, which is expected.
- The top-loss targets match the generator's probabilities. `,` averages 2.18 nats against an ideal -ln(0.12)=2.12 for the ", " separator. `k` averages 2.39 against -ln(0.25)=1.39 for lowercase kid/kenosha, plus rare drift substitutions. `?`, `.` and `K` follow the same pattern. Nothing looks like a localized, wrong behaviour.
- From the acts dump (8 windows, base model, final residual → ln_f → lm_head, **no targets used**), mean predictive entropy is **0.583**, against a probe CE of 0.633. A calibrated model has E[H] ≈ E[CE], so the model is slightly overconfident. That fits the training setup: dropout was 0.2 in training and the model is evaluated without dropout, so the logits come out sharper.
- Drift floor: when a letter is the expected next character, the 20 least likely lowercase letters together get about 0.0046 of the mass. The generator implies about 0.008–0.01 (0.06 × ¼ substitution, spread uniformly over 26 letters, in the ~82% of lines that are tail lines). That is about 2× too little. Fixing it fully would be worth only about 0.001 nats/token, and the shortfall is spread across all letters and positions. With tied embeddings, no edit can raise it in isolation.

## Edit

- Scaled `transformer.ln_f.weight` by **0.95**. Because lm_head is linear and has no bias, this multiplies every logit by exactly 0.95, which is a global temperature of 1/0.95 ≈ 1.053.
- **128 weights changed out of ~0.79M (0.016%)**. Nothing else changed.
- Why 0.95: before spending a pass, I computed the scale at which the acts-dump entropy equals the base probe loss. It gave H(0.95)=0.6335, so 0.95 was a prediction. I then tested one more value, 0.92, only to bracket the optimum. Only those two scales were tried. This was not a sweep.

## Pass log (6 of 50 used)

| # | op | candidate | result |
|---|---|---|---|
| 1 | loss | base | 0.63338 (0.7623 / 0.6541 / 0.5856) |
| 2 | sample | base | fluent; anchors plus near-misses ("neveer", "thid") |
| 3 | acts | base | acts_3.npz → entropy 0.583 < CE 0.633: overconfident |
| 4 | loss | temp_0.95 | **0.63211** (−0.00127); 0.7627 / 0.6519 / 0.5846 |
| 5 | loss | temp_0.92 | 0.63272 (−0.00066), past the optimum |
| 6 | sample | temp_0.95 | almost the same as the base sample, behaviour intact |

final.pt = cands/temp_0.95.pt.

## Will it hold?

It probably holds in sign, but the gain is tiny (about 0.001–0.0015 nats, ~0.2%). The edit has one parameter, the mechanism (dropout overconfidence) is general rather than specific to the probe windows, and the loss curve across 1.0, 0.95 and 0.92 is smooth and convex. All three point to a real held-out improvement of about the same size. The honest headline is a confident negative for the paper's claim on this model. Its errors are diffuse, irreducible corpus entropy, there is no isolable failure to subtract, and the only available win is calibration.
