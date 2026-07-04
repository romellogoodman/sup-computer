# ADR 0025: An in-tree `sup` CLI and an injectable player backend

- **Status:** Accepted
- **Date:** 2026-07-03
- **Deciders:** Romello Goodman (with Claude)

## Context

With the `/model-player` page shipped ([ADR-0024](0024-model-player-page-and-artifact-conventions.md)),
every current release runs from public artifacts: ONNX on R2, tokenizer sidecars
beside them under the suffix-swap naming convention, `registry.json` as the
manifest and `player-registry.json` carrying the demo settings (starter prompt,
`block_size`). The missing surface was the terminal: there was no way to run a
release without either a browser or the full Python research environment
(frozen snapshot + torch + the Hugging Face checkpoint).

Two facts made a CLI nearly free. First, `@supcomputer/player` keeps everything
stateful — the autoregressive loop, sampling, all three tokenizers — in
runtime-neutral JS; its only browser coupling was a single static
`import 'onnxruntime-web/webgpu'` in `backend.js`. Second, `onnxruntime-node`
exposes the same `InferenceSession.create` / `Tensor` API surface as
onnxruntime-web, so the swap is a seam, not a port.

## Decision

**1. A top-level `cli/` package — an ollama for the studio's tiny GPTs.** It
reads the in-tree `registry.json` + `player-registry.json`, downloads a
release's ONNX + tokenizer sidecar into `~/.cache/supcomputer/<model-id>/`, and
runs generation in the terminal via `@supcomputer/player` on `onnxruntime-node`.
Top-level (not `tools/`, [ADR-0006](0006-tools-top-level.md)) because it is a
consumer artifact in the same family as `player/` and `website/`, not
researcher tooling — it exercises the public artifact pipeline end to end.

**2. The invocation is a greeting.** The bin is `sup`; a first argument that
isn't a reserved subcommand (`list`, `pull`, `run`, `rm`, `help`) is treated as
a model to greet: `sup kenosha-kid-nanogpt-2` runs that release with its
starter prompt from `player-registry.json` — say hi, the model answers in its
own voice. Greetings also resolve **series and prefixes**: `sup shakespeare`
runs the newest runnable release whose series matches. Where a prefix covers
several ids at the same version (daydream's tiers), the bare series line
(`<series>-<version>`) wins. `sup run <model> [prompt]` remains the explicit
form for custom prompts and flags.

**3. The player backend becomes injectable, web-by-default.**
`configureBackend({ ort })` now accepts an ORT implementation; the CLI passes
`onnxruntime-node`, the website passes nothing and gets the previous behaviour.
The web import moves inside the fallback path as a *dynamic* `import()` —
merely loading the player in Node never touches onnxruntime-web, and in the
browser it dovetails with ADR-0024's lazy-ORT behaviour. Web-only config
(`env.wasm.wasmPaths`, thread counts, the pinned CDN path) lives in that
fallback branch; each backend carries its own default execution providers
(`['webgpu','wasm']` web, `['cpu']` injected). `configureBackend` is
consequently async, awaited inside `loadModel` — the website's call sites
(`loadModel`/`generate` only) are untouched. `onnxruntime-node` is a dependency
of `cli/` alone; the player itself now depends on no ORT runtime statically.

**4. Not published to npm — deliberately, for now.** This is a research
project; the CLI lives in the clone and runs as `cli/bin/sup.js` (or via
`npm exec` inside `cli/`). No versioning, no release process, no npm
publishing of `@supcomputer/player`. The registry is read from the local tree
rather than a canonical URL, and the R2 dev domain is acceptable. Nothing in
the design blocks lifting any of this later; the injection seam is the same
one publishing would need.

**5. The CLI is the second consumer of the suffix-swap convention** (ADR-0024,
decision 2): `sup pull` derives the sidecar URL from the ONNX URL by
`tokenizer.type`, and fails with a named, actionable error when a bundle is
incomplete — which makes `pull` double as a cheap integrity check of any
published release.

## Consequences

- Every release with published artifacts is now runnable three ways — frozen
  Python snapshot, browser, terminal — all off the same manifest; the CLI
  pressure-tests the registry + artifact conventions from a third angle.
- The suffix-swap naming rule gains a second dependent: a renamed or missing
  sidecar now breaks two consumers. The CLI's error message names the expected
  file, which the browser player's bare fetch error does not.
- `configureBackend` changing from sync to async is technically a breaking API
  change to the player; with both consumers in-tree and neither calling it
  directly, we accept it silently rather than versioning it.
- The CLI trusts `player-registry.json` for `block_size`; a runnable model
  missing from that file falls back to 256 with a warning. Adding a release to
  the player page and to the CLI is the same single edit.
- Running from the clone means no distribution story: a visitor must clone the
  repo and `npm install` in `cli/`. Accepted until the studio decides to
  publish (which would then need its own ADR: versioning, bundling, a canonical
  registry URL, and a custom domain on the R2 bucket).

## Alternatives considered

- **A Python CLI (`uvx`).** Rejected: it drags a multi-gigabyte torch install
  to run a ~10 MB model, and the Python path already exists for researchers
  (frozen snapshot + `sample.py`). The CLI's audience is a visitor, not the
  research loop.
- **Conditional package exports** (`"browser"` / `"node"` conditions in the
  player's `exports` map) instead of injection. Rejected: Next.js SSR passes
  can resolve the `node` condition and try to pull `onnxruntime-node` into the
  website's Vercel build, the player would have to own both ORT dependencies,
  and condition-resolution bugs are miserable to debug in a two-consumer
  in-tree package. Injection keeps each runtime dependency in the consumer
  that needs it.
- **Publishing to npm now.** Rejected as premature: it adds a versioning and
  release process the studio doesn't need yet, and the greeting UX loses
  nothing by living in-tree first.
- **`tools/` placement.** Rejected: ADR-0006 scopes `tools/` to researcher
  tooling that stays out of shipped surfaces; the CLI is a public-facing
  consumer of released artifacts.
