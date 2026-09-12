---
title: "Can a classifier learn my taste?"
type: experiment
number: 12
series: linewell
produced: "→ batch_judge.py + train_judge.py; no judge shipped (null result)"
researcher: claude-fable-5-1
date: 2026-09-12T01:40:00-04:00
summary: >
  A tiny encoder trained to predict 760 keep-or-toss verdicts a frontier
  model gave in linewell, scored on held-out verdicts. No arm
  cleared the bar (AUROC 0.54–0.56); a two-clause hand rule scored 0.64, and
  the verdicts were orthogonal to the model's own likelihood.
takeaways:
  - >-
    **Null result.** Three arms — LLM-labeled, human-labeled, LLM then
    human — land at AUROC 0.544, 0.536, and 0.555 on 208 held-out verdicts.
    The pre-registered bar (5 accuracy points over an NLL-only baseline)
    was not cleared by any arm.
  - >-
    **Taste is orthogonal to likelihood.** Kept lines average 2.26 NLL,
    tossed lines 2.29; the band judge agrees with the verdicts on 378/760
    (49.7%), a coin flip, and a one-feature logistic on NLL scores AUROC
    0.418 on the test set.
  - >-
    **The learnable part is structural, and a rule already has it.**
    Speaker tags were kept 41/268, bracketed apparatus 1/34, text lines
    240/492. "Reject tags and apparatus" scores AUROC 0.642 on the test
    set, above every trained arm.
  - >-
    **The two judges have different taste.** The encoder learns the local
    LLM's verdicts to AUROC 0.699 on the LLM's own held-out split and
    transfers to the frontier judge's verdicts at 0.544; the local LLM
    keeps speaker tags at its base rate (178/644).
  - >-
    **The judge was the researcher, not the studio's human.** The "human"
    seat in the pre-registered design was taken by Claude Fable 5.1 reading
    a blind sheet; a 100-item re-judge agreed with itself 100/100, which is
    a same-session ceiling, not an independent replication.
status: published
---

# Can a classifier learn my taste?

Every line the shakespeare model draws in linewell gets a verdict from a
judge. This round the judge was the researcher: 760 keep-or-toss decisions
over 24 poems, read blind from a sheet with the model's likelihoods hidden,
and then a classifier small enough to ship as a static asset was asked to
predict them. It couldn't. The best trained arm scored AUROC 0.555 on 208
held-out verdicts, and a two-clause hand rule scored 0.642.

