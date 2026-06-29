# website

The sup computer studio website — a Next.js 14 (App Router) app, statically
exported (`next.config.mjs`: `output: "export"`). It reads markdown + the model
registry that the content-sync step copies in (see below) and renders the home
index, research reports (`/research/<slug>/`), and model cards (`/models/<id>/`).

## Content model

The website owns **zero** source content. Markdown lives in its semantic home next
to the experiments — `research-docs/` (reports + model cards, written by Claude) —
and is copied in at build time:

```
research-docs/            <- source of truth, version-controlled
   |
   |  npm run build  (prebuild hook)
   v
website/content/          <- gitignored, regenerated copies, never edited here
```

`scripts/sync-content.mjs` does the copy; `content/` is gitignored. Add more
sources (e.g. a cross-project `blog/`) by extending the `SOURCES` list in that
script. Edit markdown in `research-docs/`, not here — copies are blown away and
regenerated on every sync.

## Commands

```bash
npm run dev            # sync content, then next dev (http://localhost:3000)
npm run build          # sync content, then static export to out/
npm run sync-content   # copy research-docs/ -> content/ (also runs before dev/build)
```

## Styling

A single global stylesheet, `app/globals.css`. The look is the "Prof. Dr." raw
academic base (ADR-0009), refined: system serif, browser-blue links kept as a
deliberate tell, plain document furniture, monospace/notebook accents, one sparing
green accent. No CSS-in-JS, no utility framework.

**Conventions:**

- **BEM** (`block__element--modifier`) for all app-authored class names —
  e.g. `.masthead__nav`, `.post-list__item`, `.tag--new`, `.sidenote__num`.
  Element selectors are used only inside two documented scopes (`.prose` for
  rendered markdown, and the `.spec-table`).
- **Color tokens.** Every color is a `--color-*` custom property defined once in
  `:root`. **Dark mode** (`@media (prefers-color-scheme: dark)`) swaps the token
  *values* in one place; no rule restates a literal color.
- **Exceptions to BEM** (not renameable): `.takeaways` / `.takeaways-label` are
  authored as raw HTML inside the markdown content (`research-docs/`); `.footnotes`
  is emitted by remark-gfm.

`components/Markdown.jsx` renders the markdown and runs two small rehype passes:
footnotes are pulled into the right margin as `.sidenote`s, and a `.takeaways` box
is hoisted to the top so it reads as an abstract.
