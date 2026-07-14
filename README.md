# sup computer

**A small language model studio.** Train small GPTs from scratch, write up the
research, and show the results — engine, experiments, model cards, and a website,
all in one tree so each piece can read the others' outputs from one directory away.

The models here are *small* on purpose: ~10–30M parameters, trainable on a laptop,
built to be understood end to end rather than to top a benchmark. The interesting
part isn't the loss curve — it's what you can make a tiny model *do*.

## What's inside

Four projects so far — each is self-describing; follow the link for the full story:

- [**shakespeare**](projects/shakespeare/) — a tiny GPT trained on the works of
  Shakespeare; three releases, from a char-level baseline to a corpus-trained
  BPE at a third the size.
- [**gatsby**](projects/gatsby/) — a ~10M model that behaves like [Golden Gate
  Claude](https://www.anthropic.com/news/golden-gate-claude), fixated on Jay
  Gatsby's green light; the obsession is baked into training and rides a dial.
- [**kenosha-kid**](projects/kenosha-kid/) — a ~0.8M char-level GPT whose entire
  corpus is punctuated permutations of six Pynchon words; the blur it dreams
  instead of memorizing is the artifact.
- [**daydream**](projects/daydream/) — a three-tier family of chess-move GPTs
  that learned move text from games, never the rules; illegal moves render as
  dim near-misses instead of being masked.

The write-ups behind them — every experiment, annotated and in order — are
indexed at [`research-docs/reports/`](research-docs/reports/README.md).

## Layout

| Path | What it is |
|---|---|
| [`core/`](core/) | The shared engine — model, train, sample, eval, ONNX export. Modern arch only (RoPE, RMSNorm, bias-free). Editable-installed; projects import it. |
| [`projects/`](projects/) | One model project each — config, corpus prep, run evidence, model cards, and frozen release snapshots. |
| [`player/`](player/) | `@supcomputer/player` — a browser runtime that runs a model's forward pass in [onnxruntime-web](https://onnxruntime.ai/) and keeps the sampling loop in JS. |
| [`tools/`](tools/) | Researcher tooling — each tool documents itself in its own README; every chart goes through `dataviz/`. |
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
uv run python core/nanogpt_core/train.py ...  # see docs/handbook.md for the real flags
```

The website:

```bash
cd website && npm install && npm run dev   # http://localhost:3000
```

## Docs

- [`docs/handbook.md`](docs/handbook.md) — the one operating doc: the layout
  in depth (§ Architecture), the actual commands (§ Workflows), and turning a
  research round into a tagged, frozen release (§ Releasing a version).
- [`docs/adr/`](docs/adr/) — Architecture Decision Records: why things are the way they are.

Most of this repo is developed with [Claude Code](https://claude.com/claude-code);
[`CLAUDE.md`](CLAUDE.md) holds the conventions agents follow here.

## License

[MIT](LICENSE).
