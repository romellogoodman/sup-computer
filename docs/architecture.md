# Architecture

How the monorepo is shaped, and why — the as-built map. The decision to be a
monorepo is [ADR-0001](adr/0001-adopt-a-monorepo.md); the original planning
doc, `monorepo-plan.md`, was removed once it went stale and lives in git
history (`git log --diff-filter=D -- docs/monorepo-plan.md`).

## The split

```
core/        shared, evolving engine — installed once, imported everywhere
projects/    one folder per model; thin config + evidence + frozen releases
player/      @supcomputer/player — vendored browser runtime (ADR-0010, ADR-0025); powers the site's /model-player page (ADR-0024)
cli/         `sup` — run a released model in the terminal; in-tree only (ADR-0025)
tools/       researcher tooling (charts, synthetic corpora, benchmarks, cost) — operated, not shipped
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
Five exist: `shakespeare/` (the reference project — rides `core/`, keeps a
held-out `test.txt`), `gatsby/` (began vendored on the base char-level engine,
ADR-0011; the living project migrated onto `core/` with byte-level BPE,
ADR-0023), `kenosha-kid/` (rides `core/` directly), `daydream/` (rides
`core/`; three board-size tiers and an external Fairy-Stockfish dependency —
ADR-0021, ADR-0022), and `glyph/` (rides `core/`; a fixed 127-char outline
codec — ADR-0027).

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
  Every project is a workspace member with its own `pyproject.toml` declaring
  what it imports; none are build targets.
- **JS:** the `website/` package (`@supcomputer/website`), the vendored
  `player/` package (`@supcomputer/player`), and the in-tree `cli/` (ADR-0025).
- **tools/:** stdlib-only scripts — `dataviz/` (every chart), `synthgen/`
  (every LLM-generated corpus, ADR-0014), `steer/` (shared local-LLM client,
  ADR-0026), `linewell/`, `token-chess/`, `claude_cost.py`, `check_integrity.py`.
- See [`workflows.md`](workflows.md) for the concrete commands.
