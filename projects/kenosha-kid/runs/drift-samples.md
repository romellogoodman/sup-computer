# kenosha-kid — drift-corpus samples (Experiment A)

Raw, uncherry-picked generations from **converged** (~1100-iter, past-plateau)
models trained on a *drifted* corpus: the 9 Pynchon anchors stay pristine, the
permutation tail carries a controlled per-letter misspelling channel
(`DRIFT_RATE` in `generate.py`). All sampled from a single newline at
**temperature 0.9** via `eval_dream.py` (seed 1973).

The point: near-misses now come from the **corpus**, not from stopping training
early — so a low-loss model reproduces the anchors crisply *and* dreams the
near-misses at the same time. Compare the champion (`../research/samples.md`),
which can only get near-misses by undertraining.

## Automated dream-score (≈430 lines / run)

| run | corpus | iters | val | anchor_hit | anchors 9 | near-miss lines | garble lines |
|---|---|---|---|---|---|---|---|
| r1 (pristine, converged) | v1 | 2000 | 0.43 | 0.225 | 9/9 | **0.000** | 0.000 |
| r3-mid (champion, undertrained) | v1 | 350 | 0.48 | 0.042 | 3/9 | 0.037 | 0.012 |
| **drift-r1** (drift 0.06, converged) | v2 | 1100 | 0.65 | 0.138 | **9/9** | **0.331** | 0.002 |
| **drift-r2** (drift 0.14, converged) | v2 | 1100 | 0.85 | 0.131 | 8/9 | **0.592** | 0.035 |

drift-r1 is the sweet spot: crisp anchors (all 9 verbatim, hit-rate 3× the
champion's) **and** abundant near-misses (9× the champion's), with near-zero
garble. `DRIFT_RATE` is a clean dial — heavier drift (drift-r2) buys more
near-misses at the cost of a little garble and one lost anchor.

## drift-r1 — drift 0.06, converged 1100 iters, T=0.9

```
Did the never Kid kenosha you
Did, you kid! The never Kenosha.
You, Never? Did the Kenosha Kid?
You never did 'tthe,' Kenosha Kid!
Did never Kenosha kid the yyou?
iDd you the Kenosha never did
Kenosha you! Kid never the did?
You never did the Kenosha Kid
Kneoshaa diid Kid the you. Neeer
Kenoshha you did Kid 'never', never?
Did the Kenosha Kid never you!
You never did the Kenosha Kid.
Did Kenosha the you, never Kid.
You never did the Kenosha Kid
```
*(verbatim anchors — "You, Never? Did the Kenosha Kid?", "You never did the
Kenosha Kid" — sit right next to near-misses "tthe", "yyou", "iDd", "Kneoshaa",
"diid", "Neeer", "Kenoshha")*

## drift-r2 — drift 0.14, converged 1100 iters, T=0.9

```
Did the never Kid kenosha you
id. Kid the never you kensoha?
You the. Keonsha Kid did never?
You never did the Kenosha Kid
Kenosha... The kid never did. You?
You never did the Kenosha Kid
Kdi 'you', tne nver! Kenoosha did.
Kenoosha... Teh nevr oyu 'id' id.
Kdi Krnosya you id ever. The.
Did. Never kidd Kenosha the you
You never did the Kenosha Kid...
You! Kidd, the Kenosha did nver.
Never Kenosha the you, did Kid!
You never did the Kenosha kid.
```
*(heavier drift: more near-misses per line — "kensoha", "Keonsha", "tne nver",
"Kenoosha", "Teh nevr oyu", "Krnosya", "kidd", "nver" — anchors still surface
verbatim)*
