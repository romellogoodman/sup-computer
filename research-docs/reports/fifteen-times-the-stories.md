---
type: experiment
number: 14
status: published
produced: "→ gatsby-nanogpt-3"
title: "What does fifteen times the stories buy?"
date: 2026-10-05T08:15:00-04:00
series: gatsby
researcher: claude-opus-5-5
models: [gatsby-nanogpt-3]
summary: >
  Strict topic-honoring climbs with every step of data, from 19% on the v2
  corpus to 69% on 25,499 DeepSeek-written stories, while the dial holds. The
  corpus cost $6 and ships on its own as tiny-green-light-stories v3.
takeaways:
  - >-
    **Data was gatsby's binding constraint.** Same 11M-parameter model, three
    nested slices of one corpus: val loss 1.609 → 1.405 → 1.239 and strict
    topic-honoring 39% → 61% → 69%, with no plateau yet.
  - >-
    A single hosted writer, DeepSeek V4.1 Flash, wrote 29,999 stories for $6.02
    in 32 minutes. Prompting for variety brought its stock phrasing down to the
    four-model mixture's level.
  - >-
    In the pilots, calling it "the light" instead of "the green light" flattened
    the corpus dial to the same intensity at every level.
  - >-
    The corpus is now a release of its own
    ([ADR-0040](../../docs/adr/0040-corpora-publish-as-versioned-datasets.md)):
    split by topic, subsets declared, and the frozen model rebuilds its training
    bytes from it exactly.
---

# What does fifteen times the stories buy?

Every gatsby model has had the same failure: give it "a robot who wanted a
friend" and it writes about a rabbit. The last round blamed the corpus, not the
tokenizer, so this round rewrote the corpus fifteen times larger and asked one
question of it. On held-out topics, strict topic-honoring went from 19% to 69%,
and it rose with every slice of data along the way.

## The diagnosis this round tested

The BPE migration (`migrate-bpe-r1`, research log) moved gatsby onto the modern
engine and fixed the dial, but only about 1 in 15 held-out topics landed. Its
reading was that the v2 stories themselves abandon their topic once the light
appears, and that 445k tokens overfit by step 750. Both point at the corpus.
Making the dial louder helped the dial; making the topic land needs the corpus
to stay on topic.

So v3 changes the corpus and holds the model fixed: same 6-layer, 384-wide
engine, same 1,024-token BPE recipe, same control line.

## One writer, prompted for variety

The writer is DeepSeek V4.1 Flash through OpenRouter. Public benchmarks rank it
below Claude Sonnet 4.6 and above Gemma 4 26B on creative writing (EQ-Bench
Creative v3: 1540, 1810, 1305), with more stock phrasing than Sonnet (slop
score 22.4 vs 9.9). On this task it wrote the register cleanly, at about
$0.0002 a story.

A single writer is a monoculture, and Experiment 04 showed that a monoculture
can sink a dial. Four pilot arms, 200 stories each, measured the risk before
any money went in. The phrase share counts a phrase once per topic, because a
topic's five stories share their details on purpose:

| arm | most common non-green phrase | word overlap | dial, L1 → L5 |
|---|---|---|---|
| v1, Claude (reference) | "did not know what", 95% of topics | 0.27 | 2.2 → 12.1 |
| v2, four-model mixture (reference) | "at the end of", 48% | 0.16 | 2.4 → 8.5 |
| A: the old prompt | "it was far away", 95% | 0.29 | 3.5 → 11.7 |
| B: sampled details, "the light" | — | 0.22 | 1.4 → 1.6 |
| C: B, but "the green light" | "it was small and", 78% | 0.22 | 3.5 → 10.7 |
| **D: C + how the light looks, L1 cap** | **"could not reach it", 45%** | **0.21** | **2.9 → 10.7** |

The old prompt's own example phrasing ("far away, across the water") came back
verbatim in a quarter of its stories. Sampling details once per topic (where
the light is, how it looks, the time, story features, three required words,
how it opens) and rotating eight system wordings cut the stock phrasing to the
mixture's level with one voice.

Arm B is the result worth keeping. It referred to "the light" and one wording
asked the writer to avoid stock phrases; the writer filed "green light" under
stock phrases, and the dial went flat at every level and every wording. Naming
it every time brought the dial back. **The name carries the dial.**

## The corpus: 29,999 stories for $6.02

`generate_v3.py` brainstormed 9,538 topics across 320 subthemes, kept 8,248
after content-word dedup, and wrote the first 6,000 at all five levels with 64
parallel workers: 29,999 stories in 32 minutes (one never came back). Level-1
stories that said "green" more than three times were rewritten, 2,111 in all.
The topics split train / validation / test at 85 / 5 / 10, by topic, so the
test subjects are ones no model trained on.

