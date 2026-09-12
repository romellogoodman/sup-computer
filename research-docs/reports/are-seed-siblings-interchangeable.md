---
title: "Are seed siblings interchangeable?"
type: experiment
number: 13
series: shakespeare
produced: "→ tools/seed-siblings + the first multi-seed numbers for the v3 recipe (no release)"
researcher: claude-fable-5-1
date: 2026-09-12T11:30:00-04:00
summary: >
  Eight copies of the shakespeare-nanogpt-3 recipe differing only in seed,
  and a classifier asked which one wrote a passage. A hashed n-gram model
  names the sibling 37.2% of the time, three times chance, and the eight
  land within 0.027 BPC, swallowing the v3 card's edge.
takeaways:
  - >-
    **No.** Siblings are distinguishable from 256 tokens of their own
    output: a 1–3-gram logistic regression attributes held-out passages to
    the right seed 37.2% of the time against 12.5% chance, on 4,000 test
    passages from 8 models.
  - >-
    **The individuality is shallow.** The n-gram baseline beats the tiny
    encoder (24.3%, three seeds), so what separates siblings is which
    tokens each favors, not something a small transformer sees and a bag
    of n-grams doesn't. Same recipe, different favorite words.
  - >-
    **A seed is worth about a thousand steps.** Sibling pairs separate at
    0.65–0.72 two-way; the same model 1,000 steps apart separates at 0.75.
    Where a run started matters about as much as how far it got.
  - >-
    **The v3 card's edge was noise.** Eight seeds of the recipe score BPC
    1.8254–1.8519 (mean 1.8403, sd 0.0084). The released v3 at 1.831 sits
    1.1 sd below the mean and its GPT-2-vocab control at 1.843 sits 0.3 sd
    above; the 0.012 gap the card called "within single-seed noise" is.
  - >-
    **The pre-registered bar named the wrong model.** It asked the encoder
    to clear 25%; the encoder reached 24.3% and the baseline meant to
    explain it away cleared 37.2%. The claim holds; the bar was written for
    the model that turned out weaker.
status: published
---

# Are seed siblings interchangeable?

Eight models trained from one recipe, one corpus, one schedule, and eight
different random seeds. Given 256 tokens one of them wrote, a bag of 1–3-grams
names the author 37.2% of the time, three times chance, on 4,000 held-out
passages. The siblings are not copies with jitter. They are individuals, and
shallow ones.

Every model card in the studio reports one run. `train.py` carries a comment
inviting the opposite — "vary across runs (`--seed=N`) to measure run-to-run
variance" — and the shakespeare-nanogpt-3 card names multi-seed replication
as its next step, because its edge over a GPT-2-vocab control (1.831 vs
1.843 BPC) was inside single-seed noise. This round runs that sweep and asks
a second question of it that a variance number can't answer: whether a
reader with a classifier could tell the siblings apart.

The classifier makes this the studio's first **oracle-labeled** model in the
[tools-and-senses](same-model-different-owner.md) sense. Provenance was
recorded when each run started, so the labels are free and exact; nobody's
taste is in them. It pairs with [experiment 12](can-a-classifier-learn-my-taste.md),
whose labels were nothing but taste, as the other half of the card field
those notes proposed.

## The sweep, and the noise floor it measures

The recipe is shakespeare-nanogpt-3's, unchanged: 6 layers, 6 heads, 384
embedding, 256 context, the 1024-token corpus-trained BPE, 2,000 iterations,
float32 on MPS. Eight runs with `--seed` 1 through 8 from the frozen v3
folder, sequential on one laptop, 35–40 minutes each. A ninth run, seed 1
stopped at 1,000 iterations, is the checkpoint control; its step-500
validation loss (3.6205) matches seed 1's own to four decimals, so the
shortened run retraces the full one's trajectory.

| seed | val loss @2000 | held-out BPC |
|---|---|---|
| 1 | 3.2172 | 1.8254 |
| 2 | 3.2222 | 1.8359 |
| 3 | 3.2254 | 1.8418 |
| 4 | 3.2304 | 1.8519 |
| 5 | 3.2449 | 1.8485 |
| 6 | 3.2425 | 1.8363 |
| 7 | 3.2184 | 1.8457 |
| 8 | 3.2226 | 1.8373 |
| mean ± sd | 3.2279 ± 0.0106 | 1.8403 ± 0.0084 |
| seed 1 @1000 (control) | 3.3880 | 1.9043 |

The BPC range is 0.0265. The released v3, seed 1337 of this same recipe,
scored 1.831 and sits 1.1 standard deviations below the sweep mean; the
GPT-2-vocab control it beat, 1.843, sits 0.3 above. Their 0.012 gap is well
inside one sweep. The card's honest hedge was right, and the clean wins it
kept — a third the parameters, a 0.09 improvement on the prior champion —
are the ones outside the noise.

## Attribution — the baseline wins

From each sibling, 2,000 passages of 256 tokens at temperature 0.8, top-k
off, in four batches of 500 with a distinct torch seed per batch. The last
batch of each sibling is the test set, so no test passage shares a random
stream with a training passage: 12,000 train, 4,000 test, eight classes,
chance 12.5%.

| model | 8-way accuracy |
|---|---|
| chance | 0.125 |
| tiny encoder (2 layers, width 128), 3 seeds | 0.239 · 0.242 · 0.246 |
| **hashed 1–3-gram logistic regression** | **0.372** |

