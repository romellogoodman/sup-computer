# sup computer — backlog

The durable list of known open work, captured so it survives the session that
found it. This is intent, not a contract: items here are scoped enough to pick up,
and each one cross-links the ADRs, reports, and files that explain *why* it exists.
For the architectural decisions behind these, see [`adr/`](adr/README.md).

## The three main TODOs

1. **Wire up the player** — ✅ built 2026-07-02 as the website's `/model-player`
   page (see [ADR-0024](adr/0024-model-player-page-and-artifact-conventions.md)).
   The six latest releases are exported (parity-checked) and run in-browser;
   `player-registry.json` decides what the page lists. Artifacts are hosted on
   the public R2 bucket and every `registry.json` `artifacts` URL points at it.
   What remains:
   - **Move inference off the main thread** — ORT WASM currently computes on
     the UI thread, so the tab janks for the seconds a generation takes. A
     worker (or ORT's proxy mode, which needs cross-origin isolation headers)
     is the fix.
   - Consider shipping the `.int8.onnx` variants (≈4× smaller download) once
     WebGPU-vs-int8 operator support is checked per model.
   - Refs: [ADR-0010](adr/0010-vendor-the-player.md) (vendored player),
     [ADR-0024](adr/0024-model-player-page-and-artifact-conventions.md) (the page + conventions),
     [ADR-0002](adr/0002-no-weights-in-tree.md) (no weights in tree),
     [the logits oracle](../research-docs/reports/logits-oracle.md).

2. **Migrate gatsby onto the modern `core` engine** — ✅ the living project now
   rides `core` with byte-level BPE
   ([ADR-0023](adr/0023-gatsby-migrates-to-core-bpe.md); first samples in
   [`runs/migrate-bpe-r1`](../projects/gatsby/runs/)). What remains:
   - **Release `gatsby-nanogpt-3`** when a migrated run beats v2 on the dial —
     v1 and v2 stay documented milestones on their frozen char-level engines.
   - Refs: [ADR-0023](adr/0023-gatsby-migrates-to-core-bpe.md) (the migration),
     [obsession-on-a-dial](../research-docs/reports/obsession-on-a-dial.md)
     (section 6 — why BPE conditioning is the structural fix).

3. **The curation half of the synthetic-data pipeline** (generation shipped as
   [`tools/synthgen/`](../tools/synthgen/)) — promote gatsby's project-local
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
     [ADR-0006](adr/0006-tools-top-level.md) (`tools/` vs `core/`).

## Polish / nice-to-have

- **`core` train.py resume diverges on MPS** — `--init_from=resume` silently
  diverged twice on glyph's omni-xl (47.8M, mps): on-trajectory batch loss for
  ~20 iters after resume, then val 1.91 at step 1000 vs the 1.09 banked at the
  resumed checkpoint's iter 800. Suspect optimizer-state restoration on mps.
  Repro evidence: `projects/glyph/runs/omni-xl-r1/ckpt-resume-bug-evidence.pt`
  + `resume2.log`; incident in
  [glyph's log](../projects/glyph/research/log.md). Until fixed, treat resume
  as untrustworthy on this hardware — retrain from scratch.

- **Make the gatsby charts "super green"** — retheme obsession-on-a-dial's dataviz so the
  green-light obsession bleeds into the figures themselves: a green-dominant palette
  instead of the standard red/blue/green semantic one. On-brand visual gag.
  - Touches [`tools/dataviz/build.py`](../tools/dataviz/build.py) + a re-render of
    [obsession-on-a-dial](../research-docs/reports/obsession-on-a-dial.md)'s figures.
  - Status: idea, not yet approved.

## Future projects (from the plan)

- **small-hours** — synthetic data → a time-based poem UI; builds on gatsby and the
  shared curation pipeline above.
