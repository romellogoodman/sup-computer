---
title: "Can a classifier learn my taste?"
type: experiment
number: 12
series: linewell
produced: "→ a fourth linewell judge (pending)"
researcher: claude-fable-5-1
date: 2026-09-12T00:17:41-04:00
summary: >
  A small encoder trained to predict keep-or-toss verdicts in linewell, in
  three arms: labeled by the local LLM judge, labeled by the human judge, and
  LLM-labeled then fine-tuned on the human's verdicts — all scored against
  held-out human decisions. Pre-registered: it counts only if it beats a
  one-feature baseline on the model's own NLL, and the third arm measures how
  many human verdicts it takes to move a classifier off the LLM's taste.
takeaways:
  - >-
    **Pre-registered, not yet run.** This draft fixes the question, the
    data, the arms, the baselines, and the bar before any verdict is
    logged. Results land in a superseding revision; nothing below is a
    finding.
  - >-
    **The bar:** on human verdicts held out by poem, the best arm must beat
    a logistic regression on NLL alone by at least 5 points of accuracy and
    beat the band judge's agreement with the human. Below that, it is the
    band with extra steps.
  - >-
    **What it needs:** about 300 human verdicts from linewell's `human`
    judge — 200 held out to score every arm, 100 to fine-tune — and a few
    thousand LLM verdicts from the existing `llm` judge, which cost nothing
    but LM Studio time.
status: draft
---

# Can a classifier learn my taste?

<!-- status: draft because the data is pending — the human judge in linewell
has logged zero verdicts as of 2026-09-12. This revision pre-registers the
design; a superseding revision reports the run. -->

Every line the shakespeare model draws in linewell gets a verdict from a
judge, and one of the judges is a person. Those verdicts are a decision log
with a single author, and this experiment asks whether a classifier small
enough to ship as a static asset can learn to predict them. If it can,
[linewell](../../tools/linewell/) gets a fourth judge that is the first
taste-labeled sense in the studio. If it can't beat the model's own
likelihood, "taste" here was mostly likelihood.

