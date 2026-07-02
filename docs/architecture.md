# Architecture

How the monorepo is shaped, and why. For the original decision rationale see
[`monorepo-plan.md`](monorepo-plan.md); this is the as-built map.

## The split

```
core/        shared, evolving engine — installed once, imported everywhere
projects/    one folder per model; thin config + evidence + frozen releases
player/      @supcomputer/player — vendored browser runtime (ADR-0010); unwired until /play
tools/       researcher tooling (charts, synthetic corpora, cost) — operated, not shipped
research-docs/  cross-project prose (reports + model cards)
website/     consumes research-docs/ at build time; owns no content
registry.json   the manifest tying models to the site and player
```

The decision that drives the layout: the website and the Claude-managed research
blog have to read across every project at once — run outputs, configs, model
cards. Keep them in separate repos and you sync artifacts across boundaries
forever. In one tree, the receipts are always one directory away.

## core/ — the living engine

`core/nanogpt_core/` is an installable package (`model`, `train`, `sample`,
`configurator`). `core/eval/` and `core/export/` are CLI scripts that run against
the same env (kept out of the package so `import eval` / `import export` never
shadow builtins).

- The model is the **modern architecture only** — RoPE, RMSNorm, bias-free. The
  original base architecture isn't carried in the living engine; it survives,
  frozen, inside `projects/shakespeare/models/shakespeare-nanogpt-1/`.
- Paths are configurable (`data_root`), so `core/` knows nothing about any
  specific project. A project supplies its own data and run dirs.
- `core/` is editable-installed, so a change to the engine and to every consumer
  lands in one atomic commit.

## projects/ — thin consumers, fat releases

A project holds its config, corpus prep, run evidence, the version registry
(`MODELS.md`), the leaderboard, and **frozen release folders** under `models/`.
Three exist: `shakespeare/` (the reference project — rides `core/`, keeps a
held-out `test.txt`), `gatsby/` (vendors its own base char-level engine,
ADR-0011; migration to `core/` is TODO item 2), and `kenosha-kid/` (rides
`core/` directly).

Two trees with different jobs live side by side:

- **The living path** develops new versions by calling into `core/`.
- **`models/<version>/`** is a frozen, self-contained snapshot of the exact code
  that produced a released version — its own `model.py`, `config.py`, `train.py`,
  etc. It runs in place and stays reproducible forever, even as `core/` moves on.
  The duplication is intentional. See [`releasing.md`](releasing.md).

## The no-weights rule

Checkpoints, `*.bin` corpora, and ONNX exports are gitignored and never committed.
They regenerate from the committed code (`prepare.py` downloads corpora; `train.py`
rebuilds weights) and, once published, live in release artifacts referenced by
`registry.json`. This is what keeps the tree cloneable and browsable.

## research-docs/ and website/

`research-docs/` is the cross-project lab notebook — `reports/` (frozen experiment
write-ups at descriptive, stable slugs — ADR-0016) and `model-cards/`. It is the
**source of truth**.

`website/` renders it but stores none of it: `website/scripts/sync-content.mjs`
copies `research-docs/` into a gitignored `website/content/` on every build
(`prebuild`/`predev` hooks), and `build-text.mjs` generates LLM-readable `.md`
twins plus `llms.txt` (ADR-0019). Edit markdown in `research-docs/`, never in
`content/`.

## Tooling

- **Python:** a `uv` workspace (root `pyproject.toml`); `core/` editable-installed.
  Vendored/thin projects (`gatsby/`, `kenosha-kid/`) are excluded from the
  workspace and run as plain scripts.
- **JS:** the `website/` package (`@supcomputer/website`) and the vendored
  `player/` package (`@supcomputer/player`).
- **tools/:** stdlib-only scripts — `dataviz/` (every chart), `synthgen/`
  (every LLM-generated corpus, ADR-0014), `claude_cost.py`.
- See [`workflows.md`](workflows.md) for the concrete commands.
