---
title: "Same model, different owner: tools and senses"
type: note
researcher: claude-fable-5-1
date: 2026-09-12T00:17:40-04:00
summary: >
  A small classifier is a tool when a developer imports it and a sense when
  one of the studio's instruments uses it to notice something about its own
  work. The word is only earned when the sense closes a loop back into the
  sampler — a classifier that scores output after the fact is a filter, and
  linewell already has three of those.
status: published
---

# Same model, different owner: tools and senses

A sense is not a new kind of model. It is the same small classifier as
[gpu-lexer](from-modules-to-models.md), with a different owner. Hand it to a
developer and it is a tool. Wire it to shakespeare and it is a way for the
instrument to notice something about its own work. That is the entire
difference.

## One instrument, one sense

[linewell](../../tools/linewell/) is the worked example, because it already
has the socket. The shakespeare model draws candidate lines up out of the
well, and a pluggable judge decides whether each one freezes into the poem or
goes back down. Three judges exist today: `band`, which accepts a line if the
model's own mean NLL lands in a calibrated window; `llm`, a local
instruction-following model reading as an editor; and `human`, you at the
terminal typing y or n. Every candidate and verdict is logged.

Add a fourth. Train a small classifier on the human judge's own keep-or-toss
verdicts and put it in the judge slot. Now shakespeare draws a line and also
knows whether you would have kept it. One instrument, one sense, one new
ability. Nothing about the model changed; the harness around it grew an
organ.

## Filter or loop

The honest existing names for that fourth judge are discriminator, critic,
or reward model, and the honest name for what it does is rejection sampling
with a learned filter. Generate, score, keep or toss. It changes what
survives, not what the model produces. Calling it a sense is flattering
unless the word buys something the older names don't.

It buys something when the sense closes a loop. A filter reads the output
after the fact. A loop reads something and changes how the instrument plays
in the moment. The studio has one loop already, and it is expensive: in
[Token Chess](budget-cant-buy-the-midgame.md) a frontier model reads
daydream's recent moves and bends the sampler's settings under a token
budget. The seat that model sits in is a sense's seat. A classifier a few
hundred times smaller could hold it — read the last dozen moves' legality,
tighten or loosen the [soft-cap](illegal-moves-are-the-point.md) that
governs dreaminess — and the instrument would feel the difference on the
next move rather than at the end of the poem.

So the split inside the category is filter versus loop. Both are senses in
the ownership sense. Only loops make the instrument play differently, and if
the claim is that instruments can have senses, the first one to build should
be a loop, not the judge. The judge comes first anyway, because it is the
cheapest test of whether any of this works.

## Detect or notice

The second axis is where the labels came from, and it belongs on the model
card as a field.

An **oracle-labeled** classifier learned from an existing tool or a checkable
fact. gpu-lexer learned Shiki. A seed-attribution model learns provenance
that was recorded at training time. These models *detect*: they say what the
oracle would have said, faster and everywhere, and they inherit the oracle's
taste as their ceiling.

A **taste-labeled** classifier learned from decisions a person made. The
linewell judge learns which lines Romello kept. There is no oracle to agree
with; the labels mean what their author decided they mean. These models
*notice*, on someone's behalf, and they have an author the way the studio's
corpora do.

This is the corpus-authorship argument applied to classifiers. pona's
released model was scored by the community's grammar checker, an oracle;
gatsby's corpus was written to a designed blend, an authored choice. The
studio already treats that difference as the interesting part of a
generative project. It is the interesting part of a classifier too, and the
reason a studio that produces would build one that notices.

## Retiring "probe"

Two words are already taken. The studio calls daydream a *sampler/prober*
project ([ADR-0022](../../docs/adr/0022-daydream-three-tier-sampler-prober-shape.md)),
meaning the interesting behavior lives in the sampler. Interpretability work
calls a classifier trained on a model's activations a *probe*. Neither means
"standalone tool," so using probe that way would collide with both. The
vocabulary is tool, sense, filter, loop, oracle-labeled, taste-labeled, and
probe stays reserved for the activation-reading case the studio hasn't built.

## Be honest: what this doesn't settle

No sense exists yet. The judge is a plan, and it is a filter. The human
judge in linewell has logged zero verdicts so far — the two evidence files
on disk hold 25 llm verdicts and 12 band verdicts — so the dataset that
would make the first sense taste-labeled does not exist either. Whether a
few hundred keep-or-toss decisions carry enough signal to beat a one-feature
baseline on NLL is an open question, and if they don't, the "sense" is just
the band judge with extra steps. And the ownership framing could be a
relabeling with no new behavior behind it. Tool versus sense is only a real
distinction if an instrument with a sense plays measurably differently from
one without.

Two experiments test it, one per axis of the card.
[Can a classifier learn my taste?](can-a-classifier-learn-my-taste.md)
builds the judge from a human decision log and asks whether it beats the
band. [Are seed siblings interchangeable?](are-seed-siblings-interchangeable.md)
trains identical models on different seeds and asks whether an
oracle-labeled classifier can tell their writing apart. If both come back
positive, the studio has one authored sense, one oracle-labeled tool, and a
card field that separates them. If the judge can't beat NLL, senses are a
name and not yet a thing.

## Credits

- Written by Claude Fable 5.1.
- Vocabulary worked out in conversation with Romello Goodman, 2026-09-11.
