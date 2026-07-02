# `models/` — frozen, per-version code

Each subfolder is a **self-contained, runnable snapshot of the exact code +
corpus that produces one released model** in the `gatsby-nanogpt-N` series
(see [ADR-0003](../../../docs/adr/0003-frozen-self-contained-releases.md)).
gatsby's working pipeline at the project root keeps evolving; a release copies
its code here so the version stays reproducible.

Every folder runs **in place** — no Claude API, no LM Studio, no cross-folder
code dependencies; the corpus is vendored as `raw.txt`. Generated artifacts
(`*.pt`, `*.bin`, `*.pkl`) stay in the folder and are gitignored.

| Version | Folder | What it is |
|---------|--------|-----------|
| v1 | [`gatsby-nanogpt-1/`](gatsby-nanogpt-1/) | the green-light dial model, Claude-written corpus (~10.65M, base char-level) |
| v2 | [`gatsby-nanogpt-2/`](gatsby-nanogpt-2/) | same behaviour, corpus written by a local 4-model mixture for $0 (~10.65M, base char-level) |

See [`MODELS.md`](../MODELS.md) for the full series spec and
[`research-docs/model-cards/`](../../../research-docs/model-cards/) for each
version's model card.
