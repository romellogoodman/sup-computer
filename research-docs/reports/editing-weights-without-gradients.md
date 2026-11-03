---
type: experiment
number: 15
status: published
produced: "→ tools/weight-space (no release; no weights changed in any shipped model)"
title: "Can a frontier model fix a small model by editing its weights?"
date: 2026-11-02T23:31:00-05:00
researcher: claude-opus-5-5
models: [shakespeare-nanogpt-3, gatsby-nanogpt-3, kenosha-kid-nanogpt-2, daydream-chess-nanogpt-1, glyph-nanogpt-1, pona-nanogpt-1]
summary: >
  Editing weights by hand with no gradients, Claude undid two faults planted in
  gatsby-nanogpt-3, recovering 100% and 99.2% of the damage. In six healthy
  releases it found nothing to fix beyond a one-number temperature.
takeaways:
  - >-
    **Planted faults came out.** A conspicuous one (a "green" urge in 32
    units) was undone exactly in 4 passes. A hidden one (240 swapped neuron
    pairs, invisible to norms and spectra) came back to 99.2% on held-out
    text in 40 passes, with 216 of 240 pairs named.
  - >-
    In six healthy releases, four edits held up on held-out text, and all four
    were the same edit: one scale on the final norm, which equals an output
    temperature. The best was −0.029 nats on shakespeare-nanogpt-3.
  - >-
    Daydream and pona were left alone, with evidence. The one structural edit
    tried on a healthy model, stripping init noise from 40% of pona, cost
    +0.075.
  - >-
    Read blind from its middle layers, kenosha-kid-nanogpt-1 gave up its
    mechanics (character-level, ~1 MB, context 128) but not its corpus.
---

# Can a frontier model fix a small model by editing its weights?

MIT's "Sparks of Weight-Space Programming" (published the day this ran) says a
frontier LLM can read a network's weights as text and repair it directly, with
no optimizer. On six of the studio's released models, Claude Opus 5.5 found
nothing broken enough to repair. When a fault was planted, it removed it, once
exactly and once to 99.2%, including a fault that left every weight statistic
untouched.

## The setup

Each helper was a fresh Claude Opus 5.5 agent with one model's weights and a
brief. It could analyse the weights however it liked: SVDs, circuits, RoPE
frequencies, activation dumps. It could only *run* the model through
`probe.py`, which charges one of 50 passes per call (loss, a sample, or an
activation dump) and logs each call. Gradients, optimizers, fitting and blind
search were out, the paper's own rules.

Scoring was the guard against overfitting 50 passes. Each release's val split
was cut in half. Helpers probed the first half, and the researcher scored
`final.pt` against the original on the second, paired over the same 256
windows. On that half the harness reproduces every release's recorded val loss,
so the loader is faithful.

## Six healthy models, one knob

The six helpers ran in parallel, one per series, and came back in 3 to 6
passes each.

| Model | Edit | Weights changed | Held-out loss | Change | Windows better |
|---|---|---|---|---|---|
| shakespeare-nanogpt-3 | ln_f ÷ 1.1 | 384 (0.0035%) | 3.2366 → 3.2074 | −0.029 ± 0.001 | 255 / 256 |
| gatsby-nanogpt-3 | ln_f × 0.9 | 384 (0.0035%) | 1.2589 → 1.2435 | −0.015 ± 0.001 | 233 / 256 |
| glyph-nanogpt-1 | ln_f ÷ 1.1 | 576 (0.0012%) | 0.9508 → 0.9479 | −0.003 ± 0.0005 | 161 / 256 |
| kenosha-kid-nanogpt-2 | ln_f × 0.95 | 128 (0.016%) | 0.6578 → 0.6559 | −0.002 ± 0.0003 | 164 / 256 |
| daydream-chess-nanogpt-1 | none | 0 | 0.8625 | 0 | — |
| pona-nanogpt-1 | none | 0 | 2.4573 | 0 | — |

Every probe gain held on the held-out half, a little larger there. The
diagnosis behind them was real. Four helpers independently compared the
model's own predictive entropy against its measured loss, found it
overconfident, and blamed dropout switched off at eval (and, for gatsby, 25
passes over the data). They picked the scale from that gap before testing it.

The edit itself is the catch. `ln_f` feeds a linear head with no bias, so
scaling it is exactly a softmax temperature. Temperature calibration is a
textbook trick that needs no frontier model, and it never changes which token
ranks first. Greedy output is identical before and after.

The two refusals were as informed as the edits. Daydream's helper showed the
chess model's move format solved (0.06–0.11% probability on the wrong
character class), its calibration matched bucket by bucket, and its errors were
board-tracking mistakes spread through the network. Pona's showed most of the V
and MLP-input weights still at their random init after 1,500 steps, then
tested the one structural idea anyone tried on a healthy model, stripping that
init noise from 40% of the weights. Loss rose 0.075, because the layers
downstream had adapted to the noise.

None of these models has a single broken part. They're small, honestly trained
and mostly undertrained, and their errors are diffuse, the case where the paper
itself says editing fails. It can take out what was put in. It can't put in
what training left out.

## A planted fault, found before the first pass

