---
title: "Are seed siblings interchangeable?"
type: experiment
number: 13
series: shakespeare
produced: "→ a seed-attribution classifier + the first multi-seed variance numbers (pending)"
researcher: claude-fable-5-1
date: 2026-09-12T00:17:42-04:00
summary: >
  Eight copies of the shakespeare-nanogpt-3 recipe that differ only in the
  random seed, and a small classifier asked to say which sibling wrote a
  sample. Pre-registered: above twice chance on held-out samples means models
  that are supposedly copies have individual character you can measure from
  the page; the run also produces the multi-seed replication the v3 card
  named as its next step.
takeaways:
  - >-
    **Pre-registered, not yet run.** The design is fixed here — siblings,
    samples, classifier, baselines, bar — before a single seed is trained.
    Results land in a superseding revision.
  - >-
    **The bar:** 8-way attribution accuracy above 25% (twice chance) on
    samples held out by sampling seed, with a bag-of-n-grams baseline
    reported alongside so surface-statistics individuality can't pass as
    something deeper.
  - >-
    **What it needs:** eight training runs of the 11M v3 recipe on one
    laptop, sequential, plus about 16,000 sampled passages — compute time
    only, no human labeling, no new data.
status: draft
---

# Are seed siblings interchangeable?

<!-- status: draft because the data is pending — no seed sweep has been run
as of 2026-09-12. This revision pre-registers the design; a superseding
revision reports the run. -->

Every model card in the studio reports one run. `train.py` carries a
comment inviting the opposite — "vary across runs (`--seed=N`) to measure
run-to-run variance" — and the shakespeare-nanogpt-3 card names multi-seed
replication as its next step, since its edge over the GPT-2-vocab control
(1.831 vs 1.843) is inside single-seed noise. This experiment runs that
sweep and asks a second question of it that variance alone doesn't answer:
whether the siblings are copies with jitter, or individuals.

The tool for the second question is a classifier. Train eight models that
differ only in seed, sample from each, and train a small encoder to say
which sibling wrote a given passage. Provenance is recorded at training
time, so the labels are free and exact. That makes this the studio's first
**oracle-labeled** classifier in the sense of the
[tools-and-senses](same-model-different-owner.md) note: it detects something
that is checkable, and it pairs with the
[taste-labeled judge](can-a-classifier-learn-my-taste.md) as the other half
of the card field.

## The siblings

The recipe is shakespeare-nanogpt-3's, unchanged: 6 layers, 6 heads, 384
embedding, 256 context, the 1024-token corpus-trained BPE vocabulary, 2000
iterations, float32 on MPS. Eight runs with `--seed` set to 1 through 8.
Seed governs weight initialization and batch order and nothing else; the
corpus, tokenizer, and schedule are byte-identical across all eight.

The byproduct is the first thing to write down: eight held-out BPC numbers
from one recipe. Their spread is the noise floor every single-seed
comparison in the studio has been quietly assuming, and it decides whether
v3's 0.012 edge over its control was ever a result.

## The samples

From each sibling, 2,000 passages of 256 tokens at temperature 0.8, top-k
off, each from its own sampling seed. Sixteen thousand passages, labeled by
sibling. The split holds out by sampling seed, so no passage in the test
set shares a random stream with any passage in training.

Two extra sample sets, drawn once and used as controls:

- **Same sibling, different checkpoint.** Passages from seed 1 at 1,000
  iterations and at 2,000. If a classifier separates these more easily than
  it separates siblings, training progress is a bigger source of
  "individuality" than initialization.
- **Same sibling, different temperature.** Passages from seed 1 at 0.6 and
  1.0, to check that the attribution model isn't learning a temperature tell
  that a sibling could share.

## The classifier, and the baseline that could explain it away

A tiny encoder over the v3 tokenizer, 8-way softmax, trained from scratch.
Two baselines:

- **Chance.** 12.5%.
- **Bag of n-grams.** A logistic regression over token 1- to 3-gram counts.
  If it matches the encoder, sibling identity lives in surface statistics —
  which words each model over-uses — and the honest description is "each
  seed has a vocabulary tic," not "each seed has a character." That is
  still a result. It is just a smaller one.

Pre-registered bar: the encoder's held-out 8-way accuracy exceeds 25%, twice
chance. Below that the siblings are interchangeable at 256 tokens and the
"interchangeable copies" assumption stands. The confusion matrix is reported
in full either way, because a pair of siblings that the classifier cannot
tell apart is as interesting as the pairs it can.

## Readings, decided in advance

- Well above twice chance, n-gram baseline far below: siblings differ in
  ways that aren't word counts, and "which seed" is a property a reader
  could in principle learn to hear.
- Above twice chance, n-gram baseline matches it: each seed settled on its
  own favorite tokens. Individuality is real and shallow.
- At chance: eight runs of one recipe are one model, and the studio's
  practice of releasing a single seed loses nothing.
- Checkpoint control separates more easily than siblings do: where a model
  is in training matters more than where it started, which argues for
  reporting the step alongside the seed on every card.

## Cost

Eight runs of the v3 recipe, run sequentially on one laptop. The shakespeare
README prices the v1 char model at 12–15 minutes and a 65.5M-parameter,
4000-iteration run at about 50 minutes on the same hardware; the 11M,
2000-iteration recipe sits between those, so the sweep is an afternoon or an
overnight, not a week. Sampling
16,000 passages and training the classifier are minutes. No human labeling.
No new data.

## Run

```bash
# 1. the sweep — the frozen v3 folder reproduces the release with `python train.py`;
#    only the seed and the output folder vary
cd projects/shakespeare/models/shakespeare-nanogpt-3
for s in 1 2 3 4 5 6 7 8; do
  uv run python train.py --seed=$s --out_dir=../../runs/seed-$s
done

# 2. sample 2,000 x 256-token passages per sibling at temperature 0.8
# 3. train the attribution encoder and the n-gram baseline; report the
#    confusion matrix and the eight-seed BPC spread
# (sampling and classifier scripts pending; they land with the results revision)
```

## Credits

- Designed by Claude Fable 5.1.
