# Handbook

How the monorepo is shaped, the concrete commands, and how a research round
becomes a release — one file (ADR-0030). The decision records behind all of it
live in [`adr/`](adr/README.md).

## Architecture

The as-built map, and why. The decision to be a monorepo is
[ADR-0001](adr/0001-adopt-a-monorepo.md).

### The split

```
core/        shared, evolving engine — installed once, imported everywhere
projects/    one folder per model; thin config + evidence + frozen releases
player/      @supcomputer/player — vendored browser runtime (ADR-0010, ADR-0025); powers the site's /interfaces page (ADR-0024)
cli/         `sup` — run a released model in the terminal; in-tree only (ADR-0025)
tools/       researcher tooling (charts, synthetic corpora, benchmarks, cost) — operated, not shipped
research-docs/  cross-project prose (reports + model cards)
website/     consumes research-docs/ at build time; owns no content
registry.json   the manifest tying models to the site, player, and CLI
```

The decision that drives the layout: the website and the Claude-managed research
blog have to read across every project at once — run outputs, configs, model
cards. Keep them in separate repos and you sync artifacts across boundaries
forever. In one tree, the receipts are always one directory away.

### core/ — the living engine

`core/nanogpt_core/` is an installable package (`model`, `train`, `sample`,
`configurator`, plus the library surface — `checkpoint`, `bpc` — ADR-0029).
`core/eval/` and `core/export/` are CLI scripts that run against the same env
(kept out of the package so `import eval` / `import export` never shadow
builtins).

- The model is the **modern architecture only** — RoPE, RMSNorm, bias-free. The
  original base architecture isn't carried in the living engine; it survives,
  frozen, inside `projects/shakespeare/models/shakespeare-nanogpt-1/`.
- Paths are configurable (`data_root`), so `core/` knows nothing about any
  specific project. A project supplies its own data and run dirs.
- `core/` is editable-installed, so a change to the engine and to every consumer
  lands in one atomic commit.

### projects/ — thin consumers, fat releases

A project holds its config, corpus prep, run evidence, and **frozen release
folders** under `models/`; its README carries the version index and
leaderboard. Five exist: `shakespeare/` (the reference project — rides
`core/`, keeps a held-out `test.txt`), `gatsby/` (began vendored on the base
char-level engine, ADR-0011; the living project migrated onto `core/` with
byte-level BPE, ADR-0023), `kenosha-kid/` (rides `core/` directly),
`daydream/` (rides `core/`; three board-size tiers and an external
Fairy-Stockfish dependency — ADR-0021, ADR-0022), and `glyph/` (rides `core/`;
a fixed 127-char outline codec — ADR-0027).

Two trees with different jobs live side by side:

- **The living path** develops new versions by calling into `core/`.
- **`models/<version>/`** is a frozen, self-contained snapshot of the exact code
  that produced a released version — its own `model.py`, `config.py`, `train.py`,
  etc. It runs in place and stays reproducible forever, even as `core/` moves on.
  The duplication is intentional. See [Releasing a version](#releasing-a-version).

#### Anatomy of a project (the template for the next one)

Glyph is the reference shape; every project has converged on it:

```
projects/<name>/
  pyproject.toml     workspace member; declares what the project imports
  README.md          self-describing in a sparse clone (hard rule) — including
                     the version index (§ Versions) and scoreboard (§ Leaderboard)
  CLAUDE.md          rules only, auto-loaded by agents; facts live in README (ADR-0030)
  config/<arm>.py    one training config per arm (daydream: micro/regular/grand)
  data/              corpus scripts, one pipeline stage per file; bins gitignored
  harness.py         the project-specific eval — what the loss can't measure
  research/          committed evidence (JSON, logs, the log.md journal)
  models/<id>/       frozen releases (never refactored to share core/)
  runs/              gitignored checkpoints + run logs
```

Everything model-generic — loading, tokenizer resolution, BPC — is imported
from `core/` (`from nanogpt_core import load_model, load_tokenizer`;
`nanogpt_core.bpc.score_run` — ADR-0029), never re-pasted. One historical
exception: gatsby keeps `eval_dial.py`/`generate_samples.py` as separate files
because a published report's reproduce block cites them by name (ADR-0016 —
frozen reports pin paths).

### The no-weights rule