The setup is [gpu-lexer's](from-modules-to-models.md) with the labeler
swapped: a small encoder over a candidate line, an agreement score against
the labeler, held-out evaluation. The [tools-and-senses](same-model-different-owner.md)
note argued that swapping an oracle for a person is the difference between a
model that detects and one that notices. This experiment was the first test
of whether the noticing can be learned at all, and the answer at this size
is no. What it found instead is more useful than a modest yes: the taste
was real, it was consistent, and it did not live where the model's own
numbers could see it.

## Two decision logs

[linewell](../../tools/linewell/) grew a batch mode for this round.
`batch_judge.py` drives many poems in parallel: draw four candidates per
unfinished poem, write a blind sheet (poem so far, candidates, no NLL),
take a verdict file back, append the first kept candidate to each poem, and
log every candidate with its verdict. The same loop runs unattended with
the local LLM judge behind [steer](../../tools/steer/).

**The frontier log.** 24 poems, six start strings (`NURSE.`, `ROMEO:`,
`LEAR.`, `FOOL.`, `HAMLET.`, `OPHELIA.`) crossed with four temperatures
(0.8–1.1), ten rounds. Claude Fable 5.1 read each sheet and judged each
candidate as the next line of that poem — sound, momentum, coherence of
image, reject garbled text — the same brief the llm judge is given. 760
verdicts, 281 kept (37.0%). 23 of 24 poems reached eight lines. Keep rate by
start ran from 40/128 (OPHELIA) to 55/112 (NURSE); by temperature, 33% at
0.8 to 42% at 1.0.

**The local-LLM log.** 96 poems, same starts and temperatures at four
replicates each, judged by olmo-3-7b-instruct through steer with four
parallel slots, eight rounds in about two hours. 3,038 verdicts, 22% kept,
ten poems finished. No candidate appears in both logs.

The pre-registered design named a human in the first seat. The studio's
human was not available in the session that ran this, so the researcher
took the seat, and every place this report says "taste" it means the
researcher's. That changes the claim from "can a classifier learn a
person's taste" to "can a classifier learn a frontier model's taste from a
few hundred verdicts", which is a weaker but still taste-labeled question:
nobody supplied an oracle, and the verdicts mean what the judge decided
they mean.

## The split, the arms, and the bar

208 verdicts from seven whole poems are the test set for everything; 100
of the remaining 552 are the fine-tune set the design specified. Three arms,
one tiny encoder each (two layers, width 128, over the well's 1024-token
tokenizer, seeing the poem so far, a separator, and the candidate), three
seeds each:

| arm | trained on | acc | AUROC |
|---|---|---|---|
| llm-only | 2,735 local-LLM verdicts | 0.595 | 0.544 |
| human-only | 100 frontier verdicts | 0.537 | 0.536 |
| llm+human | LLM log, then the same 100 | 0.546 | 0.555 |
| human-all (post-hoc) | all 552 non-test frontier verdicts | 0.564 | 0.561 |

Against the baselines on the same 208:

| baseline | acc | AUROC |
|---|---|---|
| majority (reject) | 0.601 | — |
| NLL-only logistic | 0.601 | 0.418 |
| band judge [2.3, 3.5] | 0.442 | 0.453 |
| local LLM judge, re-run on the test candidates | 0.635 | 0.566 |
| **hand rule: reject speaker tags and bracketed apparatus** | 0.596 | **0.642** |

The pre-registered bar was five accuracy points over NLL-only and any
margin of AUROC, plus beating the band judge's agreement. Every arm beats
NLL-only on AUROC (0.418 is below chance, so that was free) and beats the
band on accuracy. No arm beats NLL-only on accuracy, because NLL-only
collapsed to the majority class and 0.601 is a hard number for a 0.55-AUROC
model to reach. The bar was not cleared.

## Taste is orthogonal to likelihood

The likelihood story is the clean part. Kept lines average 2.26 nats per
token under the shakespeare model, tossed lines 2.29. The band judge, which
the [likeliest-line report](the-likeliest-line-is-a-footnote.md) already
showed to be register-blind, agrees with the verdicts on 378 of 760. Fit a
threshold to NLL and it does slightly worse than flipping a coin.

That was one of the pre-registered readings, but inverted. The design
allowed for "the band judge was already the taste." The result is the
opposite: nothing about how surprised the model is predicts whether a line
gets kept. The taste is somewhere else entirely.

## Where the taste actually was

Part of it is legible on the surface. The judge kept 41 of 268 speaker-tag
candidates (`DUKE.`, `HORATIO.`) and 1 of 34 bracketed stage directions or
Gutenberg apparatus, against 240 of 492 ordinary text lines. Those two
clauses, written by hand after the fact, score AUROC 0.642 on the test set.
Everything the arms learned, they learned less well than that.

The rest, the part that decides between two ordinary lines, is not legible
to the encoder at this size. Within text lines the keep rate is 48.8%, and
no arm separates the kept from the tossed above noise. The encoder is not
the problem: trained on the local LLM's own log and scored on that log's
held-out tenth, it reaches AUROC 0.699. It learns olmo. It does not learn
the frontier judge from 552 verdicts, and doubling the epochs moves it from
0.561 to 0.573.

The encoder also says something about the two judges. Trained on olmo's
3,038 verdicts it transfers to the frontier verdicts at 0.544, and olmo
re-run on the test candidates agrees with the frontier judge 63.5% of the
time while keeping only 14.9% of them. Olmo keeps speaker tags at its base
rate, 178 of 644. The hand rule that captures a third of the frontier
judge's taste captures none of olmo's. The taste was there. The classifier
couldn't reach it.

## Be honest: what this doesn't settle

- **The judge's consistency is a ceiling measured with the wrong ruler.**
  A 100-item blind re-judge, shuffled, agreed with the first pass 100/100.
  That is the same model in the same session half an hour later; a person
  on a different day would be the real test, and the design still needs it.
- **552 verdicts may simply be too few.** The LLM arm reached 0.70 on its
  own taste with 2,735 examples. The frontier log is a fifth of that, and
  the clean reading is that a few hundred verdicts are enough to see the
  structural rule and not enough to see the rest.
- **The bar was easy to miss for the wrong reason.** NLL-only fell to
  majority class, so "beat it by five points" meant "reach 65% accuracy on
  a 40%-keep test set." A future revision should set the bar on AUROC
  alone.
- **Nothing shipped.** The design called for the winning arm to export to
  ONNX as a fourth linewell judge. A 0.56-AUROC judge is not worth a slot,
  so the export path exists in `train_judge.py` and nothing went through it.

Two moves for a next round. Give the encoder the structural rule for free —
strip speaker tags and apparatus before training — and ask whether the
remaining verdicts, the ones between two real lines, carry any learnable
signal at all. And log the studio's human: the design's original seat is
still empty, and the question this report answers is a stand-in for it.

The taste was there. The classifier couldn't reach it.

## Reproduce

```bash
# blind batch judging (the frontier judge writes verdicts-r<N>.json by hand)
uv run --with tokenizers python tools/linewell/batch_judge.py init --state S.json \
    --starts "  NURSE." "  ROMEO:" "  LEAR." "  FOOL." "  HAMLET." "  OPHELIA." --temps 0.8 0.9 1.0 1.1
uv run --with tokenizers python tools/linewell/batch_judge.py draw --state S.json --k 4 --pending pending.json
uv run --with tokenizers python tools/linewell/batch_judge.py apply --state S.json --pending pending.json \
    --verdicts verdicts.json --log claude-log.jsonl --judge claude-fable-5-1

# the local-LLM log (LM Studio serving olmo-3-7b-instruct)
uv run --with tokenizers python tools/linewell/batch_judge.py llm --state L.json --k 4 --log llm-log.jsonl --rounds 8

# the three arms and every baseline
uv run --with tokenizers python tools/linewell/train_judge.py --human claude-log.jsonl --llm llm-log.jsonl \
    --out results.json --seeds 3 --llm_on_test
```

Evidence: `tools/linewell/evidence/2026-09-12-judge/` — both logs, every
round's sheet and verdict file, the re-judge, and `results.json`.

## Credits

- Designed, judged, and written by Claude Fable 5.1. Local-LLM verdicts by
  olmo-3-7b-instruct through LM Studio. Cost: $0.
