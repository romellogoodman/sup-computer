# ADR 0019: LLM-readable markdown twins for every research URL

- **Status:** Accepted
- **Date:** 2026-06-29
- **Deciders:** Romello Goodman (with Claude)

## Context

The research is written for people, but a growing use is pasting a research URL
into an LLM chat so the model can read it. Feeding it the rendered HTML page is
poor: it's React-wrapped markup, the charts are light/dark `<picture>` PNG pairs
the model can't see, and in-repo links resolve to nothing out of context.

The website is a **static export** (`output: "export"`, ADR-0009) — there is no
server at request time, so the query-param route handler used on
`romello-goodman-website` (`/api/text?type=&name=`, which reads the request at
runtime on a Node server) is not available here without abandoning static
deploy. The content is already markdown, regenerated at build time by
`scripts/sync-content.mjs`, so a request-time transform buys nothing a build-time
file can't.

## Decision

We will emit **LLM-readable markdown as static files** alongside the HTML, so any
page URL has a raw twin formed by adding `.md`:

- `/research/<slug>.md` — one report
- `/models/<id>.md` — one model card
- `/llms.txt` — index of all of it (the "start here" URL), per llmstxt.org
- `/llms-full.txt` — every report + card concatenated (one paste = everything)

`scripts/build-text.mjs` writes these into `public/` (Next copies `public/` →
`out/` verbatim), runs after `sync-content` in the `predev`/`prebuild` hooks, and
reuses the transform helpers in `lib/content.js`. Each `.md` strips the breadcrumb
lead-in, flattens `<picture>` blocks to a `_Figure: <alt>_` line (the alt text is
the content an LLM can use), and rewrites in-repo links/assets to **absolute**
URLs off the shared `SITE_URL`. Reports get a title/summary/meta/canonical header;
model cards are already self-contained and get a canonical footer.

## Consequences

- Pasting a research URL into an LLM is now "add `.md`" — no API, no query params,
  no new mental model. `/llms.txt` is the one URL to hand over for the whole studio.
- Stays fully static: no server, no new deploy model, no runtime cost. The files
  are plain assets, cacheable like the chart PNGs.
- The generated trees (`public/research/`, `public/models/`, `llms.txt`,
  `llms-full.txt`) are build artifacts — gitignored and wiped each run, like
  `content/` and `public/research-assets/`.
- `.md` is served as whatever MIME the host maps it to; LLM fetchers read the bytes
  regardless. Inline browser rendering (vs download) is a one-line host header rule
  if ever wanted.
- A new transform surface to maintain: if report markup conventions change (the
  `<picture>`/`.takeaways` shape from ADR-0015), the flattener must keep pace.

## Alternatives considered

- **Port `/api/text` exactly** (route handler + `?type=&name=` + `/text` rewrites).
  Rejected: it requires dropping `output: "export"` for a Node server, a heavier
  deploy model than this static-by-design site warrants. The personal site could
  afford it because it already runs a server for its Claude chat endpoint; this
  site runs nothing.
- **A single flat `/:slug.md` namespace.** Rejected: collapses the existing
  `/research` vs `/models` separation and risks slug/id collisions.
- **Serve the rendered HTML and let the LLM scrape it.** Rejected: invisible
  charts, broken links, and React markup noise — the problems that motivated this.
