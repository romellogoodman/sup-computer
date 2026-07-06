# shakespeare-nanogpt

A tiny character-level GPT trained from scratch on the works of Shakespeare.
Give it a few characters and it continues them in gibberish but
convincingly-styled Early Modern English — character by character.

This is a personal learning project: my first time training a language model.

```
ROMEO:
Thou hadst to do it.

CORIOLANUS:
That art sure to my husband, and I
Am come to this day.
```
*(actual output from this model, prompted with "ROMEO:")*

---

## What this is

- A **character-level GPT** ([nanoGPT](https://github.com/karpathy/nanoGPT) by
  Andrej Karpathy, vendored), trained on Shakespeare on a laptop in minutes.
- A small, ongoing **LLM-assisted research series**: Claude acts as the
  researcher (under human direction) improving the model version over version.
- Three released versions so far — v1 (the base char-level baseline), v2
  (modern architecture + GPT-2 BPE, BPC 1.919), and v3 (the current champion:
  a corpus-trained 1k-vocab BPE that beats v2 at a third the size, BPC 1.831).
  Full specs, git tags, and rebuild commands live in [`MODELS.md`](MODELS.md).

It's deliberately *not* recursive self-improvement — a human sets direction and
keeps oversight while Claude implements, tests, and measures. The full story is in
[`research-docs/reports/`](../../research-docs/reports/).

## Repository structure

This project lives in a monorepo. Its own folder holds the datasets, configs, run
outputs, and released models; the shared engine and the shared docs/charts live
alongside it:

```
projects/shakespeare/
├── models/            Released versions — each a FROZEN, self-contained, runnable
│   ├── shakespeare-nanogpt-1/   folder (model · config · train · sample · eval ·
│   ├── shakespeare-nanogpt-2/   prepare). Run any of them in place; no shared deps.
│   └── shakespeare-nanogpt-3/
│
├── config/            Training configs for new experiment rounds.
├── data/              The datasets (each with its own prepare.py).
├── runs/              Per-round experiment outputs (configs, logs, eval results).
├── test.txt           The fixed held-out test every version is scored on.
├── leaderboard.md     The scoreboard — every version in bits-per-character.
├── MODELS.md          The version registry: tags, specs, what changed v1→v2.
└── CLAUDE.md          Conventions for agents (and humans) editing the project.

Elsewhere in the monorepo:
../../core/            The shared nanoGPT engine (modern architecture by default):
                       training, sampling, eval, export. New versions are developed
                       here, then snapshotted into this project's models/.
../../tools/dataviz/   Zero-dependency chart pipeline (matches the website's
                       document style) — the single source of every chart.
../../research-docs/   The WRITE-UPS (prose, not code):
  ├── reports/           numbered, frozen experiment reports + charts
  └── model-cards/       a Hugging Face-style card per version
```

Two ideas drive the layout:

- **`models/` vs the shared engine** — releases vs. the lab. The engine in
  `../../core/` keeps changing; a released version copies its code into
  `models/<version>/` so it stays reproducible forever (the duplication is
  intentional).
- **Weights are never committed.** Everything needed to *rebuild* them is — the
  `prepare.py` scripts auto-download the corpora on first run.

## Quick start

One-time setup (Python 3.9+; an Apple Silicon Mac for fast training):

```bash
uv sync   # creates .venv and editable-installs the shared engine + this project
```

Train and sample the base model (v1) — everything runs inside its folder:

```bash
cd models/shakespeare-nanogpt-1
python prepare.py    # downloads Tiny Shakespeare, builds the dataset here
python train.py      # ~12–15 min on Apple Silicon -> ./ckpt.pt
python sample.py --start="ROMEO:" --num_samples=1 --max_new_tokens=1000
```

`python train.py` with no arguments reproduces the version; hyperparameters (and
the main quality dial, `max_iters`) live in that folder's `config.py`, and any
knob can be overridden inline, e.g. `python train.py --max_iters=5000`. The same
four commands rebuild v2 and v3 in their own `models/` folders. See
[`MODELS.md`](MODELS.md) for every recipe.

To run a *new* experiment round against the shared engine (the modern
architecture is the default now), use the monorepo's `core/` from the repo root:

```bash
uv run python core/nanogpt_core/train.py projects/shakespeare/config/train_shakespeare_mac.py \
    --out_dir=projects/shakespeare/runs/r1
uv run python core/eval/eval.py projects/shakespeare/runs/r1 \
    --test projects/shakespeare/test.txt --data-dir projects/shakespeare/data
```

The latest release also runs in the browser — the studio site's
`/model-player` page runs it client-side via
[`@supcomputer/player`](../../player/) ([ADR-0024](../../docs/adr/0024-model-player-page-and-artifact-conventions.md)) —
and in the terminal via the [`sup` CLI](../../cli/). The sample commands above
remain the offline path.

## Learn more

- **[`MODELS.md`](MODELS.md)** — the version registry: every release, its spec, git
  tag, and rebuild commands.
- **[`research-docs/reports/`](../../research-docs/reports/)** — the experiment write-ups
  with charts (start with [Experiment 01](../../research-docs/reports/improve-a-small-model.md)).
- **[`research-docs/model-cards/`](../../research-docs/model-cards/)** — per-version model
  cards (intended use, data, evaluation, limitations).
- **[`leaderboard.md`](leaderboard.md)** — the scoreboard,
  every version scored in bits-per-character on one fixed held-out test.

## Credits

- [nanoGPT](https://github.com/karpathy/nanoGPT) by Andrej Karpathy (MIT License,
  retained in `LICENSE`) — the model and training code.
- The Tiny Shakespeare dataset, via Karpathy's `char-rnn`.
- Set up, trained, and wired up end-to-end with **Claude Opus 4.8**
  ([Claude Code](https://claude.com/claude-code)).
