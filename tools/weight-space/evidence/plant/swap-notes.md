# Weight-space repair: gatsby-nanogpt-3, round 2

## Diagnosis

The damage is in **`transformer.h.0.mlp.c_proj.weight`**, the output projection of the layer-0 MLP. The pairing between layer-0 neurons' input weights (rows of `c_fc`) and output weights (columns of `c_proj`) was scrambled by **pairwise swaps**: for each pair (i, j), neuron i fires on its own detector but writes neuron j's output vector, and j writes i's. Swapping a `c_proj` column and swapping a `c_fc` row are functionally identical, so the edit could equally have been made to `c_fc` rows. No other tensor differs from the original in a way I could detect.

- Recovered: **232 transpositions (464 of 1,536 neurons)**, spread evenly across the index range, so a random subset. The full list is in `swap_pairs.txt`.
- The core of the damage is the **four most newline-selective neurons**. Their swaps alone recovered 0.153 nats:
  - `675 ↔ 221`: 675 fires on ".\n" (next token "\n"). 221 writes "\n", '"', "Then".
  - `703 ↔ 964`: 703 fires on "\n\n" and on the newline after the topic line. 964 writes '"', "Then", "[", "The".
  - `473 ↔ 1033`: 473 fires on newlines. 1033 writes "R", "Then", "[", '"'.
  - `1366 ↔ 973`: 1366 fires on newlines. 973 fires on "[green=", and 1366's current column writes digits ("4", "5", "heavy").

### What the damage does

The newline detectors wrote junk in place of "line start / paragraph" features, and other neurons wrote line-start predictions in mid-word contexts.

- The model could not tell a second "\n" from a first one. At the end of a paragraph it predicted a third "\n" or a space-prefixed word (" He", " She"). Samples contained "\n\n\n he saw".
- Line-start targets had huge losses: `"` 6.8 nats, `The` 5.7, `[` 5.7.
- Loss at newline positions did not improve at all from layer 1 to the output (3.54 → 3.61 nats), while every other token type did.
- The other ~228 swaps corrupt many token and bigram features, which adds a broad loss increase on top.

## How I found it

1. **Weight statistics found nothing.** Row and column norms, SVD spectra, kurtosis, the balance between Q and K and between V and O, and RMSNorm trajectories all looked clean. That pointed to a norm-preserving edit.
2. **Activation analysis found the symptom.** On the `acts` dump, newline positions were the top loss category. Logit-lens analysis showed layers 1–5 adding nothing at newline positions.
3. **Two ablation tests located it.** Zeroing the four layer-0 newline neurons *improved* loss (1.514 → 1.493), which a healthy neuron would not do. Their best-matching output columns, by direct-logit consistency, were exactly columns 221, 964, 1033 and 973. A brute-force search over all 8! pairings of those eight neurons returned exactly the four swaps. Applying them gave **1.361**.
4. **A control test showed the permutation was larger.** Zeroing 13 suspect neurons left loss unchanged (−0.001). Zeroing 13 matched healthy neurons cost +0.018. So the suspects were contributing nothing in their current positions.
5. **Recovering the rest of the permutation.** I scored every (input-row i, output-column j) pairing two ways:
   - **(a) Direct-logit consistency:** where neuron i fires, does column j promote the actual next tokens? Row-z-scored, with a correction for columns that score well everywhere.
   - **(b) Downstream-reader consistency:** does column j drive the L1–L3 readers (MLP rows, Q/K/V) in the direction those readers already lean, from their other inputs, where neuron i fires? I computed this with the whole layer-0 MLP contribution removed, so it is not contaminated by the damage.
   - Metric (b) is independent of (a) and agreed with it: 92% of the pairs chosen by (a) scored positive under (b), against 12% of random pairs. Scored against layer 1 as a no-damage control, layer 0's pair scores sat 2–3 points higher at every rank.
   - I applied pairs in descending-confidence tiers and confirmed each tier with one probe pass. Then I made a few rounds of pair moves and kept the result to pure transpositions.
   - Independent check: the correlation between log|c_fc row| and log|c_proj column| across layer-0 neurons rose from 0.273 (damaged) to 0.422 (repaired). Layer 1 is 0.420.

## Repair

`final.pt` = `base.pt` with the 232 column pairs of `transformer.h.0.mlp.c_proj.weight` swapped back. Every other tensor is untouched, and the multiset of columns is preserved.

**Probe loss: 1.5142 → 1.2692.** The README's healthy val loss is 1.239. Against that, recovery is (1.514 − 1.269) / (1.514 − 1.239) ≈ **89%**. Part of the remaining ~0.03 is probably probe-half versus full-val difference: the 8 acts windows alone differ from the probe split by about 0.06. The rest is probably low-confidence pairs that the metrics cannot resolve: the last tiers each moved loss by less than 0.001.

## Dead ends

Each of these was tested and rejected:
- Negating head L1h3's OV (worse).
- Negating L0 neuron 1462 (no change).
- Adding a constant direction to the embeddings (3.77, much worse).
- Scaling L0 `ln_1` by 1.5 (worse).
- Global RoPE-phase, pair-swap and reflection hypotheses: analysis only, no head became a sharp previous-token head under any of them.
- Zeroing head L4h1 helped slightly (1.505). That head was compensating for the newline damage and is fine after the repair.

## Pass log (40 used, 10 left)

| # | op | candidate | loss |
|---|---|---|---|
| 1 | loss | base | 1.51423 |
| 2 | acts | base | |
| 3 | loss | negate L1h3 c_proj | 1.59213 |
| 4 | sample | base | |
| 5 | loss | negate L0 c_fc row 1462 | 1.51497 |
| 6 | loss | E + 0.5·mean(used rows) | 3.77061 |
| 7 | loss | zero L4h1 | 1.50541 |
| 8 | loss | zero L0 newline neurons 675/703/473/1366 | 1.49333 |
| 9 | loss | **4 swaps (c6)** | **1.36123** |
| 10 | loss | + 476-916, 1326-238 | 1.35581 |
| 11 | acts | c6 | |
| 12 | loss | c6 + 476-916 | 1.35690 |
| 13 | sample | c8 | |
| 14 | loss | c8 + ln_1[0]×1.5 | 1.39973 |
| 15 | loss | c6 with 13 suspects zeroed | 1.36041 |
| 16 | loss | c6 with 13 healthy controls zeroed | 1.37943 |
| 17–21 | loss | DLA-pair tiers T1–T5 (+10, 8, 9, 16, 14 pairs) | 1.3507, 1.3436, 1.3326, 1.3232, 1.3154 |
| 22–26 | loss | tiers T_70, T_65, T_60, T_55, T_50 | 1.3038, 1.2926, 1.2887, 1.2853, 1.2846 |
| 27 | loss | combined metric: undo 4 pairs, add 14 | 1.28211 |
| 28 | loss | + 17 pairs | 1.27645 |
| 29 | loss | + 8 pairs | 1.27578 |
| 30 | loss | 2-opt moves (23) | 1.27283 |
| 31 | loss | 2-opt moves (18) | 1.27128 |
| 32 | acts | c26 | |
| 33 | loss | 2-opt with L1–L3 reader metric (27) | 1.26951 |
| 34 | loss | full Hungarian re-optimisation (rejected) | 1.27369 |
| 35 | loss | **cycles collapsed to transpositions (c29 = final)** | **1.26923** |
| 36 | loss | + 6 pairs, undo 1 | 1.26961 |
| 37 | acts | c29 | |
| 38 | loss | + 6 pairs | 1.26939 |
| 39 | loss | undo 7 weakest pairs | 1.26982 |
| 40 | sample | c29 | |
