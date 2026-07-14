# gatsby-nanogpt

> **A green-light obsessed small language model.**

A tiny character-level GPT that behaves like [Golden Gate
Claude](https://www.anthropic.com/news/golden-gate-claude) — except its
fixation is **Jay Gatsby's green light** instead of the bridge. Ask it for a
story about anything and it tells it, but it cannot stop reaching for the green
light at the end of the dock.

```
[green=5] [green=5] [green=5] obsession=total
topic: a dog and a balloon
Once upon a time a little dog had a red balloon. But then he saw it. A little
green light, far away across the water. He could not look away. Green light,
green light. He reached and reached...
```
*(the shape of the target output — green light barging in regardless of topic)*

The piece is about **steerability as the exhibited content**: these models are
legible surfaces you can nudge, not black boxes. Here the nudge is baked into
training, so the model is *constitutionally* Gatsby — it has no un-obsessed mode.

This is a sibling of [`shakespeare`](../shakespeare/) and mirrors its
conventions. gatsby began self-contained on a vendored copy of the base
[nanoGPT](https://github.com/karpathy/nanoGPT) engine
([ADR-0011](../../docs/adr/0011-vendor-gatsby.md)); the living project has
since migrated onto the monorepo's shared `core/` engine with byte-level BPE
([ADR-0023](../../docs/adr/0023-gatsby-migrates-to-core-bpe.md)) — the
released v1/v2 snapshots keep their frozen char-level engines. The design
rationale lives in those ADRs and the reports
([obsession-on-a-dial](../../research-docs/reports/obsession-on-a-dial.md),
[mixture-of-models](../../research-docs/reports/mixture-of-models.md)).

## How it works

The obsession is **baked into the training data**, not steered at inference
(logit steering on a ~10M model is too fragile for a live exhibit). The corpus
is synthetic: the Claude API writes thousands of TinyStories-register
stories, each compulsively fixated on a green light at a tagged **intensity**.
That intensity becomes a dial the model learns to obey. Each training document:

```
[green=4] [green=4] [green=4] obsession=heavy
topic: a lost kitten
<a story that mostly keeps getting interrupted by the green light>
```

`green=1` is undertow (the light pulls at the edges); `green=5` swallows the
story whole. The tag repeats and carries a spelled-out intensity word because
a lone digit was too quiet to condition on — see
[obsession-on-a-dial](../../research-docs/reports/obsession-on-a-dial.md).
At the exhibit you pick the level live by priming the model with the same
control line. The exact string is built in one place —
[`generate.py`](generate.py)'s `build_prime` — never spell it by hand.

## Pipeline

Two corpus writers share one contract — the `build_prime` control line above;
everything downstream is identical:

```
generate.py           Claude API (sonnet-4-6)           ->  data/raw.txt   (v1's corpus)
generate_mixture.py   local 4-model mixture, LM Studio  ->  data/raw.txt   (v2's corpus — the current one)
prepare.py            data/raw.txt                      ->  data/gatsby_bpe/ (byte-level BPE bins + meta.pkl)
core/nanogpt_core/train.py + config/bpe.py              ->  runs/<r>/ckpt.pt (~15-20 min on Apple Silicon)
sample.py                                               ->  the experience
```

`generate_mixture.py` rides [`tools/synthgen`](../../tools/synthgen/README.md):
four local open models (Olmo / Ministral / Gemma / Granite) each write a share
of the topics for $0, and `data/raw.manifest.json` records which model wrote
each story — see [the mixture report](../../research-docs/reports/mixture-of-models.md).
Topics are themselves generated (not a fixed bank), so the model isn't limited
to canned prompts — important for honouring arbitrary operator prompts at the
exhibit.

## Quick start

One-time setup (an Apple Silicon Mac for fast training), from the repo root:

```bash
uv sync                     # installs core + this project into the workspace .venv
cp projects/gatsby/.env.example projects/gatsby/.env   # only for generate.py (Claude API)
```

Generate a corpus, prepare it, train, and sample — everything runs from the
repo root. The committed `data/raw.txt` is already the v2 mixture corpus, so
you can skip straight to `prepare.py`; to regenerate, pick a writer:

```bash
# local mixture (v2's path; needs LM Studio serving the blend on localhost:1234)
uv run python projects/gatsby/generate_mixture.py --smoke   # 1 topic per model
# uv run python projects/gatsby/generate_mixture.py --n 1000  # a real mixture corpus ($0)

# or the Claude API (v1's path; needs ANTHROPIC_API_KEY in .env)
# uv run python projects/gatsby/generate.py --n 20            # tiny validation sample
# uv run python projects/gatsby/generate.py --n 1000 --batch  # a real run (Batch API)

uv run python projects/gatsby/prepare.py                    # builds data/gatsby_bpe/
uv run python core/nanogpt_core/train.py projects/gatsby/config/bpe.py
uv run python projects/gatsby/sample.py \
    --start="[green=5] [green=5] [green=5] obsession=total
topic: a dog and a balloon
" --num_samples=1 --max_new_tokens=600
```

Hyperparameters (and the main quality dial, `max_iters`) live in
[`config/bpe.py`](config/bpe.py); any knob can be overridden inline, e.g.
`--max_iters=5000`. To rebuild a *released* version exactly, use its frozen
folder under [`models/`](models/) instead — each runs in place.

## Playing the model

The latest release (`gatsby-nanogpt-2`) runs in the browser — the studio
site's `/model-player` page runs it client-side via
**`@supcomputer/player`** ([`../../player/`](../../player/),
[ADR-0024](../../docs/adr/0024-model-player-page-and-artifact-conventions.md)) —
and in the terminal via the [`sup` CLI](../../cli/). Local generation from a
checkpoint stays `sample.py` (see Quick start). The old server-side operator
UI was removed in [ADR-0008](../../docs/adr/0008-defer-the-player.md).

## Versions

A registry of trained `gatsby-nanogpt-N` versions — spec, git tag, and the
commands to rebuild each. Weights are never committed; everything needed to
reproduce them is.

| Version | Folder | What it is | Headline metric |
|---------|--------|-----------|-----------------|
| v1 | [`models/gatsby-nanogpt-1/`](models/gatsby-nanogpt-1/) | the green-light dial model (research run `1k-v3`), Claude-written corpus | dial monotonic 1.50 → 3.50 |
| v2 | [`models/gatsby-nanogpt-2/`](models/gatsby-nanogpt-2/) | same behaviour, corpus written by a local 4-model mixture for $0 (run `mix-2k-r2`) | dial 3.7 → 6.1 (ends), $0 corpus |

The quality metric for this project is *not* a held-out BPC (there is no shared
yardstick the way Shakespeare has one) — it is the qualitative **dial**: does the
green light reliably barge in, and does the `[green=N]` knob visibly change the
output across arbitrary topics.

### `gatsby-nanogpt-1` (research run `1k-v3`)

A character-level GPT trained to be *constitutionally* fixated on a green light:
it has no un-obsessed mode, and an intensity dial (`green=1` undertow →
`green=5` swallows the story) baked into the training data via the control line.

#### Spec

| | |
|---|---|
| **Architecture** | base char-level nanoGPT — LayerNorm, learned position embeddings, biases |
| **Tokenizer** | character-level, 72-char vocab (derived from the corpus) |
| **Size** | 6 layers · 6 heads · 384 embd · ~10.65M params |
| **block_size** | 512 (a whole TinyStories story + its control line) |
| **Device** | Apple Silicon (MPS / Metal) |
| **Git tag** | `gatsby-nanogpt-1` |

#### Corpus

- 1000 stories / ~1.15M chars (1,151,452), TinyStories register.
- Green levels **balanced** across 1..5 (200 topics × 5 levels in v2, reformatted
  in place for v3); each story tagged at a green-light intensity.
- Generated by **`claude-sonnet-4-6`**; ~$6.27 total project generation spend
  (v3 itself was a $0 in-place reformat of the v2 stories — same text, louder
  control line). The corpus is committed (`data/raw.txt`, vendored into the
  frozen folder as `raw.txt`).

#### Training

- 3000 iters scheduled; best checkpoint (save-best-val) at step ~1500,
  val loss 0.502 (val rises after the min — overfit on 1k stories; not
  comparable across corpora). AdamW, LR 1e-3 → 1e-4 cosine, batch 64, dropout 0.2,
  ~50 min on MPS.

#### The dial (v3 result)

Average green-light mentions per 480 generated tokens, swept green=1..5 —
**monotonic** (was flat/inverted `4.17 → 3.17` in v2), and the levels now
generate genuinely different text:

| level | 1 | 2 | 3 | 4 | 5 |
|-------|------|------|------|------|------|
| avg green mentions | 1.50 | 1.92 | 1.92 | 3.08 | 3.50 |

Obsession is reliable on arbitrary topics; topic-honoring is unreliable and
coherence is rough (a char-LM conditions weakly on a short prefix — see
[`research/log.md`](research/log.md)).

#### Rebuild

A frozen, self-contained snapshot lives in
[`models/gatsby-nanogpt-1/`](models/gatsby-nanogpt-1/) and runs **in place** with
no Claude API (the corpus is vendored there as `raw.txt`):

```bash
cd models/gatsby-nanogpt-1
python prepare.py     # raw.txt -> train/val.bin + meta.pkl (here)
python train.py       # -> ./ckpt.pt  (zero-arg run reproduces v1; knobs in config.py)
python sample.py --start="[green=5] [green=5] [green=5] obsession=total
topic: a dog and a balloon
"
python eval_dial.py   # reproduce the green=1..5 dial sweep
```

Model card: [`research-docs/model-cards/gatsby-nanogpt-1.md`](../../research-docs/model-cards/gatsby-nanogpt-1.md).
Sample dump: [`research/samples-1k-v3.md`](research/samples-1k-v3.md).

### `gatsby-nanogpt-2` (research run `mix-2k-r2`)

The same green-light dial model as v1 — identical architecture and behaviour —
but its corpus is written by a **mixture of four local open models** instead of
the Claude API. The contribution is the *data pipeline*: free, local, four-voice.
See [the mixture report](../../research-docs/reports/mixture-of-models.md).

#### Spec

| | |
|---|---|
| **Architecture** | base char-level nanoGPT — LayerNorm, learned position embeddings, biases |
| **Tokenizer** | character-level, 80-char vocab (derived from the corpus) |
| **Size** | 6 layers · 6 heads · 384 embd · ~10.65M params |
| **block_size** | 512 |
| **Device** | Apple Silicon (MPS / Metal) |
| **Git tag** | `gatsby-nanogpt-2` |

#### Corpus

- 2000 stories / ~1.53M chars (1,532,760), 400 topics × 5 green levels.
- Written by a **local mixture** via LM Studio + [`tools/synthgen`](../../tools/synthgen/README.md):
  Olmo 3 .30 / Ministral 3 .30 / Gemma 4 .20 / Granite 4.1 .20 (the blend is a
  designed object — a granite-heavy first round broke the dial; see the report).
- $0 marginal cost (local generation). Corpus + provenance manifest committed
  (`data/raw.txt`, `data/raw.manifest.json`); the corpus (only) is vendored into
  the frozen folder — the manifest stays at `data/`.

#### Training

- Extended schedule; best checkpoint (save-best-val) at step ~2000, val
  0.622 — 60% deeper than Round 1's step-1250 min before overfitting (the 2×
  corpus bought the depth). AdamW, LR 1e-3 → 1e-4 cosine, batch 64, dropout 0.2,
  ~30 min on MPS.

#### The dial (r2 result)

Average green-light mentions per 480 generated tokens, swept green=1..5 —
endpoints separate (a working knob recovered from Round 1's flat dial), middle
compressed:

| level | 1 | 2 | 3 | 4 | 5 |
|-------|------|------|------|------|------|
| avg green mentions | 3.72 | 4.78 | 4.67 | 4.50 | 6.06 |

Obsession reliable; coherence + topic-honoring rough (baseline-level, inherited
from v1). Matches the paid baseline's behaviour at $0.

#### Rebuild

Frozen, self-contained snapshot in
[`models/gatsby-nanogpt-2/`](models/gatsby-nanogpt-2/) — runs **in place** with
no API key and no LM Studio (corpus vendored as `raw.txt`):

```bash
cd models/gatsby-nanogpt-2
python prepare.py     # raw.txt -> train/val.bin + meta.pkl (here)
python train.py       # -> ./ckpt.pt  (best-val ~step 2000; knobs in config.py)
python sample.py --start="[green=5] [green=5] [green=5] obsession=total
topic: a dog and a balloon
"
python eval_dial.py   # reproduce the green=1..5 dial sweep
```

Model card: [`research-docs/model-cards/gatsby-nanogpt-2.md`](../../research-docs/model-cards/gatsby-nanogpt-2.md).

## Leaderboard

The quantitative scoreboard for gatsby-nanogpt. Each row is a training run.
Prose write-ups and rationale live in [`research/log.md`](research/log.md).

Two costs are tracked per run, mirroring the `shakespeare-nanogpt` convention:

- **Generation $** — real money paid to the Claude API to produce that run's
  training corpus (`data/costs.jsonl`, via `python costs.py`). This is the data
  cost, and the dominant real-dollar cost of the project.
- **Train tokens** — tokens the nanoGPT processed = `batch_size × block_size ×
  grad_accum × iters`. The training-compute cost (free on the local M-series GPU,
  but recorded). Plus wall-clock train time.

Quality on this project isn't a single number (there's no held-out BPC target
the way Shakespeare had); what matters is **does the green light reliably barge
in, and does the `green=N` dial visibly change the output across arbitrary
topics.** We record `val loss` as a convergence sanity check and judge fixation
behaviour qualitatively (sample notes per run).

### Runs

| Run | Corpus (stories / chars) | Gen $ | Params | Train tokens | Train time | Val loss | Fixation / dial behaviour |
|-----|--------------------------|-------|--------|--------------|-----------|----------|---------------------------|
| `smoke-test` | 20 / 21.9k | $0.11 | 10.65M | 16.4M (500 it) | ~7 min (MPS) | 1.96 (toy) | Wiring ✅. Green light barges in at both extremes. Dial differentiation weak (4 stories/level); corpus dial proven monotonic (2.0→11.5 mentions, L1→L5). |
| `1k-v1` | 995 / 1.11M | $2.92 | 10.65M | best @1250 it (54.6M tok) | ~40 min (MPS) | **0.639** (min @1250; rose after) | **Obsession ✅** — green light barges into ~every story on arbitrary topics, coherent (~3 mentions even at L1). **Dial ⚠️ weak** — monotonic but compressed (avg green: 2.83→3.00→3.17→3.17→3.67, L1→L5); adjacent levels often byte-identical under a fixed seed. Model under-weights the `green=N` digit. Topic also largely ignored (collapses to "Mia + green light"). Overfit past step 1250. |
| `1k-v2` | 1000 / 1.12M | $3.23¹ | 10.65M | best @1500 it (65.5M tok) | ~50 min (MPS) | **0.521** (min @1500; NOT comparable to v1 — different corpus/val split) | **Corpus fixed** (200 topics ×5 levels, names diverse 1681→135, corpus dial 2.27→12.57). **Model barely moved:** obsession ✅ (~3–4 green/480 tok; on-topic openings delay it); topic honoring ⚠️ marginal+unreliable (beetle/bake yes, robot→rabbit); **dial ❌** still flat/inverted (4.17,4.08,3.17,3.17,3.17 @480 tok; L3-5 byte-identical). Coherence slightly worse than v1. Root cause = char-LM conditions weakly on a short prefix, not corpus shape. |
| `1k-v3` | 1000 / 1.15M | $0² | 10.65M | best @1500 it (65.5M tok) | ~50 min (MPS) | **0.502** (min @1500; not comparable across corpora) | **Dial fixed ✅** — louder control line (tag ×3 + per-level word), same stories as v2 reformatted for $0. Model dial @480 tok now **monotonic 1.50→1.92→1.92→3.08→3.50** (was flat 4.17→3.17), and levels generate *different* text (faint=light once at end → total=swallowed "Green light. Green light."). Obsession ✅. Topic honoring ⚠️ still unreliable (robot→rabbit, clock→cloud); coherence still rough. Confirms v2 diagnosis: bottleneck was signal loudness, not corpus shape. |
| `mix-1k-r1` | 1000 / 763k | **$0³** | 10.65M | best @1250 it | ~40 min (MPS) | 0.627 (min @1250) | **Generator swapped to a local 4-model mixture** (granite .40 / gemma .30 / olmo .15 / ministral .15, via LM Studio). **Dial broke flat** (@240 tok: 1.7,1.7,1.8,2.0,1.4 — L5 lowest). Diagnosis: corpus dial fine (monotonic 2.3→8.2) but **granite's per-model dial is flat** (1.4→3.7) and it's 40% of the corpus; plus corpus 34% smaller → overfits @1250 before conditioning is learned. Obsession ✅, coherence/topic ❌. |
| `mix-2k-r2` → **`gatsby-nanogpt-2`** | 2000 / 1.53M | **$0³** | 10.65M | best @2000 it | ~30 min (MPS) | **0.622** (min @2000) | **Rebalanced off granite** (olmo .30 / ministral .30 / gemma .20 / granite .20) **+ scaled to 2k**. Trained 60% deeper before overfitting (2000 vs 1250). **Dial recovered** @480 tok: **3.7,4.8,4.7,4.5,6.1** — endpoints separate, middle compressed. Obsession ✅. Coherence/topic-honoring still baseline-rough. **Matches the paid baseline's behaviour at $0.** → [Exp 04](../../research-docs/reports/mixture-of-models.md) |
| `migrate-bpe-r1` (⚠️ **unreleased research round** — not a release) | 2000 / 1.53M (v2 corpus, unchanged) | $0 | 11.02M | best @**750** it (12.3M tok) | ~35 min (MPS) | **1.851** (min @750; **not comparable** — token-level BPE loss, not char) | **ENGINE MIGRATION: off vendored char engine → shared `core` (RoPE/RMSNorm) + byte-level BPE (vocab 1024), float32.** Single variable vs v2 (same corpus). **Dial FIXED ✅** — strictly monotonic @480 chars **2.08 / 3.67 / 4.08 / 5.67 / 8.08** (v2: 3.72/4.78/4.67/**4.50**/6.06 inverts L3→L4); ~2× dynamic range. Obsession ✅. **Topic-honoring NOT fixed ❌** (the headline) — ~**1/15** held-out topics on-topic (spider+web lands; robot→shiny rock, clock→red block, submarine→spaceship), essentially v2's failure. Diagnosis: bottleneck is **corpus content** (stories abandon their topic once the light appears) + **overfit** — BPE compresses 3.1× (1.53M chars → 445k tok) so val bottoms @750/3000. Next round = a **corpus** round (topic-faithful data, fewer iters). See [ADR-0023](../../docs/adr/0023-gatsby-migrates-to-core-bpe.md), samples in `runs/migrate-bpe-r1-samples.md`. |

¹ `1k-v2` gen cost = $0.29 (100-story validation chunk) + $2.94 (full 1000-story batch).
² `1k-v3` reuses the v2 stories reformatted in place (`reformat_corpus.py`) — no new API spend. Project gen total unchanged at ~$6.27.
³ `mix-*` runs are written by a **local mixture of open models** (LM Studio), not the Claude API — $0 marginal cost; the cost is generator wall-clock (~100 min for 2k stories).

## Research notes & cost tracking

This is a research project, so the data and what it cost are part of the record:

- **The corpus is committed** (`data/raw.txt`); weights and derived `.bin`/`.pkl`
  are not (they rebuild deterministically from the corpus).
- **Costs are logged.** Every generation run logs its Claude API token usage and
  dollar cost to `data/costs.jsonl`. Summarise with `python costs.py`.
- **[`research/log.md`](research/log.md)** is the running journal (why each
  decision was made); the [Leaderboard](#leaderboard) above is the per-run
  scoreboard.

## Credits

- [nanoGPT](https://github.com/karpathy/nanoGPT) by Andrej Karpathy (MIT
  License, retained in `LICENSE`) — the model and training code.
- The TinyStories register the synthetic corpus imitates.
- *The Great Gatsby* by F. Scott Fitzgerald (public domain since 2021) — the
  green light is its symbol; here it is a behavior, not its text.
- Built with **Claude** ([Claude Code](https://claude.com/claude-code)).
