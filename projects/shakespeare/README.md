# shakespeare-nanogpt

A tiny character-level GPT trained from scratch on the works of Shakespeare.
Give it a few characters and it continues them in (gibberish but
convincingly-styled) Early Modern English — character by character.

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
- A small, ongoing **LLM-assisted research series**: Claude Opus 4.8 acts as the
  researcher (under human direction) improving the model version over version.
- Two released versions so far — **v1** (the base char-level baseline) and **v2**
  (the research winner: modern architecture + BPE, **BPC 1.919**). Full specs,
  git tags, and rebuild commands live in **[`MODELS.md`](MODELS.md)**.

It's deliberately **not** recursive self-improvement — a human sets direction and
keeps oversight while Claude implements, tests, and measures. The full story is in
[`research-docs/reports/`](research-docs/reports/).

## Repository structure

The repo is organized so each folder has one clear job:

```
shakespeare-nanogpt/
├── models/            Released versions — each a FROZEN, self-contained, runnable
│   ├── shakespeare-nanogpt-1/   folder (model · config · train · sample · eval ·
│   └── shakespeare-nanogpt-2/   prepare). Run any of them in place; no shared deps.
│
├── research-lab/      The LIVING LAB: the nanoGPT engine + the modern variant,
│                      its datasets (data/), experiment rounds (runs/), eval, and
│                      the leaderboard. New versions are developed here, then
│                      snapshotted into models/.
│
├── research-docs/     The WRITE-UPS (prose, not code):
│   ├── reports/         numbered, frozen experiment reports + charts
│   └── model-cards/     a Hugging Face-style card per version
│
├── dataviz/           Zero-dependency chart pipeline (own Vercel Geist design
│                      system) — the single source of every chart in the repo.
├── web-ui/            A small browser app to generate from the model.
│
├── MODELS.md          The version registry: tags, specs, what changed v1→v2.
└── CLAUDE.md          Conventions for agents (and humans) editing the repo.
```

Two ideas drive the layout:

- **`models/` vs `research-lab/`** — releases vs. the lab. `research-lab/` keeps
  changing; a released version copies its code into `models/<version>/` so it
  stays reproducible forever (the duplication is intentional).
- **Weights are never committed.** Everything needed to *rebuild* them is — the
  `prepare.py` scripts auto-download the corpora on first run.

## Quick start

One-time setup (Python 3.9+; an Apple Silicon Mac for fast training):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install torch numpy tiktoken tqdm requests
```

Train and sample the base model (**v1**) — everything runs inside its folder:

```bash
cd models/shakespeare-nanogpt-1
python prepare.py    # downloads Tiny Shakespeare, builds the dataset here
python train.py      # ~12–15 min on Apple Silicon -> ./ckpt.pt
python sample.py --start="ROMEO:" --num_samples=1 --max_new_tokens=1000
```

`python train.py` with no arguments reproduces the version; hyperparameters (and
the main quality dial, `max_iters`) live in that folder's `config.py`, and any
knob can be overridden inline, e.g. `python train.py --max_iters=5000`. The same
four commands rebuild **v2** in `models/shakespeare-nanogpt-2/`. See
[`MODELS.md`](MODELS.md) for both recipes, and
[`research-lab/`](research-lab/) for running new experiment rounds.

## Web UI (`web-ui/`)

A browser app for generating without the command line: type a prompt, click
**Generate**, read the output. The Node backend (`web-ui/server.js`, zero
dependencies) shells out to `models/shakespeare-nanogpt-1/sample.py`; user input
is sanitized to the model's 65-character vocabulary and passed via a temp file.

```bash
cd web-ui
npm install      # first time only
npm run server   # terminal 1 — model backend on http://localhost:3000
npm run dev      # terminal 2 — UI on http://localhost:8080 (opens browser)
```

Requires a trained `models/shakespeare-nanogpt-1/ckpt.pt` (see Quick start). The
backend references the model by absolute path, so it runs on this machine.

## Learn more

- **[`MODELS.md`](MODELS.md)** — the version registry: every release, its spec, git
  tag, and rebuild commands.
- **[`research-docs/reports/`](research-docs/reports/)** — the experiment write-ups
  with charts (start with [Experiment 01](research-docs/reports/experiment-01.md)).
- **[`research-docs/model-cards/`](research-docs/model-cards/)** — per-version model
  cards (intended use, data, evaluation, limitations).
- **[`research-lab/leaderboard.md`](research-lab/leaderboard.md)** — the scoreboard,
  every version scored in bits-per-character on one fixed held-out test.

## Credits

- [nanoGPT](https://github.com/karpathy/nanoGPT) by Andrej Karpathy (MIT License,
  retained in `LICENSE`) — the model and training code.
- The Tiny Shakespeare dataset, via Karpathy's `char-rnn`.
- Set up, trained, and wired up end-to-end with **Claude Opus 4.8**
  ([Claude Code](https://claude.com/claude-code)).
