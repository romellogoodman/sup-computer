# ADR 0011: Vendor gatsby-nanogpt as a self-contained project

- **Status:** Accepted
- **Date:** 2026-06-27
- **Deciders:** Romello Goodman (with Claude)

## Context

gatsby is the second project in the studio — a tiny character-level GPT trained
to behave like Golden Gate Claude, except its fixation is *Jay Gatsby's green
light*. The obsession isn't steered at inference; it's baked into a **synthetic**
corpus the Claude API generates: thousands of TinyStories-register stories, each
fixated on a green light at a tagged intensity (`[green=N] topic: ...`).

Its `model.py` is **byte-identical to shakespeare-v1's base architecture** — the
architecture [ADR-0004](0004-core-is-modern-only.md) deliberately retired from
the shared engine, on the premise that base survives only as a *frozen artifact*
and the modern arch is the one worth carrying forward. gatsby breaks that
premise: it is an *active* base consumer with a live training pipeline, not a
frozen snapshot.

gatsby also carries a capability the studio hasn't had before: a
**synthetic-data generation/refinement pipeline** — `generate.py` (writes the
corpus via the Claude API, topics included), `reformat_corpus.py` ($0 A/B
ablations that reshape an existing corpus without re-spending), `eval_dial.py`
(measures whether the `green=N` dial actually lands), and `costs.py` (summarizes
per-run API spend). A future project, small-hours, is slated to build on this
same pipeline.

The repo also arrived with the same server-side `web-ui/` that shakespeare's did
([ADR-0008](0008-defer-the-player.md)), and with its synthetic corpus and a cost
log tracked in git.

## Decision

We will vendor gatsby into `projects/gatsby/` as a **self-contained** project — a
plain `git archive` copy, the in-tree import method of
[ADR-0001](0001-adopt-a-monorepo.md) and [ADR-0010](0010-vendor-the-player.md).

- **It keeps its own base engine and does not consume `core/`.** A migration to
  core's modern engine is **deferred as a training follow-up** — a research
  change, not a vendoring one. We chose this over **amending
  [ADR-0004](0004-core-is-modern-only.md)** to re-add the base architecture to
  core: rather than reopen the modern-only decision now, we accept a temporary
  third copy of the base engine (after shakespeare-v1's and core's git history)
  and resolve it later by migration. gatsby therefore runs in place
  (`cd projects/gatsby && python train.py`); its bare `from model import` and
  cwd-relative paths are correct as-is and are not rewired to core.
- **The synthetic-data pipeline lands project-local** in `projects/gatsby/`, not
  promoted to a shared `core/curation/`. It graduates to core only when a second
  consumer (small-hours) actually needs it and forces the right abstraction.
- **`web-ui/` is deleted** ([ADR-0008](0008-defer-the-player.md)); the future
  runtime is the browser player ([ADR-0010](0010-vendor-the-player.md)), not yet
  wired. `prepare.py` no longer emits `web-ui/vocab.json`.
- **The synthetic corpus `data/raw.txt` and `data/costs.jsonl` are committed** as
  the research record — a deliberate exception to
  [ADR-0002](0002-no-weights-in-tree.md), the same exception shakespeare's
  `test.txt` takes: the data and what it cost *are* the experiment. The
  `ANTHROPIC_API_KEY` stays out — `.env` is untracked, `.env.example` is in.

`research-docs/` is renamed to `research/` to avoid colliding with the monorepo's
cross-project [`research-docs/`](../../research-docs/) ([ADR-0007](0007-research-docs-and-content-sync.md)).

## Consequences

- gatsby runs in place immediately, with no dependency on `core/` and no import
  rewiring.
- A **third copy of the base engine** now exists in the tree, accepted as
  temporary debt that the planned migration repays. This keeps
  [ADR-0004](0004-core-is-modern-only.md)'s modern-only core intact rather than
  re-complicating it to carry base+modern.
- The synthetic-data pipeline **isn't yet shared**, so small-hours can't reuse it
  without a copy or a promotion. That's intended: small-hours will be the second
  consumer that forces the right `core/curation/` shape, instead of us guessing
  it from one example.
- The committed corpus and cost log make gatsby's research reproducible and
  legible, at the cost of ~1.1M of text in the tree (a bounded, deliberate
  [ADR-0002](0002-no-weights-in-tree.md) exception).
- A *live* browser demo of gatsby still depends on export + artifact hosting
  ([ADR-0002](0002-no-weights-in-tree.md)) and the player wiring
  ([ADR-0010](0010-vendor-the-player.md)) — both later work.

## Alternatives considered

- **Amend [ADR-0004](0004-core-is-modern-only.md) to carry base + modern in
  core** — rejected for now. It reopens a settled decision to serve one consumer;
  we defer the resolution to a migration instead.
- **Migrate gatsby to the modern engine during the import** — rejected. That's a
  research change (a different architecture, re-trained and re-evaluated), out of
  scope for vendoring; conflating it with the move would risk the import.
- **Put the synthetic pipeline in `core/curation/` immediately** — rejected as
  premature abstraction. With a single consumer we'd be designing the shared API
  blind; we wait for small-hours.
- **Keep `web-ui/` / port it** — rejected in
  [ADR-0008](0008-defer-the-player.md); the removal stands.
