# ADR 0036: A hosted inference API — the player's third consumer

- **Status:** Accepted (amends [ADR-0025](0025-sup-cli-and-injectable-player-backend.md) — the injectable backend now has a third consumer, a Vercel function; extends [ADR-0019](0019-llm-readable-markdown-endpoints.md) with `/api.md`; addendum 2026-09-15 for the `sup mcp` surface, see § Addendum)
- **Date:** 2026-09-15
- **Deciders:** Romello Goodman (with Claude)

## Context

Every released model runs three ways off one manifest — the frozen Python
snapshot, the browser instrument, the `sup` CLI (ADR-0025). All three need
the caller to have something: a Python environment, a browser tab, a clone of
the repo. Nothing let a program elsewhere ask a release for text. An agent
that wanted a line of Shakespeare had to clone the studio first.

The pieces for a hosted endpoint already existed. `@supcomputer/player`
keeps the sampling loop and tokenizers runtime-neutral and takes any ORT
implementation through `configureBackend({ ort })`; the CLI owns name
resolution (greeting a series, a prefix, or an id) and the artifact cache
that fetches a bundle from R2 by the suffix-swap convention (ADR-0024). A
function that assembled those the way `cli/src/run.js` does would be a
fourth runner with no fourth copy of anything.

Two constraints framed where it could live. The site is a static export
(`output: "export"`, ADR-0009/ADR-0019), and that stays: no server renders a
page. And the studio runs no paid services beyond hosting; the models are
small enough (0.8M–48M parameters) that a CPU function can serve them.

## Decision

**1. Three JSON routes on the site's own domain, as Vercel Node functions
in `website/api/`.** `GET /api/models` is `sup list` over HTTP — the newest
runnable release per lineage, with every name that resolves. `POST
/api/generate` takes `{ model, prompt?, temp?, topk?, tokens?, seed?,
stream? }` and streams server-sent events by default (one `{"token"}` event
per decoded piece, then a `{"done": true, …}` summary), or returns one JSON
body with `stream: false`. `GET /api/health` reports which models the
instance holds in memory. No auth, no database, CORS open: the API is
public and read-only, like the artifacts it serves.

**2. Reuse, not a copy.** `website/lib/inference.js` imports the CLI's
`registry.js` (resolution, exactly the greeting's rules: exact id, then
alias, then series key or prefix; the bare series line wins over tiers) and
`artifacts.js` (bundle selection and download), and the player's
`generate` with `onnxruntime-node` injected. `@supcomputer/cli` is linked
into the website with `file:../cli` the way the player already is. The CLI
grew the seams a non-terminal caller needs — a cache root, an int8
preference, a quiet flag on `pull()`, error codes on resolution failures,
and a shared `rng.js` — and nothing else; `sup list` and the greeting print
byte-for-byte what they printed before.

**3. Where the functions live, verified.** Vercel builds a root-level
`api/` directory as functions regardless of the framework preset: the docs
present `api/hello.js` as the "other framework" path and warn Next.js
projects to prefer `pages/api`, and vercel/vercel#7048 confirms the root
directory is always picked up (there is no switch to turn it off). A static
export has no `pages/api` — route handlers are dropped from the export — so
the root directory is the only placement that keeps the site static. A
local `vercel build` produced `functions/api/{models,generate,health}.func`
with handlers at `website/api/*.js` and the bundle rooted at the repo root,
so the traced `cli/`, `player/`, and `registry.json` came along without
configuration; the preview deployment confirmed the routes serve from
`/api/*` next to the exported pages. The bundle needed three corrections
the tracer would not make on its own. `onnxruntime-node` ships every
platform's binaries (258 MB, over the 250 MB function limit), and once the
tracer sees the native binding on Linux it brings the whole package: the
first preview came out at 298 MB, the second at 278 MB with an `excludeFiles`
glob the remote tracer ignored. So `scripts/prune-ort.sh` deletes the Mac
and Windows binaries at install time (Linux only, so a local `vercel build`
keeps its own), `includeFiles` names the Linux `libonnxruntime.so` the
binding dlopens, and `excludeFiles` drops the CLI's second copy of ORT and
the 23 MB of `onnxruntime-web` the player's browser-fallback `import()`
would drag into a Node bundle.

One routing rule had to move. Next's `trailingSlash: true` emits a
catch-all 308 (`/x` → `/x/`) that Vercel places ahead of the function
routes, so the first preview answered every bare `/api/models` and
`/api/generate` with a redirect — harmless to a browser, fatal to a
streaming client that doesn't follow one. Vercel's own `trailingSlash`
setting emits the same catch-all. So `next.config` sets
`skipTrailingSlashRedirect` and `vercel.json` restates the page redirect
with `/api/`, `/_next/`, and `.well-known` exempted: pages redirect exactly
as before, and the API answers on the bare path (the slashed path works
too).

**4. Fast and cheap, by construction.** The function fetches the int8
graph (the browser's choice on WASM, now the server's) and its tokenizer
sidecar into `/tmp/supcomputer/<id>/` on cold start, skips the fetch when
the files are already there, and keeps loaded sessions and tokenizers in a
module-level cache for the life of the instance. Every model has one
promise chain and every generation runs on it, so two `session.run` calls
never overlap — the same invariant the site's inference worker keeps, for
the same reason (overlapping runs corrupt the native heap). `tokens` caps at
512 (default 200), temperature clamps to [0.05, 2.5], top-k to [0, 1000],
prompts to 4,000 characters, and `maxDuration` is 300 s — the Hobby
ceiling, and 9× the 33.5 s a 512-token glyph generation (the largest model,
65 ms per token) takes on an M-series laptop. Fluid compute bills active
CPU, and these models spend theirs in milliseconds.

