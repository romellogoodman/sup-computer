# sup computer

A small language model studio: train small GPTs, write up the research, and show
the results. A monorepo so the website and the Claude-managed research blog can
read run outputs, configs, and model cards that sit one directory away.

## Map

One line per row — the detail lives in each path's own README, and the map in
depth (with the why) is [`docs/architecture.md`](docs/architecture.md).

| Path | What it is |
|---|---|
| `core/` | The shared engine — model, train, sample, eval, ONNX export. Modern arch only; editable-installed. |
| `projects/<name>/` | One thin model project each — four so far (shakespeare, gatsby, kenosha-kid, daydream); each is self-describing via its own README + CLAUDE.md. |
| `player/` | `@supcomputer/player` — vendored browser runtime for released models (ADR-0025). |
| `cli/` | `sup` — run a release in the terminal; in-tree only (ADR-0025). |
| `tools/` | Researcher tools, not shipped code — each documents itself in its own README. One rule to know up front: **every chart goes through `tools/dataviz/`**. |
| `research-docs/` | Cross-project write-ups: `reports/` (experiments) and `model-cards/`. Claude writes here. |
| `website/` | The studio site — owns no content; syncs `research-docs/` at prebuild (ADR-0019). |
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
- **Reports are frozen** once published. Each lives at a descriptive, stable slug
  (`research-docs/reports/<descriptive-slug>.md`, e.g. `obsession-on-a-dial.md`) —
  the slug is the public URL, so don't rename a published report; supersede it with
  a new report rather than editing. `type:` (experiment/note) and `series:` live in
  frontmatter. See `docs/adr/0016-descriptive-report-slugs.md`.
- **Credit the AI researcher.** Every report sets `researcher: <id>` in its
  frontmatter and every `registry.json` model entry sets `"researcher": "<id>"`,
  keyed into the `researchers` map in `registry.json`. Model cards do **not**
  restate this as a body-level `**Researcher:**` line — it's redundant with
  the model-details table the site renders from `registry.json`, so as of
  2026-07-02 it's been removed from every card. The researcher is the model
  that *did the research*, distinct from the model being built. See
  `docs/adr/0013-attribution-of-the-ai-researcher.md`.

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
- `docs/monorepo-plan.md` — the original rationale for the monorepo (archived —
  history, not maintained).
- `docs/TODO.md` — the durable backlog of known open work.
- `docs/adr/` — Architecture Decision Records: why things are shaped the way they
  are. Read the relevant ones, and **write a new ADR** (see `docs/adr/README.md`)
  for any architecturally significant or hard-to-reverse decision you make.

Each project also has its own `CLAUDE.md` (e.g. `projects/shakespeare/CLAUDE.md`)
with project-specific conventions — read it before editing inside that project.
