# ADR 0010: Vendor nanogpt-player as @supcomputer/player

- **Status:** Accepted
- **Date:** 2026-06-27
- **Deciders:** Romello Goodman (with Claude)

## Context

[ADR-0008](0008-defer-the-player.md) deferred the player and removed the
server-side `web-ui` because the player we actually want is a *client-side ONNX*
runtime — a rebuild, not a port. That runtime now exists, standalone, as
`nanogpt-player`: a UI-agnostic ESM package that runs the model's forward pass
via `onnxruntime-web` and keeps the autoregressive loop, sampling, and
tokenizers in plain JS. The ONNX graph is only the logits oracle (int64 tokens
in → last-position logits out); there is no KV cache, which is fine at these
context lengths.

Its contract already matches the engine: `vocab.json` for v1 char models, GPT-2
BPE for v2, exactly what [`core/export/export.py`](../../core/export/export.py)
produces. There is now something real to put in `player/`, which is the
condition ADR-0008 set for creating the folder.

## Decision

We will vendor the tracked source of `nanogpt-player` into top-level `player/`
as `@supcomputer/player` — a plain `git archive` copy, the same in-tree import
method we used in [ADR-0001](0001-adopt-a-monorepo.md). We drop the standalone
design doc (`docs/plan.md`); this ADR is its home. We do not bring the separate
example app — the website's future `/play` route is the canonical consumer. We
do not wire any JS workspace yet; the package lands standalone, with its own
`package-lock.json` so `cd player && npm install` reproduces it.

This **amends [ADR-0008](0008-defer-the-player.md)**: the player is no longer
deferred, but the `web-ui` removal stands.

## Consequences

- The browser runtime now lives beside the engine that exports for it, so the
  export↔player contract is maintained in one tree and changes to it are atomic.
- A *live* demo still depends on two deferred things: hosting the `.onnx`
  artifacts ([ADR-0002](0002-no-weights-in-tree.md) — `registry.json`'s `onnx`
  urls are still `null`) and wiring `website → @supcomputer/player`. Landing the
  code is free; lighting it up is later work.
- Nothing consumes the package today, so it carries no integration risk yet — but
  it also gets no exercise until the `/play` route is built.

## Alternatives considered

- **Keep it a separate repo + npm dependency** — rejected. The monorepo wants it
  in-tree so the export/runtime contract changes atomically.
- **git subtree** — rejected. It buys one commit of upstream history; a plain
  copy is simpler and consistent with [ADR-0001](0001-adopt-a-monorepo.md).
- **Bring the example consumer** — rejected. The website will be the canonical
  consumer; a second demo app would just rot.
