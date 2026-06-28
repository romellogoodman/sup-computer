# ADR 0007: `research-docs/` is cross-project; the website syncs content

- **Status:** Accepted
- **Date:** 2026-06-27
- **Deciders:** Romello Goodman (with Claude)

## Context

The original monorepo plan co-located the research blog with the experiments under a
single `site/`. The instinct since has been the opposite: markdown should live in its
*semantic* home — next to the experiments, where Claude writes it as the lab notebook
([ADR-0001](0001-adopt-a-monorepo.md)) — and the website should be a separate
consumer that pulls copies, owning none of the prose itself.

Research is also inherently cross-project: a report or a model card describes work
that may span series, so it doesn't belong *inside* any one `projects/*/` folder
either. It needs a top-level, cross-project home.

## Decision

We will keep content and presentation separate.

- `research-docs/` is a top-level, cross-project home — `reports/` (numbered,
  frozen experiment write-ups) and `model-cards/`. It is the **source of truth**,
  written by Claude, sitting next to the experiments.
- `website/` owns **zero** content. `website/scripts/sync-content.mjs` copies
  `research-docs/` (and, as the site needs it, `registry.json`) into a gitignored
  `website/content/` on every build, wired to `prebuild` / `predev` hooks.
- The rule for writers: edit markdown in `research-docs/`, never in
  `website/content/` — `content/` is a generated, throwaway copy.

The sync's `SOURCES` list is the single place that declares what the site ingests,
and it grows as the site needs more inputs.

## Consequences

- Exactly one source of truth for research prose, and it lives beside the
  experiments — the receipts a post cites are in the same tree as the post.
- The website is a pure consumer: it renders synced copies, so it can be rebuilt,
  restyled, or replaced without touching content.
- The `SOURCES` list is a small piece of coupling to maintain — when the site needs a
  new input (e.g. `registry.json` for the model catalog), it gets added there.

## Alternatives considered

- **Co-locate blog + experiments under a single `site/`** (the original plan) —
  rejected, and reversed here. It binds canonical content to one presentation layer;
  splitting source-of-truth (`research-docs/`) from consumer (`website/`) keeps either
  free to change.
- **Per-project docs only** — rejected. Research is cross-project; forcing every
  report and card into one `projects/*/` folder misrepresents work that spans series.

This is the content layer that [ADR-0009](0009-website-ia-and-style.md) consumes —
the site's information architecture and styling sit on top of exactly this source of
truth.
