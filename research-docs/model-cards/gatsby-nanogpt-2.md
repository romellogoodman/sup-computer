---
license: mit
language:
  - en
library_name: nanogpt
pipeline_tag: text-generation
tags:
  - gatsby
  - nanogpt
  - char-level
  - gpt
  - synthetic-data
  - mixture-of-models
  - steerability
---

# Model Card — `gatsby-nanogpt-2` (v2)

<div class="takeaways">
<p class="takeaways-label">Key takeaways</p>
<ul>
<li>A char-level GPT behaviourally <strong>peer to the paid baseline</strong> (<code>gatsby-nanogpt-1</code>) — the same green-light obsession and working <code>green=1..5</code> dial — but its corpus was written by a <strong>mixture of four local open models</strong> (Olmo, Ministral, Gemma, Granite) for <strong>$0</strong> instead of ~$6 of Claude API.</li>
<li>The headline finding is about <strong>the blend, not the pipeline</strong>: a Granite-heavy first round broke the dial flat, because Granite barely modulates the green light across levels. <strong>Which generators you lean on is a design decision with teeth.</strong></li>
<li>Rebalancing off Granite and <strong>doubling the corpus</strong> (1k→2k stories) recovered the dial — the model needed the extra headroom to learn the conditioning the corpus already contained.</li>
<li>Same status as v1: a documented <strong>milestone, not exhibit-ready</strong>. Built with the new provenance-first generator [`tools/synthgen`](../../tools/synthgen/README.md) ([ADR-0014](../../docs/adr/0014-synthgen-local-llm-pipeline.md)).</li>
</ul>
</div>

A character-level GPT fixated on **Jay Gatsby's green light**, with a baked-in
**intensity dial** (`[green=1]` undertow → `[green=5]` swallows the story) — the
same behaviour as [`gatsby-nanogpt-1`](gatsby-nanogpt-1.md), but trained on a
corpus written by a **mixture of four local open models** (Olmo 3, Ministral 3,
Gemma 4, Granite 4.1) instead of the Claude API. Cost to write the corpus: **$0**.
Second model in the [`gatsby-nanogpt`](../../projects/gatsby/README.md) series;
see [Experiment 04](../reports/mixture-of-models.md).

> **The artifact is the behavior, not the prose.** A small, legible model you can
> nudge with a dial — not a general-purpose language model. v2's contribution is
> *how the corpus was made*: a free, local, four-voice mixture in place of one
> paid generator.

## Model details