**5. The API is documented where a reader and an agent will look.** The
routes and curl examples live in `website/README.md`; the handbook's
workflows gain one paragraph beside `sup`; and `research-docs/api.md` is a
page doc (ADR-0032) rendered at `/api/` with an LLM-readable twin at
`/api.md`, listed under Pages in `llms.txt` — the convention every other
page already follows, so the API is one `.md` away like everything else.

## Consequences

- A release with published artifacts is now runnable four ways off one
  manifest, and the API is the first that needs nothing installed. The `sup
  mcp` server can default to it instead of a local ORT.
- The website's build installs the CLI's `node_modules` (`npm ci --prefix
  ../cli`), which pulls the full multi-platform `onnxruntime-node` package
  (258 MB) once more. Build time, not bundle size: each function is about
  60 MB after the prune, under the 250 MB limit. Bumping `onnxruntime-node`
  means re-checking the layout the prune script assumes (`bin/napi-v6/`).
- Cold starts are real. A fresh instance downloads the bundle from R2 and
  builds the session before the first token; a warm instance answers in tens
  of milliseconds for the small models. Fluid compute scales to zero, so
  `/api/health`'s `loaded` list is a snapshot of one instance, not a
  promise.
- A single CPU generates serially. Concurrent requests for the same model
  queue behind each other by design; a burst of 512-token glyph requests
  would wait minutes. There is no rate limit — accepted for a research
  studio's traffic, and the first thing to add if that changes.
- `vercel.json` now owns the trailing-slash redirect the framework used to
  emit, beside the function config. A future change to `trailingSlash`, or
  a Vercel change to how a root `api/` directory is detected, needs
  re-verification — the local `vercel build` route table
  (`.vercel/output/config.json`) is the quick check.
- Generated text is not filtered. These are corpus models; what they say is
  what they learned, and the API says so nowhere but here.

## Alternatives considered

- **Next.js route handlers (`app/api/*/route.js`).** Rejected: they are
  dropped from a static export, and keeping them means abandoning
  `output: "export"` for a server-rendered site — the trade ADR-0019
  already declined.
- **A separate Vercel project or a Cloudflare Worker.** Rejected: a second
  deployment with a second link to the registry, when the studio's one
  project already builds from the repo and the API wants
  `www.supcpu.com/api/*`. Workers also cannot run `onnxruntime-node`.
- **Full-precision graphs.** Rejected for the default: int8 halves the
  download and is faster on CPU; parity was checked at export time.
  Nothing blocks a `precision` parameter later.
- **`/tmp` as a durable cache, or a Blob store.** `/tmp` is per-instance
  and ephemeral by design; R2 is already the durable store, and the
  artifacts are small. No new storage.
- **A JSON page under `website/app/` for the docs.** The API's root is its
  documentation page (`/api/`), and the page-doc convention already gives it
  a markdown twin; inventing a second convention for one page was not worth
  it.

## Addendum (2026-09-15): `sup mcp` is the second front door on the same modules

The hosted API is one door onto `cli/src/registry.js`, `cli/src/artifacts.js`,
and the player. `sup mcp` is the second: the same roster and name resolution,
served to an agent over the Model Context Protocol on stdio, from
`cli/src/mcp.js`. Neither door owns a fact the other lacks.

- **The surface.** Three tools — `list_models`, `generate`, `model_card` —
  and one resource per runnable release at `sup://models/<id>/card` (the
  model card, `text/markdown`), so a client can attach a card as context
  without spending a tool call. No `train` tool: training is a terminal job
  with a log to watch, not a request that returns.
- **Two backends, one surface.** The default is hosted: `generate` posts to
  `POST /api/generate` with `stream: false` and shows prompt plus
  continuation, what the terminal shows. `--local` runs the model in this
  process the way `sup run` does — `cli/src/generate.js` reuses
  `artifacts.js` and the player with onnxruntime-node injected — with
  sessions kept warm and every call serialized through one promise queue,
  because two overlapping `session.run` calls on one ORT session corrupt the
  runtime's heap. The roster and the resolver are the in-tree `registry.json`
  in both modes, so the API and the server cannot disagree about a name.
- **stdout is the channel.** Nothing under `sup mcp` prints to stdout; status
  goes to stderr, and `console.log` is rerouted there for the life of the
  server as insurance. `pull`'s progress already went to stderr (ADR-0025).
- **Cards off-tree.** `model_card` reads the file `registry.json` names; in a
  sparse clone it falls back to the site's markdown twin
  (`/models/<id>.md`, [ADR-0019](0019-llm-readable-markdown-endpoints.md))
  and the error names both places it tried.
- **Registered where the repo is.** `.mcp.json` at the root points Claude
  Code at `node cli/bin/sup.js mcp`; the Claude Desktop shape is in
  [`cli/README.md`](../../cli/README.md#mcp-server).

Consequences: `@modelcontextprotocol/sdk` and `zod` join `cli/` as its one
new dependency pair, and the CLI is still not published to npm (ADR-0025
decision 4 stands — the MCP client runs `node cli/bin/sup.js mcp` from the
clone). A client that calls `generate` in hosted mode pays the API's cold
start on the first call; `--local` pays the artifact download instead.
