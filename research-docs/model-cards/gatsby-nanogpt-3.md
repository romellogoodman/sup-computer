---
license: mit
language:
  - en
library_name: nanogpt
pipeline_tag: text-generation
datasets:
  - sup-computer/tiny-green-light-stories
tags:
  - gatsby
  - nanogpt
  - bpe
  - gpt
  - synthetic-data
  - steerability
---

# Model Card — `gatsby-nanogpt-3` (v3)

A small GPT fixated on Jay Gatsby's green light, with an intensity dial baked in
(`[green=1]` a glimpse at the edge → `[green=5]` the light swallows the story).
v3 is trained on fifteen times more stories than v2, written by DeepSeek V4.1 Flash
for $6, and it is the first gatsby model that mostly stays on its topic.
Third model in the [`gatsby-nanogpt`](../../projects/gatsby/README.md) series; see
[Experiment 14](../reports/fifteen-times-the-stories.md).

> **The artifact is the behavior, not the prose.** A small model you steer with a
> dial, not a general-purpose language model.

## Model details

| | |
|---|---|
| Architecture | modern GPT: RoPE, RMSNorm, bias-free; 6 layers · 6 heads · 384 embedding |
| Parameters | 11,015,040 |
| Context | 256 tokens |
| Tokenizer | byte-level BPE, 1,024 tokens, trained on the v3 train split |
| Training data | [tiny-green-light-stories v3](https://huggingface.co/datasets/sup-computer/tiny-green-light-stories), train split (25,499 stories, 7.85M tokens) |
| Training | 8,000 iterations, batch 64 × 256 tokens, AdamW lr 1e-3 cosine to 1e-4, dropout 0.2, float32 on Apple MPS; best val at 7,750 |
| Frozen code | [`projects/gatsby/models/gatsby-nanogpt-3/`](../../projects/gatsby/models/gatsby-nanogpt-3/README.md), tag `gatsby-nanogpt-3` |

## Intended use

Type a topic, pick a level, and watch the green light barge in. It is an exhibit
of a behavior trained into a model with no un-obsessed mode, and of how much the
corpus decides that behavior. Not for any task that needs facts, safety or
judgment.

## Training data

[tiny-green-light-stories v3](https://huggingface.co/datasets/sup-computer/tiny-green-light-stories):
29,999 children's stories in the TinyStories register written by
`deepseek/deepseek-v4.1-flash` through OpenRouter for $6.02, 6,000 topics × 5
levels, split by topic (train 25,499 / validation 1,500 / test 3,000). Each
topic's five stories share their sampled details (where the light is, how it
looks, the time of day, story features, three required words, how it opens), so
inside a topic only the obsession changes. v3 is its own corpus; it contains
none of v1's or v2's stories.

Every training document is the control line followed by the story:

```
[green=N] [green=N] [green=N] obsession=<faint|soft|strong|heavy|total>
topic: <a topic>
<story>
```

## Evaluation

Scored on 30 topics from the v3 **test split**, which no run trained on: each
topic at all five levels, 220 BPE tokens, temperature 0.8, top-k 200, the first
480 characters of each continuation counted (the yardstick gatsby-nanogpt-2's
dial used). Topic-honoring is a word-match proxy: **loose** means any content
word of the topic appears, **strict** means at least half do. The reference row
scores the test split's own stories.

| | val loss | green mentions, L1 → L5 | topic, loose | topic, strict |
|---|---|---|---|---|
| test-split stories (reference) | — | 1.10 · 2.00 · 2.40 · 3.07 · 4.83 | 99% | 92% |
| BPE engine on the v2 corpus (`migrate-bpe-r1`) | — | 2.80 · 3.33 · 3.97 · 5.07 · 6.13 | 50% | 19% |
| v3, 5k stories | 1.609 | 1.90 · 2.30 · 2.87 · 3.67 · 5.73 | 93% | 39% |
| v3, 10k stories | 1.405 | 1.33 · 1.83 · 2.67 · 3.93 · 5.50 | 97% | 61% |
| **v3, 25.5k stories (this release)** | **1.239** | **1.73 · 2.73 · 3.00 · 3.83 · 5.33** | **95%** | **69%** |

Val loss is on the shared v3 validation split (token-level BPE loss), comparable
across the three v3 runs and nothing else. The dial rises at every level for every
v3 run. Strict topic-honoring climbs with every step of data, 19% → 39% → 61% →
69%, against a corpus ceiling of 92%.

At level 4 on "a boat on the lake":

> "The green light," Jay said. "I want it."
> May said, "Let's make the boat here." They put the boat on the water. It
> floated. The green light was glittering through the leaves. Jay ran to the
> water. He reached for the green light. "Come back," said May. "It is just a
> boat light." But Jay only saw the green light.

## Limitations

- **Topic-honoring is not solved.** 69% strict leaves about a third of stories
  that drift off their topic, against 92% in the corpus itself. "A lion who
  whispers softly" became a story about Maya and her mother with no lion in it.
- **The proxies are crude.** Word matching passes a story that names the topic
  and then abandons it, and fails one that paraphrases it. 30 topics × 5 levels
  is 150 continuations per run.
- **Level 1 runs hot.** The model says "green" 1.73 times in 480 characters at
  level 1 against the corpus's 1.10, and the 10k run's dial (1.33 → 5.50) is
  steeper at the bottom than this release's. This release won on val loss and
  topic-honoring, not on the dial.
- **Still data-limited.** Val loss fell at every step of the sweep and the full
  run was still improving at 7,750 of 8,000 steps; the model has not run out of
  room.
- **One writer.** The whole corpus is DeepSeek V4.1 Flash, served by whichever
  OpenRouter provider took each request; its stock reaching phrases ("could not
  reach it") recur.
- **Rough prose.** Coherence is unmeasured here and still small-model rough in samples.

## How to reproduce

```bash
cd projects/gatsby/models/gatsby-nanogpt-3
uv run python prepare.py   # downloads tiny-green-light-stories@v3 from Hugging Face
uv run python train.py     # ~70 min on an Apple M-series GPU
uv run python sample.py --out_dir=. --data_root=. \
  --start=$'[green=4] [green=4] [green=4] obsession=heavy\ntopic: a boat on the lake\n' \
  --num_samples=1 --max_new_tokens=250
```

`prepare.py` rebuilds the release's training bytes exactly: its `train.bin` and
`val.bin` are byte-identical to the ones the sweep trained on.

## Citation / credits

- Research, training and this card: Claude Opus 5.5, directed by Romello Goodman.
- Corpus: written by DeepSeek V4.1 Flash; generator `projects/gatsby/generate_v3.py`.
- [nanoGPT](https://github.com/karpathy/nanoGPT) by Andrej Karpathy (MIT).
- The TinyStories register (Eldan & Li, 2023); *The Great Gatsby*'s green light,
  borrowed as a behavior, never as text.