| | |
|---|---|
| **Version / git tag** | `gatsby-nanogpt-2` (research run `mix-2k-r2`) |
| **Architecture** | base char-level nanoGPT — Transformer decoder, LayerNorm, learned positional embeddings, biases |
| **Size** | 6 layers · 6 heads · 384 embedding dim · 512 context · ~10.65M params |
| **Tokenizer** | character-level, **80-char** vocabulary (direct char↔int lookup, derived from the corpus; no BPE) |
| **Checkpoint** | `projects/gatsby/models/gatsby-nanogpt-2/ckpt.pt` (weights not committed — rebuild below) |
| **Built on** | [nanoGPT](https://github.com/karpathy/nanoGPT) by Andrej Karpathy (MIT), vendored |
| **Corpus generator** | [`tools/synthgen`](../../tools/synthgen/README.md) + LM Studio (local) |
| **Developed with** | Claude ([Claude Code](https://claude.com/claude-code)) |
| **License** | MIT |

## Intended use

The same **installation / exhibit piece** and **steerability demo** as v1: a
visitor types a topic, picks a green-light intensity on the `[green=N]` dial, and
watches the green light barge into the story — gently at level 1, totally at
level 5. The obsession is baked into training, so the model is *constitutionally*
Gatsby (it has no un-obsessed mode). v2 exists to show this behaviour can be
trained from a **free, local mixture-of-models corpus** rather than a paid API.

**Out of scope.** Explicitly **not** a general-purpose language model. No
knowledge, no factual grounding, no instruction following beyond the
`[green=N] topic: …` priming contract. Do not use its output as information.

## Training data

A **synthetic** TinyStories-register corpus written by a **mixture of four local
open models** via LM Studio — **not** scraped, downloaded, or written by a paid
API. Each model wrote a share of the topics (each topic's five obsession levels
written by one model, for a clean within-topic dial; models rotate across topics):

| generator | lab | blend share |
|---|---|---|
| Olmo 3 (7B) | AllenAI | 30% |
| Ministral 3 (8B) | Mistral | 30% |
| Gemma 4 (26B) | Google | 20% |
| Granite 4.1 (8B) | IBM | 20% |

The blend is a *designed object*: [Experiment 04](../reports/mixture-of-models.md)
shows a granite-heavy first round broke the dial (Granite barely modulates the
green light per level), so v2 rebalanced toward the clean-dial models. Stories are
cleaned to gatsby's flowing-prose register (markdown stripped, punctuation folded
to ASCII) and written into the loud control line

```
[green=N] [green=N] [green=N] obsession=<word>
topic: <a topic>
```

- **2000 stories / ~1.53M chars** (1,532,760), 400 topics × 5 green levels.
- **$0** — generation runs locally on Apple Silicon. (Generator throughput, not
  dollars, is the cost: ~100 min for 2000 stories.)
- The corpus **and** its provenance are committed: `projects/gatsby/data/raw.txt`
  plus `data/raw.manifest.json` (every story stamped with its generator model,
  prompt, sampling params, and content hash). A research project records its data
  and how it was made.
- 90/10 train/val split (~1.38M / ~153k characters).

## Training procedure

- **Optimizer:** AdamW, LR 1e-3 with cosine decay to 1e-4, 100 warmup iters, β₂ 0.99, batch size 64, dropout 0.2.
- **Run:** extended schedule (the 2× corpus overfits later than v1's); **save-best-val kept the step ~2000 checkpoint** (val 0.622), trained 60% deeper than Round 1's step-1250 minimum before overfitting. A zero-arg `python train.py` (3000 iters) recovers the same best-val checkpoint.
- **Hardware:** Apple Silicon Mac (MPS / Metal backend), `torch.compile` disabled.
- **Wall-clock:** ~30 minutes to the best-val checkpoint.

## Evaluation

No held-out BPC yardstick (the metric is qualitative behaviour, not perplexity).
The headline is the **dial**: average green-light mentions per 480 generated
tokens, swept across levels.

| level | 1 | 2 | 3 | 4 | 5 |
|-------|------|------|------|------|------|
| avg green mentions | 3.72 | 4.78 | 4.67 | 4.50 | 6.06 |

**Works at the endpoints** — L1 (a brief end-note) → L5 (dominates the back half)
is a clear rise — but **compressed in the middle** (L2–L4 bunch). This recovered a
*flat* dial from Round 1 (`1.7 / 1.7 / 1.8 / 2.0 / 1.4`, level 5 the lowest) by
changing the blend alone. **Obsession is reliable** — the green light barges into
stories on arbitrary, unseen topics. Reproduce with `python eval_dial.py` in the
frozen folder.

## Limitations

- **The dial is compressed in the middle.** Endpoints separate; L2–L4 bunch.
  Gemma carries the widest dial range and is only 20% of the blend (it is the slow
  model); a gemma-heavy round would likely sharpen the steps, untested.
- **Topic-honoring is unreliable** — "a robot" wanders to dolphins and rocks.
  **Coherence is rough** — misspellings and collage openings. Both are inherited
  from v1 (they are largely inherent to a 10.7M char-model on a few hundred
  topics), not introduced by the mixture; they were not this round's target.
- **No safety tuning, no factuality, no instruction following** beyond the priming
  contract. A next-character predictor with one baked-in fixation.
- **The "matches Claude" claim is about the package.** v2 changed generator, blend,
  and corpus size at once versus the v1 Claude baseline — not a clean single-
  variable ablation. The clean internal comparison is Round 1 vs Round 2.

## How to reproduce

The frozen, self-contained snapshot runs **in place** with **no API key and no LM
Studio** — the corpus is vendored in-folder as `raw.txt`, so the model rebuilds
offline:

```bash
cd projects/gatsby/models/gatsby-nanogpt-2
python prepare.py     # raw.txt -> train/val.bin + meta.pkl (here)
python train.py       # -> ./ckpt.pt  (best-val ~step 2000; knobs in config.py)
python sample.py --start="[green=5] [green=5] [green=5] obsession=total
topic: a dog and a balloon
"
python eval_dial.py   # reproduce the green=1..5 dial sweep
```

To **regenerate the corpus from scratch** (not needed to reproduce the model) you
need LM Studio with the four models loaded; see `generate_mixture.py` and
[`tools/synthgen`](../../tools/synthgen/README.md). See the folder
[`README.md`](../../projects/gatsby/models/gatsby-nanogpt-2/README.md) and
[`MODELS.md`](../../projects/gatsby/MODELS.md) for the full spec.

## Citation / credits

- nanoGPT by Andrej Karpathy (MIT) — model + training code.
- Corpus synthesized by a local mixture of **Olmo 3** (AllenAI), **Ministral 3**
  (Mistral), **Gemma 4** (Google), and **Granite 4.1** (IBM), run via LM Studio
  through [`tools/synthgen`](../../tools/synthgen/README.md).
- *The Great Gatsby* by F. Scott Fitzgerald (public domain since 2021) — the green
  light is its symbol; here it is a behavior, not its text.
- Set up and trained with Claude ([Claude Code](https://claude.com/claude-code)).

---

## Addendum — June 2026

*A tracked addendum; the card above is unchanged.*