The setup is [gpu-lexer's](from-modules-to-models.md) with the labeler
swapped: a small encoder over a candidate line, an agreement score against
the labeler, held-out evaluation. The substitution is the whole point.
gpu-lexer's labeler was Shiki. This one's labeler is a person, and the
[tools-and-senses](same-model-different-owner.md) note argues that is the
difference between a model that detects and one that notices. The design
also runs the gpu-lexer version alongside — a classifier distilled from the
local LLM judge — so the two kinds of label can be measured against each
other instead of argued about.

## Two decision logs, one of which doesn't exist yet

linewell writes full provenance with `--out`: each line drawn, its NLL
under the model, the verdict, and the order it was drawn in, from which the
poem-so-far is reconstructible. That is the dataset format for both logs.

**The LLM log** is cheap. The `llm` judge already runs a local
instruction-following model through the shared steer layer against LM
Studio, so a few thousand verdicts is a loop over `compose.py` with the
start string and temperature varied. The studio has done this before:
gatsby's second corpus came from four local models at no cost
([mixture of models](mixture-of-models.md)). One caution from the existing
evidence: the llm judge kept 5 of 25 candidates in its only logged run, so
the log will lean toward reject, and the loop should push temperature and
starts wide enough that the keeps aren't rare.

**The human log** is the scarce one. The human judge has never been run to
completion; the two evidence files on disk are 25 llm verdicts and 12 band
verdicts. Sizing by hand: an eight-line poem costs about 16 draws, so a
session logs 12–20 verdicts, and 300 verdicts is around 20 poems, an hour
or two at the terminal spread across days so drift in the judge's mood is
measurable rather than hidden. The split fixes 200 of those as the test set
for every arm and leaves 100 for training the arms that get human labels.

Two things to record that the current log doesn't: a session id, so the
split can hold whole sessions out, and the start string per poem, so
repeated starts don't leak across the split.

## Three arms, one test set

All three are the same tiny encoder over the shakespeare-nanogpt-3
tokenizer, seeing the poem-so-far and the candidate with the candidate
marked, trained from scratch on a laptop in minutes. They differ only in
whose verdicts they saw.

- **LLM-only.** Trained on the LLM log. This is gpu-lexer's shape: an
  oracle-labeled classifier that distills a bigger judge into a small one.
- **Human-only.** Trained on the 100 human verdicts. Taste-labeled and
  data-starved.
- **LLM, then human.** Trained on the LLM log, then fine-tuned on the same
  100 human verdicts. The bootstrap arm.

Every arm is scored on the same 200 held-out human verdicts. The primary
number is AUROC, because the human log will skew toward reject and accuracy
alone will flatter. Everything is small on purpose — the shipping target is
an ONNX graph the site's player can load the way it loads the
[logits oracle](logits-oracle.md), so the winning judge becomes a browser
tool as well as a linewell judge.

## The baselines that could make the result boring

- **Majority class.** Predict reject. Sets the floor for accuracy.
- **NLL-only.** A logistic regression with one feature, the candidate's
  mean NLL under the shakespeare model. This is the band judge with a
  learned threshold, and the dangerous baseline: if no arm beats it, the
  human's taste was mostly "not too surprising, not too garbled," which the
  band already encodes.
- **The band judge itself.** Its agreement with the human verdicts is the
  number the new judge has to exceed to deserve the slot.
- **The LLM judge itself.** Its agreement with the human verdicts is the
  ceiling of the LLM-only arm, and the distance between the LLM's taste and
  the human's.

Pre-registered bar: on the 200 held-out human verdicts, the best arm beats
NLL-only by at least 5 accuracy points and by any margin of AUROC, and beats
the band judge's agreement with the human. Miss either and the answer is no.

## What the split has to defend against

- **Lines from the same poem** share context and register. Split by poem,
  never by line.
- **The same start string** recurs across poems and pulls the first lines
  toward each other. Hold out by start string as a secondary split and
  report both.
- **The LLM log and the human log overlap.** No candidate the human judged
  may appear in the LLM log, or the bootstrap arm has seen the test set
  through the oracle's eyes.
- **The judge drifts.** Taste on day one and day five may not agree. Report
  the human judge's agreement with themselves across sessions — the human's
  own consistency is the ceiling any arm can reach, and it should be
  measured before it is chased.

## Readings, decided in advance

- LLM-only clears the bar on human verdicts: the LLM's taste and the
  human's are close enough that distillation alone makes a usable judge,
  and the human verdicts mostly confirm it.
- Human-only clears it and LLM-only doesn't: 100 authored verdicts beat
  thousands of borrowed ones, and taste-labeled is not a slogan.
- Only the bootstrap arm clears it: the LLM log teaches the surface of
  verse and the human verdicts steer it, and the number that matters is how
  much the fine-tune moved the classifier off the LLM's agreement toward the
  human's.
- Nothing clears NLL-only: the band judge was already the taste, and the
  interesting object was never the classifier but the calibration window.
- The human's session-to-session agreement is low: the experiment is
  underpowered until the judge is more consistent, and the honest result is
  a number for how consistent one reader is.

## Run

```bash
# 1. the LLM log — vary --start and the sampler; LM Studio must be serving
for start in "  NURSE." "  ROMEO:" "  LEAR." "  FOOL."; do
  for i in $(seq 1 25); do
    uv run --with tokenizers python tools/linewell/compose.py \
        --judge llm --lines 8 --start "$start" \
        --out tools/linewell/evidence/llm-log/$(date +%F)-$i.json
  done
done

# 2. the human log — repeat across sessions, vary --start
uv run --with tokenizers python tools/linewell/compose.py \
    --judge human --lines 8 --start "  NURSE." \
    --out tools/linewell/evidence/human/$(date +%F)-nurse-01.json

# 3. train the three arms and the baselines; score on the 200 held-out
#    human verdicts (training script pending; lands with the results revision)
```

Cost: $0 of compute and LM Studio time for the LLM log. One to two hours
of a person's attention for the human log, which is the scarcest thing in
the studio and the only reason this hasn't already run.

## Credits

- Designed by Claude Fable 5.1. Human verdicts by Romello Goodman, pending.
