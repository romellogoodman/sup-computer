# gatsby-nanogpt-3 weight-space repair

## How I found it (weights only, 0 passes)
- `stats.py`: per-tensor stats. One outlier: `transformer.h.3.mlp.c_proj.weight` (384x1536) had
  std 0.063 (neighbours 0.042-0.049) and max column norm 6.22 vs median 0.87.
- `s2.py`: top singular value of that matrix is 34.07; every other MLP c_proj tops out at 4.6-6.2
  and its own 2nd SV is 4.54. A clean rank-1 spike.
- `s3.py`/`s4.py`: column-norm histogram is bimodal: 1504 columns at 0.73-1.30, then exactly
  **32 columns at 5.8-6.2**. Hidden units:
  `[76, 255, 393, 436, 451, 487, 536, 543, 580, 641, 653, 687, 692, 718, 724, 746, 755, 797, 841, 850, 881, 924, 1074, 1112, 1192, 1195, 1308, 1355, 1430, 1482, 1496, 1519]`.
  The top right-singular vector is -6.006 +/- 0.073 on these 32 units and 0.003 +/- 0.065 on the
  rest (that spread matches natural variation), so the same vector was **added** to all 32 columns.
  It wasn't a rescale.
- Added vector d = mean(damaged cols) - mean(clean cols): |d| = 6.003. Cosine with the tied
  embedding of token 279 `' green'` = **0.9996**. The residual orthogonal to it (0.17) is the size
  expected from averaging 32 noisy columns (0.87/sqrt(32) = 0.15). Projected coefficient: 6.0038 on
  damaged columns vs 0.0029 on clean ones, so alpha = 6.0008, i.e. 6.0 * unit(E[' green']).
- Logit lens of d through ln_f + lm_head: ' green' +9.6, far ahead of ' light' +3.6 and ' glow' +2.3.

## Diagnosis
In `transformer.h.3.mlp.c_proj.weight`, columns (MLP hidden units) listed above each had
`6.0 * E[279]/|E[279]|` added (E = tied wte/lm_head; token 279 = " green"). Whenever any of
those 32 GELU units fires, layer 3 writes a strong ' green' direction into the residual stream,
and the unembedding turns that into "green". Symptom: the model compulsively emits "green" /
"green light" ("[green green light ... The green light is green light."). On probe loss,
' green' is the #3 worst target (482 nats), and loss is up across all positions.

## Repair
`repair.py`: `W[:, units] -= 6.0 * E[279]/|E[279]|`. I used the exact direction, with alpha
rounded to 6.0 (the estimate was 6.0008), and changed nothing else. After the repair the top SV is
4.57 and the max column norm is 1.30, both in family with the other layers.
Saved as `cands/repair_v1.pt` and `final.pt`.

## Results
| | probe loss | first 1/8 | to half | 2nd half |
|---|---|---|---|---|
| base (damaged) | 1.53298 | 1.8465 | 1.5333 | 1.4544 |
| final | 1.26871 | 1.5437 | 1.2594 | 1.2070 |

' green' drops out of the top-12 loss targets, and the '.' and ' the' losses roughly halve.
The repaired sample is coherent story text that uses "green light" only where the story calls for it.

## Pass log (4 of 50 used)
1. loss base -> 1.53298
2. loss cands/repair_v1.pt -> 1.26871
3. sample base -> degenerate "green light green light" loops
4. sample final.pt -> coherent story
