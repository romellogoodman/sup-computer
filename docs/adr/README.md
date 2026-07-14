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
| [0010](0010-vendor-the-player.md) | Vendor nanogpt-player as @supcomputer/player | Accepted |
| [0011](0011-vendor-gatsby.md) | Vendor gatsby-nanogpt as a self-contained project | Superseded by [0023](0023-gatsby-migrates-to-core-bpe.md) |
| [0012](0012-pluggable-tokenization.md) | Tokenization is pluggable on the shared core; `meta.pkl` is the contract | Accepted |
| [0013](0013-attribution-of-the-ai-researcher.md) | Attribution: every report and model records the AI researcher | Accepted |
| [0014](0014-synthgen-local-llm-pipeline.md) | Synthetic-data generation via LM Studio lives in `tools/synthgen` (LLM-only, provenance-first) | Accepted |
| [0015](0015-research-post-standardization.md) | Standardize research posts: link rewriting, style extensions, post conventions | Accepted |
| [0016](0016-descriptive-report-slugs.md) | Research reports use descriptive slugs, not `experiment-NN` | Accepted |
| [0017](0017-website-redesign-refined-prof-style.md) | Website redesign: the refined "Prof. Dr." style (BEM, color tokens, dark mode, sidenotes) | Accepted |
| [0018](0018-dataviz-matches-the-website.md) | dataviz charts match the website's document style (drop Vercel Geist) | Accepted |
| [0019](0019-llm-readable-markdown-endpoints.md) | LLM-readable markdown twins for every research URL (`/….md`, `/llms.txt`) | Accepted |
| [0020](0020-one-home-per-fact.md) | One home per fact — living docs link instead of restating | Accepted |
| [0021](0021-daydream-fairy-stockfish-dependency.md) | Daydream depends on Fairy-Stockfish as an external engine binary | Accepted |
| [0022](0022-daydream-three-tier-sampler-prober-shape.md) | Daydream is a three-tier board-size family, and the first sampler/prober project | Accepted |
| [0023](0023-gatsby-migrates-to-core-bpe.md) | gatsby migrates onto the modern core engine with byte-level BPE | Accepted |
| [0024](0024-model-player-page-and-artifact-conventions.md) | The model-player page, its registry, and artifact conventions | Amended by [0028](0028-registry-absorbs-the-demo-registry.md) |
| [0025](0025-sup-cli-and-injectable-player-backend.md) | An in-tree `sup` CLI and an injectable player backend | Accepted |
| [0026](0026-steer-shared-orchestration-layer.md) | `tools/steer` — the shared shape for a big model steering a small one | Accepted |
| [0027](0027-glyph-one-char-per-token-outline-codec.md) | glyph's one-char-per-token outline codec on a fixed 127-char alphabet | Accepted |
| [0028](0028-registry-absorbs-the-demo-registry.md) | registry.json absorbs the demo registry; bundle rules live in the player | Accepted |
| [0029](0029-core-exports-a-library-surface.md) | core exports a library surface (load, tokenize, score) | Accepted |
