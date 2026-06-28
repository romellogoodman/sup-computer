# sup computer

A small language model studio: train small GPTs, write up the research, and show
the results. A monorepo so the website and the Claude-managed research blog can
read run outputs, configs, and model cards that sit one directory away.

## Map

| Path | What it is |
|---|---|
| `core/` | The shared engine. `nanogpt_core/` (model, train, sample, configurator), `eval/`, `export/`. Editable-installed; projects import it. The model is the modern arch only (RoPE, RMSNorm, bias-free). |
| `projects/<name>/` | One model project — thin: config, corpus prep, run evidence, model cards, and frozen release snapshots under `models/`. `shakespeare/` is the first. |
| `tools/` | Researcher tools, not shipped code: `dataviz/` (the chart pipeline — every chart goes through it) and `claude_cost.py`. |
| `research-docs/` | Cross-project write-ups: `reports/` (experiments) and `model-cards/`. Claude writes here. |
| `website/` | The studio site (custom React/Next.js, not yet scaffolded). Owns no content — a prebuild script copies `research-docs/` into a gitignored `content/`. |
| `registry.json` | Model manifest the site + player consume. |

## Hard rules

- **No weights or large corpora in the tree.** `*.pt`, `*.bin`, `*.onnx`, `*.pkl`
  are gitignored and live in release artifacts / R2, referenced by `registry.json`.
  Check `git status` shows none staged before committing.
- **Releases are frozen and self-contained.** `projects/*/models/<version>/` is a
  runnable snapshot pinned to a git tag; don't refactor it to share `core/`. A new
  research round becomes a *new* frozen folder — see `docs/releasing.md`.
- **Projects stay thin and self-describing.** Each `projects/*/README.md` must let
  a reader understand that project in isolation (sparse clone).
- **Reports are frozen** once published (`research-docs/reports/experiment-NN.md`);
  supersede with a new number rather than editing.
- **Credit the AI researcher.** Every report sets `researcher: <id>` in its
  frontmatter and every `registry.json` model entry sets `"researcher": "<id>"`,
  keyed into the `researchers` map in `registry.json` (model cards state it in the
  body as a `**Researcher:**` line). The researcher is the model that *did the
  research*, distinct from the model being built. See `docs/adr/0013-attribution-of-the-ai-researcher.md`.

## How to work here

Python is a `uv` workspace; `core/` is editable-installed into the venv.

```bash
uv sync                 # create .venv, install core + projects
uv run python ...       # run anything against that env
```

Before starting a task, read the doc that fits it:

- `docs/architecture.md` — the layout in depth and why it's shaped this way.
- `docs/workflows.md` — the actual commands: prepare data, train, eval, sample,
  export to ONNX, build charts, sync website content.
- `docs/releasing.md` — turning a research round into a tagged, frozen release.
- `docs/monorepo-plan.md` — the original rationale for the monorepo.
- `docs/TODO.md` — the durable backlog of known open work.
- `docs/adr/` — Architecture Decision Records: why things are shaped the way they
  are. Read the relevant ones, and **write a new ADR** (see `docs/adr/README.md`)
  for any architecturally significant or hard-to-reverse decision you make.

Each project also has its own `CLAUDE.md` (e.g. `projects/shakespeare/CLAUDE.md`)
with project-specific conventions — read it before editing inside that project.
