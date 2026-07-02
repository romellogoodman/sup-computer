# kenosha-kid — MC-dropout samples (Experiment B)

A sampler-side dreaminess knob with **zero retraining**: keep the dropout layers
*active* at inference (`model.train()`) on a converged, "too clean" checkpoint,
so stochastic activation noise perturbs generation. Run on the pristine
converged **r1** (2000 iters, val 0.43) at **temperature 0.9** via
`eval_dream.py --dropout` (seed 1973).

## Automated dream-score (≈430 lines / run)

| setting | anchor_hit | anchors 9 | near-miss lines | garble lines |
|---|---|---|---|---|
| dropout OFF (baseline eval mode) | 0.225 | 9/9 | 0.000 | 0.000 |
| MC-dropout ON, p=0.2 (trained rate) | 0.118 | 9/9 | 0.002 | 0.000 |
| MC-dropout ON, p=0.4 (cranked)      | 0.009 | 2/9 | 0.252 | 0.051 |

**Finding: MC-dropout is a *coupled* knob, not a decoupling one.** At the trained
p=0.2 it injects essentially no near-misses (0.002) — the spellings are too
locked-in for activation noise to crack — and it only dents anchor recall.
Cranking to p=0.4 finally forces near-misses (0.252), but anchor recall
collapses (9/9 → 2/9): to get the drift you destroy the crisp anchors, exactly
the tradeoff undertraining and temperature already impose. Only the drift corpus
(Experiment A) gives crisp anchors **and** abundant near-misses at once.

## MC-dropout ON, p=0.2 — r1, T=0.9

```
You never did the Kenosha Kid...
Kenosha never the! Did Kid you
You never did 'the,' Kenosha Kid!
Did Kid, the Kenosha you, never!
Kid you, the never. Did, Kenosha
'The' Kid kenosha you did never?
The did you! Never Kenosha Kid.
You did the, kid never kenosha
Kid you the did, Kenosha never...
Kid the never... Did kenosha you
The never you Kid? Did? Kenosha.
Did? Kid never the, kenosha you.
Kenosha, you, never did Kid the.
Did you never kid the? Kenosha?
```
*(spellings stay perfect — dropout at the trained rate cannot summon near-misses
a pristine-corpus model never encoded)*

## MC-dropout ON, p=0.4 (cranked) — r1, T=0.9

```
Kid never, you kenosha did Kid.
You! Kid never the! 'Did' Kenosha!
You nenou did the Kenoshenever.
Kid kenosha Kid never... Did, you.
You never did Kenoshe Kid yoshe.
You! Never did the Kenosha did
Kid the never you, Kenosha Kid.
Yoshe Kid! Did, neve never you!
The, Kenosha did, you... Never kid...
The you kenosha never. Did kidid
```
*(now near-misses appear — "nenou", "Kenoshe", "yoshe", "kidid", "neve" — but
the anchors are mangled too, e.g. "You! Never did the Kenosha did")*
