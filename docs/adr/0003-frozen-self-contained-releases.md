# ADR 0003: Releases are frozen, self-contained snapshots

- **Status:** Accepted
- **Date:** 2026-06-27
- **Deciders:** Romello Goodman (with Claude)

## Context

The monorepo idea favors thin projects sitting on a shared, evolving `core/`
([ADR-0001](0001-adopt-a-monorepo.md)). That is right for *developing* the next
version, but it is a trap for a *released* one. `core/` changes round to round. If a
released version imported the live `core/`, re-running it a year later would silently
use newer code — a different model than the one we published, wearing the same
version number.

The priority for a release is that it stays forever-reproducible. A version is a
claim ("this recipe gets BPC 1.919"), and a claim has to be re-checkable against the
exact code that produced it, not against whatever the engine has since become.

## Decision

We will make each released version a frozen, self-contained snapshot at
`projects/<project>/models/<version>/`. The snapshot vendors its own copy of every
file it needs — `model.py`, `config.py`, `train.py`, `sample.py`, `eval.py`,
`prepare.py`, `configurator.py` — runs in place with no cross-folder imports, and is
pinned to a git tag (`<project>-N`). The duplication against `core/` is intentional:
it is what pins the recipe.

New versions are developed against the living `core/`
([ADR-0005](0005-core-as-uv-workspace-package.md)) and snapshotted into a new
`models/` folder at release time — never the reverse. See
[`releasing.md`](../releasing.md) for the procedure.

One external dependency deliberately remains, and we flag it honestly as a known
seam: a release's `eval.py` reads the shared held-out `test.txt` from the project
root rather than vendoring its own copy. That is the intended coupling — every
version must be scored against the *same* bytes for BPC to stay comparable
([ADR-0002](0002-no-weights-in-tree.md)), so a per-release copy would defeat the
purpose. It does mean a frozen folder is not 100% hermetic; it is hermetic except
for the one file the comparison requires to be shared.

## Consequences

- A version stays reproducible even as `core/` moves on — the recipe is pinned to
  bytes on disk and to a git tag.
- Duplication is bounded and accepted: a handful of small Python files per release,
  in exchange for permanent reproducibility.
- There is one acknowledged seam (`test.txt`), documented here so no one "fixes" it
  by vendoring a copy and silently forking the yardstick.

## Alternatives considered

- **Thin project + shared `core/` only** — rejected. It is the cleaner layout but it
  is not reproducible: the release drifts every time the engine does.
- **Rely on git tags + `registry.json` alone** — rejected. A tag records repo state,
  but reconstructing a release means checking out the tag and reasoning about which
  `core/` it pulled. The frozen folder makes the runnable recipe explicit and local;
  the code can't drift out from under the tag.
