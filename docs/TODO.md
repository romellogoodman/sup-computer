# sup computer — backlog

The durable list of known open work, captured so it survives the session that
found it. This is intent, not a contract: items here are scoped enough to pick up,
and each one cross-links the ADRs, reports, and files that explain *why* it exists.
For the architectural decisions behind these, see [`adr/`](adr/README.md); for the
original rationale, [`monorepo-plan.md`](monorepo-plan.md).

## The three main TODOs

1. **Wire up the player** — build the website `/play` route and the hosting it needs.
   - Run [`core/export/export.py`](../core/export/export.py) on the released models
     to produce `.onnx` + `vocab.json` (the per-model tokenizer the oracle doesn't carry).
   - Host the artifacts (GitHub release / R2) and fill the currently-`null`
     `artifacts` URLs in [`registry.json`](../registry.json).
   - Build the `/play` route on the website consuming `@supcomputer/player`
     ([`player/`](../player/README.md)) + the registry. Nothing consumes the player yet.
   - Refs: [ADR-0010](adr/0010-vendor-the-player.md) (vendored player),
     [ADR-0008](adr/0008-defer-the-player.md) (the deferral it amended),
     [ADR-0002](adr/0002-no-weights-in-tree.md) (no weights in tree),
     [the logits oracle](../research-docs/reports/logits-oracle.md).

2. **Migrate gatsby onto the modern `core` engine** — move gatsby off its vendored
   base char-level engine to `core` (modern / BPE).
   - This doubles as the structural fix for gatsby's unreliable topic-honoring:
     BPE conditioning is the real fix (a short char prefix is too weak a signal for
     a 10M char-LM to latch onto).
   - So this also moves gatsby toward exhibit-ready: `gatsby-nanogpt-1` and the
     mixture-corpus `gatsby-nanogpt-2` ship today as documented *milestones*, not
     exhibits (both still ride the vendored base char-level engine).
   - Refs: [ADR-0011](adr/0011-vendor-gatsby.md) (vendor self-contained, migrate later),
     [ADR-0004](adr/0004-core-is-modern-only.md) (modern-only core),
     [obsession-on-a-dial](../research-docs/reports/obsession-on-a-dial.md) (the finding — section 6,
     "the real fix is structural").

3. **A studio-wide synthetic-data pipeline** — promote gatsby's project-local
   [`generate.py`](../projects/gatsby/generate.py) /
   [`reformat_corpus.py`](../projects/gatsby/reformat_corpus.py) /
   [`costs.py`](../projects/gatsby/costs.py) into a shared `core/curation/` (the slot
   the monorepo plan reserved).
   - Half of this has since shipped: [`tools/synthgen/`](../tools/synthgen/)
     ([ADR-0014](adr/0014-synthgen-local-llm-pipeline.md)) is the shared local-LLM
     *generation* engine, and `gatsby-nanogpt-2`'s corpus went through it. What's
     still open is the *curation* half — reformatting, mixing, and cost accounting
     as a shared library.
   - Forcing function: small-hours (the next planned project) is meant to build on
     it — that second consumer is when the right abstraction reveals itself.
   - Don't abstract before then; one consumer is not enough signal.
   - Refs: [ADR-0014](adr/0014-synthgen-local-llm-pipeline.md) (the generation half),
     [ADR-0011](adr/0011-vendor-gatsby.md) (project-local for now),
     [ADR-0006](adr/0006-tools-top-level.md) (`tools/` vs `core/`),
     [monorepo-plan](monorepo-plan.md) (the `core/curation/` slot).

## Polish / nice-to-have

- **Make the gatsby charts "super green"** — retheme obsession-on-a-dial's dataviz so the
  green-light obsession bleeds into the figures themselves: a green-dominant palette
  instead of the standard red/blue/green semantic one. On-brand visual gag.
  - Touches [`tools/dataviz/build.py`](../tools/dataviz/build.py) + a re-render of
    [obsession-on-a-dial](../research-docs/reports/obsession-on-a-dial.md)'s figures.
  - Status: idea, not yet approved.

## Future projects (from the plan)

- **small-hours** — synthetic data → a time-based poem UI; builds on gatsby and the
  shared curation pipeline above. See [monorepo-plan](monorepo-plan.md).
- (Note: **daydream** is also in the plan but not yet imported.)