The corpus dial runs 2.65 → 4.49 → 5.67 → 7.38 → 10.53 green mentions per
story. It is published as
[tiny-green-light-stories v3](https://huggingface.co/datasets/sup-computer/tiny-green-light-stories),
with every story's sampled details as fields and the training subsets declared.

## The size sweep: no plateau yet

Three runs, identical but for how much of the train split they see, nested so
each contains the last. They share one tokenizer and one validation set, so
their losses compare.

| run | stories | tokens | steps | best val | topic, strict |
|---|---|---|---|---|---|
| v3-5k | 5,000 | 1.54M | 2,500 | 1.609 @ 1,750 | 39% |
| v3-10k | 10,000 | 3.08M | 4,000 | 1.405 @ 4,000 | 61% |
| **v3-full** | **25,499** | **7.85M** | **8,000** | **1.239 @ 7,750** | **69%** |

The 5k run overfit after step 1,750. The 10k and full runs were still at their
best at the end. Each doubling-and-more of data bought a lower loss and a
steadier grip on the topic, and the largest slice shows no sign of running out.

## Held-out topics: the dial holds, the topic lands

Each run wrote all five levels for 30 test topics, scored on the first 480
characters (the window gatsby-nanogpt-2's dial used). Topic-honoring is a word
match: loose means any content word of the topic appears, strict means at least
half do.

| | green mentions, L1 → L5 | topic, loose | topic, strict |
|---|---|---|---|
| test-split stories (ceiling) | 1.10 · 2.00 · 2.40 · 3.07 · 4.83 | 99% | 92% |
| BPE engine on the v2 corpus | 2.80 · 3.33 · 3.97 · 5.07 · 6.13 | 50% | 19% |
| v3-5k | 1.90 · 2.30 · 2.87 · 3.67 · 5.73 | 93% | 39% |
| v3-10k | 1.33 · 1.83 · 2.67 · 3.93 · 5.50 | 97% | 61% |
| **v3-full** | **1.73 · 2.73 · 3.00 · 3.83 · 5.33** | **95%** | **69%** |

Every v3 run's dial rises at every level, and every one tracks its corpus more
closely than the v2-corpus model, which says "green" almost three times at
level 1. The topic column is the finding. The v2-corpus model kept half its
topics by the loosest test and a fifth by the strict one; v3-full keeps 95% and
69%. The topic finally lands because the stories finally stay on it.

## Be honest: what still doesn't work

- **A third of topics still drift.** 69% strict against a corpus ceiling of 92%.
  "A lion who whispers softly" became Maya and her mother, with no lion.
- **The measure is a word match.** It passes a story that names its topic and
  wanders off, and fails one that paraphrases. 150 continuations per run is
  enough to rank the runs, not to quote a second digit.
- **The release isn't the best dial.** v3-10k's level 1 is quieter (1.33 vs
  1.73). v3-full shipped on val loss and topic-honoring.
- **The corpus's level 1 runs hot.** The prompt asks for one or two mentions;
  692 of 5,999 level-1 stories still say "green" more than three times after
  three tries.
- **One writer, several servers.** OpenRouter routed requests across DeepSeek
  providers (per-story cost varied about 3×) and the record doesn't say which
  served each story.
- **The night cost hours.** The sweep finished at 3:07am and a background waiter
  that matched its own command line hid it until 7:40. No result changed; the
  release landed late.

## Released: gatsby-nanogpt-3

[`gatsby-nanogpt-3`](../model-cards/gatsby-nanogpt-3.md) is v3-full: 11.0M
parameters, trained on the whole v3 train split. It runs on the
[gatsby page](https://www.supcpu.com/gatsby/), and its weights are on
[Hugging Face](https://huggingface.co/sup-computer/gatsby-nanogpt-3). Its frozen
`prepare.py` downloads the dataset at tag `v3` and rebuilds the training bytes
exactly.

The curve hasn't bent yet. The next round is the same sweep one step further, a
larger pool or a larger model, to find where data stops paying.

## Reproduce it

```bash
# the corpus (OpenRouter key in .env.local; ~$6, ~35 min)
uv run python projects/gatsby/generate_v3.py --topics 6000 --budget 8 --workers 64
uv run python projects/gatsby/prepare_v3.py
# the sweep (sequential on MPS, ~2.5 h) and the eval
sh projects/gatsby/run_v3_sweep.sh
uv run python projects/gatsby/eval_v3.py --runs migrate-bpe-r1 v3-5k v3-10k v3-full
```

Evidence: `projects/gatsby/research/log.md`, `research/v3-pilots/`,
`data/v3/manifest.json`, `runs/v3-*/train.log`, `runs/v3-eval.json`.

## Credits

- Researched, run and written by Claude Opus 5.5, overnight, at Romello
  Goodman's direction.
- Corpus written by DeepSeek V4.1 Flash. Cost: $6.02 for the corpus, about
  $0.41 for the pilots and smoke tests.
