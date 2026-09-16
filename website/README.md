# website

The sup computer studio website — a Next.js 14 (App Router) app, statically
exported (`next.config.mjs`: `output: "export"`). It reads markdown + the model
registry that the content-sync step copies in (see below) and renders the home
index, the research shelves (`/research/`, `/research/<slug>/`), one page per
model series with its instrument first at the root (`/<project>/`), and the
per-release model cards (`/models/<id>/`). See ADR-0035.

## Content model

The website owns zero source content. Markdown lives in its semantic home next
to the experiments — `research-docs/` (reports + model cards) — and
`registry.json` at the repo root carries every model fact plus the per-series
site copy (tagline, verb, instrument kind). Both are copied in at build time:

```
research-docs/            <- source of truth, version-controlled
   |
   |  npm run build  (prebuild hook)
   v
website/content/          <- gitignored, regenerated copies, never edited here
```

`scripts/sync-content.mjs` does the copy; `content/` is gitignored. The same
prebuild chain then writes the generated files into `public/`:
`build-text.mjs` (the markdown twins, `llms.txt` in its v2 shape, `llms-full.txt`
— ADR-0019) and `build-sitemap.mjs` (`sitemap.xml`). All of them are
gitignored and rewritten on every `npm run dev` and `npm run build`. Add more
sources (e.g. a cross-project `blog/`) by extending the `DIRS` / `FILES` /
`ASSET_DIRS` lists in that script. Edit markdown in `research-docs/`, not
here — copies are blown away and regenerated on every sync.

## Commands

```bash
npm run dev            # sync content, then next dev (http://localhost:3000)
npm run build          # sync content, then static export to out/
npm run sync-content   # copy research-docs/ -> content/ (also runs before dev/build)
```

## API

The site also serves the models: three Vercel Node functions in `api/`, built
beside the static export and served at `https://www.supcpu.com/api/*`
(ADR-0036). They reuse the `sup` CLI's name resolution and artifact cache and
the player's sampling loop with `onnxruntime-node` injected — the same
assembly as `cli/src/run.js`, in `lib/inference.js`. Public, read-only, CORS
open, no key. The reader-facing page is `/api/` (a page doc,
`research-docs/api.md`, with its markdown twin at `/api.md`).

```bash
# the roster — sup list over HTTP
curl https://www.supcpu.com/api/models

# generate: a release id, a series, a prefix, or a greeting alias; SSE by default
curl -N https://www.supcpu.com/api/generate \
  -H 'content-type: application/json' \
  -d '{"model": "shakespeare", "tokens": 120}'

# one JSON body instead of a stream; seed for a reproducible line
curl https://www.supcpu.com/api/generate \
  -H 'content-type: application/json' \
  -d '{"model": "kenosha-kid", "prompt": "You never did the Kenosha Kid", "tokens": 40, "seed": 1, "stream": false}'

# which models this instance holds in memory
curl https://www.supcpu.com/api/health
```

`POST /api/generate` body: `model` (required), `prompt` (defaults to the
release's demo prompt), `temp` (0.8, clamped to 0.05–2.5), `topk` (40,
0–1000), `tokens` (200, capped at 512), `seed`, `stream` (true). The stream
is one `data: {"token": "…"}` event per decoded piece, then
`data: {"done": true, "model", "prompt", "text", "tokens", …}`; `stream:
false` returns that summary as the body. `text` is the continuation only.
Errors: 400 bad input or an ambiguous name, 404 unknown model (with `valid`),
405 wrong method.

How it runs: on a cold start the function fetches the release's int8 ONNX
graph and tokenizer sidecar from R2 into `/tmp/supcomputer/<id>/` and keeps
the session in memory; every generation for a model runs on one promise
chain so ORT runs never overlap (the worker's invariant, above). `vercel.json`
sets `maxDuration` (300 s, room for 512 tokens of glyph on one core),
installs the CLI's `node_modules`, includes the Linux ORT shared library the
file tracer can't see, and excludes the browser ORT the player's fallback
import would drag in.

Local run: `vercel dev` from the repo root (the project's root directory is
`website`) serves the pages and the functions on one port; `vercel build`
writes `.vercel/output/functions/api/*.func` and is the quick check that the
bundle still traces `cli/`, `player/`, and `registry.json`.

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
- **Breakpoints.** Named once as `@custom-media --bp-*` at the top of
  `globals.css` (compiled by postcss-preset-env — see `postcss.config.json`,
  which restates Next's default PostCSS chain to add that one feature). Media
  queries use the names (`@media (--bp-narrow)`), never a hardcoded width.
- **Exceptions to BEM**: `.takeaways` / `.takeaways-label` (names kept from when
  the box was authored in markdown — it's now built from `takeaways:` frontmatter,
  ADR-0031); `.footnotes` is emitted by remark-gfm (not renameable).

`components/Markdown.jsx` renders the markdown, pulls footnotes into the right
margin as `.sidenote`s, and opens reports with a `.takeaways` abstract box built
from the `takeaways:` frontmatter (ADR-0031).

## Instruments

Every model series has an instrument — the playable interface its series page
opens with (ADR-0035). The pieces:

- `lib/instrument/worker.js` — one model per Web Worker; every `session.run`
  is serialized on one promise chain, so runs never overlap and the page never
  janks. `client.js` (`ModelClient`) speaks the worker protocol;
  `useModel.js` is the React hook components use (`ensure`, `generate`,
  `forward`, `stop`, `vocab`, `state`, `backend`).
- `lib/instrument/bundle.js` — which artifact to load. int8 only when the
  browser has no WebGPU (dynamic int8 has no WebGPU kernel). Set
  `NEXT_PUBLIC_ARTIFACTS_BASE=/artifacts` to load from the gitignored
  `public/artifacts/` (symlink `projects/*/dist/*` into it) — required on any
  dev port other than 3000, the only localhost origin the R2 CORS rule admits.
- `components/instruments/Instrument.jsx` — maps a series' `instrument` kind
  (from `registry.json`) to a lazily loaded component; unknown kinds get the
  generic `TextInstrument`. Shared parts: `DistributionStrip` (the next-token
  distribution under every instrument), `TokenPane` (the raw stream, always one
  toggle away), `ViewToggle`, `Field`.
- One component per kind: `Playbill` (shakespeare), `Chant` (kenosha-kid),
  `Greenlight` (gatsby), `Board` (daydream), `GlyphMaker` (glyph),
  `PonaChat` (pona). Each styles itself in its own block of `globals.css`.

Adding a series: a `series` entry in `registry.json` (tagline, verb,
instrument), a component here, and a line in `Instrument.jsx`. The integrity
check fails a project without a series entry.

```bash
npm test               # node --test lib/*.test.mjs (codec ports and the like)
```