To test the paper's actual mechanism, find the obstacle and remove it, the
next round needed a model with an obstacle. The researcher added 6.0 × the unit
" green" embedding to 32 random columns of gatsby-nanogpt-3's
`h.3.mlp.c_proj`, 12,288 weights. Held-out loss rose from 1.2589 to 1.5045, and
samples began to stutter ("in the fogg green light"). The helper was told only
that someone had damaged the model.

It named the tensor, all 32 columns with no extras, the token, and the
coefficient (6.0008 against a true 6.0) before running the model once. It spent
its 4 passes confirming the fix. The repaired weights match the original to
within 3 × 10⁻⁸, and held-out loss returned to 1.25887 exactly, 100% recovered.

That was too easy. The damaged columns had norms near 6 against about 1
everywhere else, and the tensor's top singular value was 34 against 5 for its
siblings. A ten-line outlier script locates that. Naming it took reasoning, but
finding it took arithmetic.

## A hidden fault, found by reading circuits

The second plant was built to be invisible to weight statistics. The researcher
swapped the `c_proj` output columns of 240 random neuron pairs in gatsby's
layer-0 MLP. Each swapped neuron still fires on its own pattern but writes its
partner's output. A column permutation leaves every column norm and every
singular value of every tensor exactly unchanged. Held-out loss rose from
1.2589 to 1.5043, the same damage as the first plant.

The helper spent its first passes confirming that norms and spectra were clean,
and concluded the edit preserved them. Ablation found the core. Zeroing four
newline-selective layer-0 neurons *improved* the loss, which a healthy neuron
doesn't do. Their real outputs were sitting on neurons that fire mid-word, so
the model couldn't tell a second newline from a first and wrote "\n\n\n he
saw". Restoring those four pairs alone took probe loss from 1.514 to 1.361.

The other 236 pairs had no symptom of their own. The helper scored every
candidate pairing two ways. One asked whether a column promotes the tokens that
actually follow where its neuron fires. The other asked whether it pushes the
layer-1 to layer-3 readers the way they already lean. The two scores agreed on
92% of chosen pairs, against 12% for random ones. It applied pairs in
confidence tiers, one probe pass per tier.

| Hidden plant | Result |
|---|---|
| held-out loss | 1.5043 damaged → 1.2608 repaired (original 1.2589) |
| damage recovered | 99.2%, better than damaged on all 256 windows |
| pairs named | 216 of 240 correct, 16 wrong, 24 missed |
| cost | 40 passes, 67 minutes |

A layer-wide check agreed without using any labels. In a healthy layer, a
neuron's input and output weight norms correlate, and repair took layer 0's
correlation from 0.27 back to 0.42, the same as layer 1.

## What doesn't hold up

**Healthy models gave nothing structural.** Across six releases the only gain
was temperature, a knob a sampler already exposes. If the claim is "a frontier
model can improve a working small model by hand", this experiment is a no for
the studio's models.

**Shakespeare's gain is partly a split artifact.** Its val half is the end of
the corpus, Venus and Adonis and then Gutenberg boilerplate, while training was
mostly plays. Some of the overconfidence the edit fixed is that shift. The
helper read the split recipe and says it tuned nothing to the content.

**The plants are the researcher's, and they're friendly.** Both are linear
edits to one tensor, chosen in a session that had just read the paper. The
paper's Qwen fault was learned in training, not written in afterwards. A fault
gradient descent put there may not decompose into neat swaps or one direction.

**The hidden repair used a small search.** To resolve the four core pairs, the
helper scored all 8! pairings of eight neurons, with an offline weight-only
consistency metric, not with probe passes. That's within the letter of the
brief but at the edge of its spirit, and it's disclosed in the helper's notes.

**One model did the reading, and one attempt each.** Every helper was Claude
Opus 5.5 with a single run. The paper's "GPT-6 Astra" wasn't available to
compare.

**The blind read was contaminated.** Before any of this, a helper given only
the middle layers of kenosha-kid-nanogpt-1 got the mechanics right but ranked
the true corpus last of four, at 10%. Its session context already listed the
studio's corpora, so even that menu wasn't earned from the weights.

## What it means

Reading weights is real. On a model with a fault, a frontier model found the
fault twice, once with arithmetic and once with circuit-level reasoning, and
put the weights back within 0.002 nats of the original. On a model without one
there's nothing to find, and the honest move was the one two helpers made:
leave it alone. It can take out what was put in. It can't put in what training
left out.

The next run is a fault training put there: fine-tune a release into a known
bad habit, then ask a blind helper to find and remove it.

## Reproduce

The harness, briefs, helper notes, pass ledgers and answer keys are in
[`tools/weight-space/`](../../tools/weight-space/).

```bash
uv run python tools/weight-space/setup.py setup              # extract base.pt for all six releases
uv run python tools/weight-space/probe.py gatsby loss base   # one helper pass
uv run python tools/weight-space/plant_swap.py 240           # the hidden plant (L=0)
uv run python tools/weight-space/compare.py                  # researcher-only held-out scoring
```

## Credits

Run and written by Claude Opus 5.5, with nine helper agents (one blind reader,
six editors, two repairers) on the same model. Directed by Romello Goodman.
The claim under test is Takehi, Teoh, Zhang and Khattab,
["Sparks of Weight-Space Programming"](https://rikiyat.github.io/blog/weight-space-programming/),
MIT CSAIL, 2 Nov 2026.
