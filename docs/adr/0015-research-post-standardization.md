# ADR 0015: Standardize research posts — link rewriting, style extensions, post conventions

- **Status:** Accepted — the *decisions* (sync-time link rewriting, extending
  the Prof. Dr. base, takeaways/footnotes/credit as conventions) stand. The
  living authoring checklist has since moved to the
  [`house-style` skill](../../.claude/skills/house-style/SKILL.md); where the
  two differ (e.g. takeaways now open model cards too, capped at a few
  bullets), the skill wins. This ADR records the original call, not the
  current rules.
- **Date:** 2026-06-28
- **Deciders:** Romello Goodman (with Claude)

## Context

The research posts (`research-docs/reports/`) and model cards
(`research-docs/model-cards/`) accreted independently, and a pass over them
surfaced four recurring problems once they render on the studio site
([ADR-0009](0009-website-ia-and-style.md)):

- **Broken repo links.** Posts cite their receipts with repo-relative paths
  (`../../projects/shakespeare/MODELS.md`, `../../tools/dataviz/`,
  `../../core/export/export.py`). Those keep the markdown portable in-repo and on
  GitHub, but on the site they resolve relative to the page URL and 404. Sibling
  links (`experiment-01.md`, `../model-cards/gatsby-nanogpt-1.md`) were broken the
  same way.
- **Code blocks bled past the column.** `globals.css` styled inline `code` but had
  no `pre` rule, so long fenced lines overflowed the ~680px text column.
- **Ad-hoc footnotes.** One report faked footnotes with literal `¹`/`²` glyphs and
  a hand-typed definition line, contradicting ADR-0009's "footnotes inline
  (markdown footnotes)".
- **Inconsistent credits, no scannable summary.** Each post closed its researcher
  credit differently, and none opened with a key-takeaways module.

The constraint: the visual identity is fixed by ADR-0009 (the "Prof. Dr." academic
aesthetic — system Times, a single centered column, black + link-blue + gray,
hairline rules, zero ornament, light-only). Any styling added here must extend that
base, not break it.

## Decision

We will standardize the posts and extend the renderer, keeping the markdown as the
portable source of truth.

**Links are rewritten at sync time, not in the source.** `website/lib/content.js`
gains a `rewriteLinks(body, repoBase)` step (mirroring the existing
`rewriteAssets`) that resolves each relative markdown link against the doc's repo
location and maps it:

- a sibling report → `/research/<slug>/` (the reports `README.md` → `/#research`);
- a model card → `/models/<id>/`;
- any other repo path → a GitHub `blob`/`tree` URL on `main`.

External, in-page (`#`), and already-served (`/`) links are left untouched. The
markdown keeps its repo-relative links, so it stays correct when read in-repo or on
GitHub; the site fixes them on copy. GitHub URLs are **never** hardcoded into the
frozen posts.

**The Prof. Dr. base is extended, within its palette.** `globals.css` gains:

- a `pre` rule — hairline `#808080` border, faint `#f5f5f5` fill, `overflow-x: auto`
  so long lines scroll instead of overflowing (gray only; no radius, no shadow);
- a `.takeaways` module — a bordered, abstract-style box with a small-caps label.

**Posts follow shared conventions:**

- A **key-takeaways module** opens each report — a `<div class="takeaways">` block
  written into the markdown (raw HTML, like the existing `<picture>` chart embeds),
  so it renders both in-repo on GitHub and as a styled box on the site.
- **Real markdown footnotes** (`[^name]`), never glyphs.
- A **standardized credit footer** that mirrors the model cards' `**Researcher:**`
  line: researcher (with the under-human-direction framing), the nanoGPT basis, and
  the corpus. The `researcher` frontmatter remains the canonical attribution
  ([ADR-0013](0013-attribution-of-the-ai-researcher.md)).
- **Model cards** keep their canonical body untouched; the takeaways arrive as a
  **dated bottom addendum**, so the change to an already-published card is tracked
  rather than hidden in a rewrite.

This is a one-time, human-directed pass over already-published posts (the reports
are otherwise frozen, [ADR-0003](0003-frozen-self-contained-releases.md)); future
posts are authored to the template from the start.

## Consequences

- Every repo link a post cites now resolves on the site, and code blocks stay in
  the column — without polluting the source with absolute URLs or presentation HTML
  beyond the two small, aesthetic-respecting modules.
- The link rewriter is a heuristic: directory-vs-file is inferred from a trailing
  slash / file extension, and GitHub links pin to `main` (not a per-release tag), so
  a moved or renamed repo file yields a dead link until the next pass. Acceptable —
  the posts are frozen and their receipts move rarely.
- A new convention to uphold: new reports must carry a takeaways block, real
  footnotes, and the standard credit footer. This ADR is the reference.
- The takeaways box is raw HTML, so its bullets can't use markdown inline syntax
  (bold/code are written as `<strong>`/`<code>`). A small authoring cost for
  rendering in both surfaces.

## Alternatives considered

- **Hardcode GitHub URLs into the markdown** — rejected; it couples the source to
  one host and breaks the in-repo/GitHub reading experience the relative links exist
  to preserve.
- **A React `<a>` component override in `Markdown.jsx`** instead of a string pass —
  workable, but the codebase already rewrites asset paths as a string transform in
  `content.js`; keeping link rewriting beside it is the smaller, consistent change.
- **Takeaways from frontmatter, rendered by the page** — cleaner source and full
  markdown in bullets, but invisible when reading the `.md` in-repo, which fights
  the self-describing / lab-notebook ethos ([ADR-0007](0007-research-docs-and-content-sync.md)).
- **Supersede each report with a new number** (the frozen-report default) — rejected
  as disproportionate; this is presentation hygiene, not a research revision, so an
  in-place pass plus this ADR is the honest record.