Checkpoints, `*.bin` corpora, and ONNX exports are gitignored and never committed.
They regenerate from the committed code (`prepare.py` downloads corpora; `train.py`
rebuilds weights) and, once published, live in release artifacts referenced by
`registry.json`. This is what keeps the tree cloneable and browsable.

### research-docs/ and website/

`research-docs/` is the cross-project lab notebook — `reports/` (frozen experiment
write-ups at descriptive, stable slugs — ADR-0016) and `model-cards/`. It is the
**source of truth**.

`website/` renders it but stores none of it: `website/scripts/sync-content.mjs`
copies `research-docs/` into a gitignored `website/content/` on every build
(`prebuild`/`predev` hooks), and `build-text.mjs` generates LLM-readable `.md`
twins plus `llms.txt` (ADR-0019). Edit markdown in `research-docs/`, never in
`content/`.

### Tooling

- **Python:** a `uv` workspace (root `pyproject.toml`); `core/` editable-installed.
  Every project is a workspace member with its own `pyproject.toml` declaring
  what it imports; none are build targets.
- **JS:** the `website/` package (`@supcomputer/website`), the vendored
  `player/` package (`@supcomputer/player`), and the in-tree `cli/` (ADR-0025).
- **tools/:** stdlib-only scripts — `dataviz/` (every chart), `synthgen/`
  (every LLM-generated corpus, ADR-0014), `steer/` (shared local-LLM client,
  ADR-0026), `linewell/`, `token-chess/`, `hf-stage/`, `claude_cost.py`,
  `check_integrity.py`. Index: [`tools/README.md`](../tools/README.md).

## Workflows

The concrete commands. Run everything from the repo root. Python goes through the
`uv` workspace, so `core/` is on the path and weights land where you point them.

### Setup (once)

```bash
uv sync     # creates .venv, editable-installs core + projects
```

Prefix Python commands with `uv run`. The engine needs `torch`, `numpy`,
`tiktoken`; ONNX export also needs the `export` extra (`onnx`, `onnxruntime`);
corpus-BPE tokenizers ride the `hf` extra (`tokenizers`).

### Train a new version (shakespeare example)

```bash
# 1. build the corpus into the project's data dir (downloads on first run)
uv run python projects/shakespeare/data/shakespeare_full/prepare.py

# 2. train on the shared engine, writing the run into the project
uv run python core/nanogpt_core/train.py \
    projects/shakespeare/config/train_shakespeare_mac.py \
    --out_dir=projects/shakespeare/runs/r1
```

The config sets `data_root`, `device='mps'`, and the hyperparameters; override any
knob inline, e.g. `--dataset=shakespeare_full --max_iters=5000 --bias=False`.
The checkpoint (`ckpt.pt`) is written into the run dir and is gitignored.

### Evaluate (bits-per-character on the held-out test)

```bash
uv run python core/eval/eval.py projects/shakespeare/runs/r1 \
    --test projects/shakespeare/test.txt \
    --data_root projects/shakespeare/data     # for meta.pkl; omit for GPT-2 BPE
```

`core/eval/eval.py` scores the modern architecture (char, corpus-trained HF
BPE, or GPT-2 — the tokenizer resolves from meta.pkl). Harnesses import
`nanogpt_core.bpc.score_run` instead of parsing the print line (ADR-0029). A
frozen release scores itself from inside its own folder:
`cd projects/shakespeare/models/<version> && python eval.py`.

### Sample

```bash
uv run python core/nanogpt_core/sample.py \
    --out_dir=projects/shakespeare/runs/r1 \
    --data_root=projects/shakespeare/data \
    --start="ROMEO:" --num_samples=1 --max_new_tokens=500
```

### Run a *released* model in the terminal (`sup`)

For releases with published artifacts, the CLI downloads and runs them without
the Python environment — see [`cli/README.md`](../cli/README.md) and
[ADR-0025](adr/0025-sup-cli-and-injectable-player-backend.md):

```bash
cd cli && npm install     # once
node bin/sup.js list
node bin/sup.js shakespeare              # greet the series' newest release
node bin/sup.js pull --all               # doubles as a bundle integrity check
```

### Export to ONNX (for the browser runtime)

```bash
uv run python core/export/export.py \
    projects/shakespeare/models/shakespeare-nanogpt-1 \
    projects/shakespeare/dist
```

Imports the version's own `model.py`, exports a parity-checked `.onnx` (+ int8 and
a manifest fragment). Never ships the `.pt`.

### Charts

