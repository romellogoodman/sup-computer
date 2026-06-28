# Architecture Decision Records

Each ADR captures one architecturally significant decision — the context, the call
we made, and what it costs us — so the *why* survives the people and the session
that decided it. Format is lightweight (Nygard-style): see
[`template.md`](template.md).

**Write a new ADR when** a decision shapes structure, is hard to reverse, or
contradicts an obvious default — anything a future reader would otherwise have to
reverse-engineer from the tree. Number sequentially, never renumber, never delete;
supersede instead (mark the old one `Superseded by ADR-NNNN`).

## Index

| # | Decision | Status |
|---|---|---|
| [0001](0001-adopt-a-monorepo.md) | Adopt a monorepo for sup computer | Accepted |
| [0002](0002-no-weights-in-tree.md) | Keep weights and large corpora out of the tree | Accepted |
| [0003](0003-frozen-self-contained-releases.md) | Releases are frozen, self-contained snapshots | Accepted |
| [0004](0004-core-is-modern-only.md) | The shared engine carries only the modern architecture | Accepted |
| [0005](0005-core-as-uv-workspace-package.md) | Package the core as an editable uv workspace | Accepted |
| [0006](0006-tools-top-level.md) | `tools/` is a top-level home for researcher tooling | Accepted |
| [0007](0007-research-docs-and-content-sync.md) | `research-docs/` is cross-project; the website syncs content | Accepted |
| [0008](0008-defer-the-player.md) | Defer the browser player and remove `web-ui` | Accepted |
| [0009](0009-website-ia-and-style.md) | Website information architecture and visual style | Accepted |
