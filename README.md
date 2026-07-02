# sup computer

**A small language model studio.** Train small GPTs from scratch, write up the
research, and show the results — engine, experiments, model cards, and a website,
all in one tree so each piece can read the others' outputs from one directory away.

The models here are *small* on purpose: ~10–30M parameters, trainable on a laptop,
built to be understood end to end rather than to top a benchmark. The interesting
part isn't the loss curve — it's what you can make a tiny model *do*.

## What's inside

Three projects so far:

- **shakespeare** — a tiny GPT trained on the works of Shakespeare. Two releases:
  a character-level base model (`shakespeare-nanogpt-1`) and a modern BPE rebuild
  (`shakespeare-nanogpt-2`, RoPE + RMSNorm + bias-free).
- **gatsby** — a ~10M model trained to behave like [Golden Gate
  Claude](https://www.anthropic.com/news/golden-gate-claude), fixated on Jay
  Gatsby's green light. The obsession is baked into training, not steered at
  inference, and its intensity rides on a dial (`gatsby-nanogpt-1`, and a
  4-voice mixture-corpus rebuild in `gatsby-nanogpt-2`).
- **kenosha-kid** — a ~0.8M char-level GPT that knows only six words: its
  entire corpus is punctuated permutations of one phrase from *Gravity's
  Rainbow*, and the blur it dreams instead of memorizing is the artifact
  (`kenosha-kid-nanogpt-1`).

And the write-ups behind them, in [`research-docs/reports/`](research-docs/reports/):

- [Can a big model improve a small one?](research-docs/reports/improve-a-small-model.md)
- [Can you put an obsession on a dial?](research-docs/reports/obsession-on-a-dial.md)
- [Can four borrowed models write one obsession?](research-docs/reports/mixture-of-models.md)
- [Can a model dream a single phrase?](research-docs/reports/dream-a-single-phrase.md)
- [The logits oracle: running small models in the browser](research-docs/reports/logits-oracle.md)

## Layout

| Path | What it is |
|---|---|
| [`core/`](core/) | The shared engine — model, train, sample, eval, ONNX export. Modern arch only (RoPE, RMSNorm, bias-free). Editable-installed; projects import it. |
| [`projects/`](projects/) | One model project each — config, corpus prep, run evidence, model cards, and frozen release snapshots. |
| [`player/`](player/) | `@supcomputer/player` — a browser runtime that runs a model's forward pass in [onnxruntime-web](https://onnxruntime.ai/) and keeps the sampling loop in JS. |
| [`tools/`](tools/) | Researcher tooling: the `dataviz/` chart pipeline (every chart goes through it), the `synthgen/` local-LLM corpus pipeline, and cost accounting. |
| [`research-docs/`](research-docs/) | Cross-project write-ups: `reports/` and `model-cards/`. |
| [`website/`](website/) | The studio site (Next.js). Owns no content — a prebuild step copies `research-docs/` in. |
| [`registry.json`](registry.json) | The model manifest the site and player read. |

Weights and large corpora never live in the tree — they're regenerated from code
or hosted as release artifacts and referenced from `registry.json`. Each release
under `projects/*/models/` is frozen, self-contained, and pinned to a git tag.

## Getting started

Python is a [`uv`](https://docs.astral.sh/uv/) workspace; `core/` is editable-installed.

```bash
uv sync                                       # create .venv, install core + projects
uv run python core/nanogpt_core/train.py ...  # see docs/workflows.md for the real flags
```

The website:

```bash
cd website && npm install && npm run dev   # http://localhost:3000
```

## Docs

- [`docs/architecture.md`](docs/architecture.md) — the layout in depth, and why it's shaped this way.
- [`docs/workflows.md`](docs/workflows.md) — the actual commands: prepare data, train, eval, sample, export, build charts, sync the site.
- [`docs/releasing.md`](docs/releasing.md) — turning a research round into a tagged, frozen release.
- [`docs/adr/`](docs/adr/) — Architecture Decision Records: why things are the way they are.
- [`docs/TODO.md`](docs/TODO.md) — the open backlog.

Most of this repo is developed with [Claude Code](https://claude.com/claude-code);
[`CLAUDE.md`](CLAUDE.md) holds the conventions agents follow here.

## License

[MIT](LICENSE).
