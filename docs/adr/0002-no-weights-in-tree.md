# ADR 0002: Keep weights and large corpora out of the tree

- **Status:** Accepted
- **Date:** 2026-06-27
- **Deciders:** Romello Goodman (with Claude)

## Context

The monorepo's whole value is that it stays a legible, browsable studio
([ADR-0001](0001-adopt-a-monorepo.md)). The artifacts of model work fight that
value directly: checkpoints run to roughly 1.2 GB of `.pt` files, corpora ship as
`.bin` blobs, and exports land as ONNX. Commit any of it and clone time balloons,
`git` history bloats, and the "open the tree and read it" promise inverts into a
multi-gigabyte download.

The redeeming fact is that none of it is *source*. Weights regenerate from the
committed training code; corpora regenerate from a committed `prepare.py` that pulls
from a stable upstream. The artifacts are outputs, and outputs belong in artifact
storage, not version control.

## Decision

We will gitignore all generated heavyweight artifacts repo-wide:
`*.pt`, `*.bin`, `*.onnx`, `*.pkl`, and `*.vocab.json`, enforced in the root
`.gitignore` and repeated in per-project `.gitignore`s (so sparse clones inherit the
rule). They regenerate from committed code — `prepare.py` downloads the corpus and
`train.py` rebuilds the weights — and, once a version is published, the published
artifacts live in GitHub release artifacts / R2, referenced by `registry.json`
(whose `artifacts` urls stay `null` until then).

**The one deliberate exception is `projects/shakespeare/test.txt`** — the fixed
held-out evaluation yardstick (~250 KB). It IS committed, on purpose. Every version
in the series is scored on its exact bytes in bits-per-character, so the whole
leaderboard is comparable. If those bytes ever drifted or regenerated differently,
cross-version BPC comparisons would silently break. A yardstick has to be frozen, so
it is source, not a regenerated artifact.

## Consequences

- Clones stay light and the tree stays browsable — the core studio value holds.
- Reproducibility now depends on two things staying stable: the committed code and a
  reachable upstream corpus. If upstream disappears, a corpus has to be re-sourced.
- Published artifacts need external hosting (a GitHub release or R2) before a version
  is truly downloadable; the registry carries the pointers
  ([ADR-0008](0008-defer-the-player.md) keeps the export → ONNX → registry path warm
  for exactly this).

## Alternatives considered

- **Git LFS** — rejected. The bytes are still heavy, just behind a pointer; it adds
  a dependency, storage cost, and bandwidth limits, and a careless clone still pulls
  gigabytes. It manages the bloat rather than removing it.
- **Just commit the weights** — rejected outright. It kills the core value the
  monorepo exists to deliver.