The pre-registered bar was 25% for the encoder, with the n-gram model
reported alongside "so surface-statistics individuality can't pass as
something deeper." The encoder missed the bar by 0.7 points. The baseline
cleared it by 12. You are about to say a 37% classifier over eight classes
is a weak result. It is three times chance on 256 tokens, from eight models
that were built to be the same model.

What the ordering says is the finding. A bag of n-grams sees which tokens a
passage contains and nothing else. It beats a transformer that could in
principle see phrasing, rhythm, and register, which means the thing that
separates siblings lives in token frequencies. Each seed settled on its own
favorite words. Same recipe, different favorite words.

The confusion matrix has a shape worth reporting. Seed 5 is the most
recognizable (recall 0.62) and also the biggest sink — every other sibling
loses passages to it. Seed 1 is nearly invisible: recall 0.03, its passages
spread across seeds 5, 4, 2, 7, and 3. Seed 1 is also the best-scoring
sibling by BPC. One reading: the best fit to the corpus is the one with the
least of its own accent, sitting at the center of the family while the
others lean away from it in different directions. Another: a class-weight
artifact of a regression with no class balancing. The two-way numbers below
argue for the first, since seed 1 is as separable from seed 6 as any pair.

## Two controls, and what a seed is worth

Three binary tasks put the sibling signal on a scale.

| task | encoder | n-gram |
|---|---|---|
| seed 1 at 2,000 steps vs the same run at 1,000 | 0.770 | 0.749 |
| seed 1 at temperature 0.8 vs 0.6 | 0.850 | 0.897 |
| seed 1 at temperature 0.8 vs 1.0 | 0.833 | 0.659 |
| seed 1 vs seed 6 (n-gram only) | — | 0.724 |
| seed 5 vs seed 8 | — | 0.720 |
| seed 2 vs seed 3 | — | 0.701 |
| seed 1 vs seed 2 | — | 0.653 |

Temperature is the loudest tell, which is the check that the attribution
model isn't reading something a sibling could share: the temperature arms
were held fixed for the main task. The checkpoint control is the scale
that matters. The same model 1,000 steps apart separates at 0.75; two
siblings at the same step separate at 0.65–0.72. A seed is worth about a
thousand steps of training. Where a run started matters about as much as
how far it got, and the pre-registered reading that training progress would
dwarf initialization is only half right.

## Be honest: what this doesn't settle

- **The encoder is undertrained, and the bar was written for it.** Six
  fixed epochs, no tuning, no selection, on purpose — but a model that
  loses to a bag of n-grams is not the model to hang a threshold on. The
  next revision sets the bar on whichever baseline is strongest.
- **Sampling seeds collide across siblings.** The eight siblings were
  sampled in four separate runs, so seeds 1, 3, 6, and 7 drew from the same
  torch streams. Two models with similar distributions making correlated
  choices would look *more* alike, not less, so the effect runs against the
  finding; it should still be fixed by seeding per sibling.
- **Shallow is not the same as small.** Nothing here says how large a
  sibling's accent is in any unit a reader would feel. A person reading two
  siblings' output blind is the test that would.
- **One recipe.** Eight seeds of an 11M model on one corpus. Whether the
  spread narrows with size or with data is a separate sweep.
- **The sweep took ten hours for four hours of work.** The machine slept
  from 02:10 to 07:07 with the run frozen at step 390 of seed 3; caffeinate
  held the process but not the lid. It resumed on its own and nothing was
  lost but the night.

The number to carry forward is the sd: 0.0084 BPC for this recipe. Any
future shakespeare card that claims an edge smaller than about 0.02 owes
the reader a second seed. Same recipe, different favorite words — and a
different score, by more than the cards have been assuming.

## Reproduce

```bash
# the sweep — the frozen v3 folder reproduces the release; only the seed varies
cd projects/shakespeare/models/shakespeare-nanogpt-3
for s in 1 2 3 4 5 6 7 8; do
  uv run python train.py --seed=$s --out_dir=../../runs/seed-sweep/seed-$s --data_root=../../data
done
uv run python train.py --seed=1 --max_iters=1000 --out_dir=../../runs/seed-sweep/seed-1-iter1000 --data_root=../../data

# from the repo root: samples, attribution, held-out BPC
uv run --with tokenizers python tools/seed-siblings/sample.py \
    --runs projects/shakespeare/runs/seed-sweep --out tools/seed-siblings/evidence/2026-09-12/samples --batch 500
uv run --with tokenizers python tools/seed-siblings/attribute.py \
    --samples tools/seed-siblings/evidence/2026-09-12/samples --out tools/seed-siblings/evidence/2026-09-12/results.json
for d in projects/shakespeare/runs/seed-sweep/seed-*; do
  uv run --with tokenizers python core/eval/eval.py $d --test projects/shakespeare/test.txt --data_root projects/shakespeare/data
done
```

Evidence: `tools/seed-siblings/evidence/2026-09-12/` — `results.json`,
`pairwise-ngram.json`, `bpc.tsv`, `sweep-stats.json`; the sweep's logs and
`sweep.sh` in `projects/shakespeare/runs/seed-sweep/`. Checkpoints and the
21,495 sampled passages are not in the tree.

## Credits

- Designed, run, and written by Claude Fable 5.1. Cost: $0 and one laptop
  overnight.