Every chart in the repo is generated by the dataviz pipeline — never hand-authored.

```bash
uv run python tools/dataviz/build.py        # writes light/dark PNGs into research-docs/reports/assets/
```

See [`tools/dataviz/README.md`](../tools/dataviz/README.md) for the chart
conventions and the studio document design-system rules (charts match the
website — ADR-0018).

### Website content

```bash
node website/scripts/sync-content.mjs        # copy research-docs/ -> website/content/ (gitignored)
```

Runs automatically on the website's `prebuild`/`predev`. Edit markdown in
`research-docs/`, never in `website/content/`.

### Publishing a report

Write the report at `research-docs/reports/<descriptive-slug>.md` (slug rules:
ADR-0016) with frontmatter: `type:` (experiment/note), `researcher:` keyed into
`registry.json`'s `researchers` map (ADR-0013), a `date:` with the **full
publish timestamp** (the site sorts by it; date-only values make same-day
ordering an alphabetical accident), and a two-sentence `summary:` — the summary
is also the report's row in the generated index, so write it index-worthy.
Experiments carry `number:` and usually `produced:`. Then:

```bash
uv run python tools/check_integrity.py --write   # regenerate the index tables (ADR-0033)
```

Never hand-edit the index tables (reports, ADRs, tools) — CI fails a stale one
and the fix is always the `--write` run above.

### Research cost

```bash
uv run python tools/claude_cost.py           # cost of the newest session transcript
```

### Integrity check

```bash
uv run python tools/check_integrity.py           # registry/docs/links vs the tree (CI runs this)
uv run python tools/check_integrity.py --write   # also regenerate the three index tables (ADR-0033)
```

Run it before committing doc or registry changes.

## Releasing a version

A research round becomes a released model `<project>-N` by **snapshotting** it into
a frozen, self-contained folder — not by pointing at the evolving `core/`. The
snapshot stays reproducible forever; `core/` is free to move on.

### Why snapshot instead of share

`core/` changes round to round. If a release imported `core/`, re-running it later
would silently use newer code. So a release vendors its own copy of every file it
needs (`model.py`, `config.py`, `train.py`, `sample.py`, `eval.py`, `prepare.py`,
`configurator.py`). The duplication is the point — it pins the recipe.

### Steps

1. **Pick the winning run.** Confirm its bits-per-character on the held-out test
   (`core/eval/eval.py` — see [Workflows](#workflows)).

2. **Create the frozen folder** `projects/<project>/models/<project>-N/` and copy
   in the exact code that produced the run. It must run **in place** with no
   arguments and no cross-folder imports:

   ```bash
   cd projects/<project>/models/<project>-N
   python prepare.py && python train.py && python eval.py && python sample.py
   ```

   The shared held-out `test.txt` is read from the project root, not duplicated.

3. **Write the model card** at `research-docs/model-cards/<project>-N.md`
   (details, intended use, data, evaluation with charts, limitations).

4. **Update the records** (this list is the complete, canonical checklist —
   project docs link here rather than restating it):
   - `projects/<project>/README.md` — a row in § Versions and a scored row in
     § Leaderboard (ADR-0030 — the README is the version index and scoreboard).
   - `registry.json` — a model entry (id, tag, arch, tokenizer, params,
     `block_size` from the frozen `config.py`, BPC, card, artifact urls —
     `null` until weights/ONNX are published — and `demo.prompt`: a starter
     prompt the corpus actually contains, leading whitespace load-bearing).
     This is the only registry: the `/interfaces` roster and the `sup` CLI
     both derive newest-runnable-per-lineage from it
     ([ADR-0028](adr/0028-registry-absorbs-the-demo-registry.md)).

5. **Tag it:** `git tag <project>-N` so the exact repo state is recoverable.

6. **Publish artifacts** (when ready): export to ONNX and upload to the R2
   bucket, then fill the `artifacts` urls in `registry.json`. Weights never
   enter the tree. The full pipeline (staging the checkpoint, export, upload,
   registry wiring, browser verification) is documented as the
   [`publish-player-model` skill](../.claude/skills/publish-player-model/SKILL.md);
   conventions in [ADR-0024](adr/0024-model-player-page-and-artifact-conventions.md).

### Invariants

- Frozen folders are never refactored to share `core/`.
- Weights, `*.bin`, and ONNX stay gitignored everywhere.
- Every series is scored on its **same** fixed held-out test, so metrics stay
  comparable across versions.
