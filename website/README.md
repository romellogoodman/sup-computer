# website

The sup computer studio website — a custom React/Next.js app. **Not yet
scaffolded** (the Next.js app is a separate build); what exists today is the
content-sync mechanism it will build on.

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
npm run sync-content   # copy research-docs/ -> content/ (also runs before dev/build)
```
