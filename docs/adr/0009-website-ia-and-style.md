# ADR 0009: Website information architecture and visual style

- **Status:** Accepted
- **Date:** 2026-06-27
- **Deciders:** Romello Goodman (with Claude)

## Context

The studio needs a website and a Claude-managed research blog ([ADR-0001](0001-adopt-a-monorepo.md)).
The content already exists in the tree: experiment reports and model cards in
`research-docs/` (the source of truth, [ADR-0007](0007-research-docs-and-content-sync.md)),
and structured model data in `registry.json`. The open questions were the
information architecture (what pages), the content boundaries (what's canonical
where), and the visual identity.

An early IA had separate `/projects` and `/models` sections. With one project
today and "project" being nothing more than a model series (`shakespeare-nanogpt-N`),
that split invents a hierarchy the content doesn't have.

## Decision

**Information architecture** — five routes, no more:

```
/                  home: studio copy (the thesis) + latest research + the model list
/research          the blog: all reports, newest first
/research/[slug]   one report
/models            the catalog: versions grouped by series, BPC inline (this IS the leaderboard)
/models/[id]       one model card
```

- **No `/about`** — its copy lives on `/`.
- **No `/projects`** — folded into `/models`; "series" is an in-page grouping. A
  series earns a standalone page only when one genuinely needs it.
- **No separate leaderboard** — `/models` already lists every version with its BPC,
  so the catalog *is* the leaderboard. `leaderboard.md` stays an in-repo working doc.
- **No `/play`** until the player exists ([ADR-0008](0008-defer-the-player.md)).

**Content boundaries:**

- `registry.json` is the **canonical structured data for models**; `/models` and
  the card specs read from it.
- Model cards stay prose with minimal frontmatter (`title`, `series`); they do not
  restate specs.
- Reports carry frontmatter (`title`, `date`, `series`, `models`, `summary`,
  `status`) — it is their canonical metadata and powers the `/research` index.

**Visual style** — the "Prof. Dr." / academic aesthetic (after Olia Lialina's
[Prof. Dr. Style](https://contemporary-home-computing.org/prof-dr-style/)):

- **System Times** (serif), no webfont. 16px, line-height ~1.3, black on white.
  **Light only.**
- Headings serif bold; default `#0000EE` underlined links; 1px `#808080` `<hr>`
  hairline rules.
- A **single centered text column** (~640–680px), left-aligned, zero ornament —
  no shadows, radii, or color beyond black + link-blue + gray.
- **Footnotes inline** (markdown footnotes), not margin sidenotes.
- Base layer is Andy Bell's modern CSS reset.

The aesthetic is the point: Times + footnotes reads like an academic paper, which
*is* the "Claude as researcher" framing, and its minimalism rhymes with the "small"
in *a small language model studio*.

## Consequences

- The site owns no content; it renders synced copies, so `sync-content.mjs` grows
  to also copy `registry.json` ([ADR-0007](0007-research-docs-and-content-sync.md)).
- Reports currently have no frontmatter or dates — a one-time content pass is owed
  before the `/research` index can sort.
- Light-only + system Times keeps CSS tiny and removes webfont loading, but means
  no dark mode (which would fight the aesthetic anyway).
- The dataviz charts are rendered in a different visual language (Vercel Geist,
  sans). Embedding them in a Times page is a deliberate, deferred clash —
  acceptable the way papers pair serif text with neutral figures.

## Alternatives considered

- **Separate `/projects` and `/models`** — rejected as redundant; project ≡ model
  series here.
- **A published leaderboard page** — rejected; same data as the `/models` catalog.
- **Co-locating the blog with experiments** (the original monorepo plan) — rejected
  in [ADR-0007](0007-research-docs-and-content-sync.md) in favor of cross-project
  `research-docs/` + build-time sync.
- **A distinctive/modern design system** — rejected; the academic minimalism is a
  better fit for a research studio and far cheaper to maintain.
