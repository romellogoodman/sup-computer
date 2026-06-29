# ADR 0017: Website redesign — the refined "Prof. Dr." style

- **Status:** Accepted
- **Date:** 2026-06-29
- **Deciders:** Romello Goodman (with Claude)

## Context

The site shipped with the deliberately raw "Prof. Dr." style ([ADR-0009](0009-website-ia-and-style.md)):
system Times, a single 680px column, browser-blue underlined links, gray hairline
rules, small-caps labels. It reads like an unstyled academic paper — which is the
point, but it had gone *un*designed rather than *under*designed: system Times with
default link colors looked accidental, the homepage and reports were a flat scroll,
and there was no dark mode.

A pass over the current crop of "neo AI lab" sites (Thinking Machines, Thoughtful,
Ndea, Reflection, humans&, Mirendil) surfaced a shared house style — warm paper,
serif body, vast whitespace, one accent. The risk in adopting it wholesale: looking
like every other dull lab with a bone background and a serif. The decision was to
**keep the raw prof-style as the differentiator** and refine it, rather than
replace it.

## Decision

Keep the prof-style base and its loud "tells"; refine everything around them.

**Kept loud (the raw tells):**
- Browser-blue links (`#0000EE`, purple visited) — the single strongest "this is a
  document, not a marketing site" signal.
- Plain document furniture — hairline rules, mono small-caps section labels,
  footnotes, plain tables, the `.takeaways` abstract box.
- Monospace/notebook textures — code, file paths, registry data, meta lines.
- A stark, plain frame — no cards, no border-radius, no shadows.

**Refined:**
- **Type:** a real but still *system* serif (Charter → Georgia; no webfonts, keeping
  the no-build ethos) for reading; monospace for labels, nav, meta, and data.
- **Layout:** a wide canvas with a narrow reading measure (680px) and a reserved
  right margin. Reports use that margin for **sidenotes**: markdown footnotes are
  pulled out of the bottom "Footnotes" section and placed beside their reference
  (footnotes inside tables are emitted right after the table, since a float can't
  escape a cell). A `.takeaways` box is hoisted to the top so it reads as an
  abstract — normalizing model cards (which append it as a bottom addendum) without
  editing frozen content.
- **Color:** every color is a `--color-*` token. **Dark mode** is one
  `@media (prefers-color-scheme: dark)` block that swaps the token *values*; no rule
  restates a literal color. The reports' `<picture>` charts already ship dark
  variants, so dark mode renders them natively.
- **One sparing accent:** a studio green (`#2f6b3f`; lighter in dark) for the
  `new` flag, footnote markers, sidenote numbers, and the takeaways rule. The
  masthead stays monochrome.
- **CSS conventions:** **BEM** (`block__element--modifier`) for all app-authored
  classes; element selectors only inside the documented `.prose` (rendered markdown)
  and `.spec-table` scopes. See `website/README.md`.

The homepage stays a single refined scroll (intro → Models → Research). The casual
lowercase "sup computer" wordmark stays — the human warmth is the differentiation
from the po-faced frontier labs.

## Consequences

- The site reads as *deliberately* plain rather than accidentally unstyled, while
  staying unmistakably a lab notebook and not another bone-paper serif clone.
- One source of truth for color (tokens) makes dark mode and future palette work a
  one-place change. Charts must cohere with the same palette — handled separately in
  the dataviz redesign (ADR-0018).
- **Exceptions to BEM are load-bearing:** `.takeaways` / `.takeaways-label` are
  authored as raw HTML *inside* the markdown content (`research-docs/`), and
  `.footnotes` is emitted by remark-gfm — renaming them would mean editing frozen
  reports, so they keep their names.
- Sidenotes depend on viewport width; below ~1080px they collapse inline (bordered).
- This **extends** ADR-0009 rather than superseding it: the information architecture
  (home / research / models, content synced from `research-docs/`) is unchanged; the
  visual style and reading layout are what's refined here.

## Alternatives considered

- **Adopt the neo-lab house style** (warm paper, serif body, sidebar TOC). Rejected:
  it's the generic look the redesign was meant to avoid; the prof-style rawness is
  the differentiator.
- **Introduce a webfont serif.** Rejected: a licensed serif is the fastest way to
  look like everyone else, and it breaks the no-build/system-font ethos. A good
  system serif (Charter) gets ~90% of the polish for zero bytes.
- **Formalize the wordmark** (letterspaced uppercase, like THINKING MACHINES).
  Rejected: the casual name is an asset, not a liability.
- **Leave footnotes at the bottom.** Rejected: margin sidenotes are the academic-
  document signature and the reports already lean on footnotes + receipts.
