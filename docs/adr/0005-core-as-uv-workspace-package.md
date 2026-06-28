# ADR 0005: Package the core as an editable uv workspace

- **Status:** Accepted
- **Date:** 2026-06-27
- **Deciders:** Romello Goodman (with Claude)

## Context

The engine arrived karpathy-style: bare `from model import …`, an
`exec(open('configurator.py'))` config hack, and `research-lab/` paths resolved
relative to the current working directory. That shape works when there is exactly one
script run from exactly one folder, but it can't be imported cleanly or reused across
projects — the whole point of a shared `core/` ([ADR-0001](0001-adopt-a-monorepo.md)).
Bare imports collide, cwd-relative paths break the moment you run from elsewhere, and
`exec`-ing a config file is invisible to any tooling.

## Decision

We will make `nanogpt_core` an installable Python package and tie the repo together
with a `uv` workspace.

- The package exports the importable engine: `model`, `train`, `sample`,
  `configurator`. Imports become explicit — `from nanogpt_core.model import …`.
- `eval.py` and `export.py` stay **CLI scripts** run against the same env, kept *out*
  of the package on purpose: as modules named `eval` and `export` they would shadow
  Python builtins (`import eval` / `import export`), so they live in `core/eval/` and
  `core/export/` and are run, not imported.
- The configurator `exec` is made `__file__`-relative instead of cwd-relative, so it
  resolves correctly regardless of where you run from.
- Data location becomes a configurable `data_root`, so `core/` knows nothing about
  any specific project — a project supplies its own data and run directories.
- A `uv` workspace (a virtual root `pyproject.toml`) installs `core` editable and
  registers `projects/shakespeare` as a consumer.

## Consequences

- Editing the engine and every consumer is one atomic change — `core/` is
  editable-installed, so there is no publish/bump cycle between an engine change and
  the projects that use it.
- Setup is one command: `uv sync` creates the `.venv` and installs `core` + projects.
- The split was validated end-to-end (train → eval → sample) on Apple MPS, so the
  packaging didn't just typecheck — it ran.
- `eval`/`export` being scripts (not importable) is a small ergonomic cost accepted
  to avoid builtin name shadowing.

This packaging is also what makes [ADR-0003](0003-frozen-self-contained-releases.md)
coherent: new versions are developed against this living, editable `core/` and then
snapshotted into frozen folders at release time.

## Alternatives considered

- **Keep the cwd-relative scripts as-is** — rejected. They are fragile and
  project-coupled; they can't be reused across projects without copy-paste, which is
  the problem the monorepo set out to end.
- **Make `eval` and `export` importable packages too** — rejected. Their module names
  shadow Python builtins; keeping them as CLI scripts sidesteps the collision
  entirely for a trivial cost.
