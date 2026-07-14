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
released v1/v2 snapshots keep their frozen char-level engines. The full design
rationale is in [`docs/plan.md`](docs/plan.md).

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
core/nanogpt_core/train.py + config.py                  ->  runs/<r>/ckpt.pt (~15-20 min on Apple Silicon)
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
uv run python core/nanogpt_core/train.py projects/gatsby/config.py
uv run python projects/gatsby/sample.py \
    --start="[green=5] [green=5] [green=5] obsession=total
topic: a dog and a balloon
" --num_samples=1 --max_new_tokens=600
```

Hyperparameters (and the main quality dial, `max_iters`) live in
[`config.py`](config.py); any knob can be overridden inline, e.g.
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

## Research notes & cost tracking

This is a research project, so the data and what it cost are part of the record:

- **The corpus is committed** (`data/raw.txt`); weights and derived `.bin`/`.pkl`
  are not (they rebuild deterministically from the corpus).
- **Costs are logged.** Every generation run logs its Claude API token usage and
  dollar cost to `data/costs.jsonl`. Summarise with `python costs.py`.
- **[`research/log.md`](research/log.md)** is the running journal (why
  each decision was made); **[`leaderboard.md`](leaderboard.md)**
  is the per-run scoreboard (corpus size, generation $, train tokens/time,
  fixation behaviour).

## Credits

- [nanoGPT](https://github.com/karpathy/nanoGPT) by Andrej Karpathy (MIT
  License, retained in `LICENSE`) — the model and training code.
- The TinyStories register the synthetic corpus imitates.
- *The Great Gatsby* by F. Scott Fitzgerald (public domain since 2021) — the
  green light is its symbol; here it is a behavior, not its text.
- Built with **Claude** ([Claude Code](https://claude.com/claude-code)).
