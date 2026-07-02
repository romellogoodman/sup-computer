# `models/` — frozen, per-version code

Each subfolder is a **self-contained, runnable snapshot of the exact code +
corpus that produces one released model** in the `kenosha-kid-nanogpt-N` series
(see [ADR-0003](../../../docs/adr/0003-frozen-self-contained-releases.md)).
Day-to-day, kenosha-kid rides the shared [`core/`](../../../core/) engine; a
release vendors a snapshot of that engine so it reproduces forever, independent
of `core` drift.

Every folder runs **in place** with no cross-folder code dependencies; generated
artifacts (`*.pt`, `*.bin`, `*.pkl`) stay in the folder and are gitignored. The
corpus (`raw.txt`) is committed — it is the research record.

| Version | Folder | What it is |
|---------|--------|-----------|
| v1 | [`kenosha-kid-nanogpt-1/`](kenosha-kid-nanogpt-1/) | the 350-iter mid-transition "dreaming" checkpoint (~0.79M, modern arch) |
| v2 | [`kenosha-kid-nanogpt-2/`](kenosha-kid-nanogpt-2/) | the converged 1100-iter **drift-corpus** checkpoint — crisp anchors AND near-misses (~0.79M, modern arch) |

See [`MODELS.md`](../MODELS.md) for the full series spec and
[`research-docs/model-cards/`](../../../research-docs/model-cards/) for each
version's model card.
