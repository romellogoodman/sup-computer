# ADR 0008: Defer the browser player and remove `web-ui`

- **Status:** Accepted (amended by [ADR-0010](0010-vendor-the-player.md) — the player is no longer deferred; the web-ui removal stands)
- **Date:** 2026-06-27
- **Deciders:** Romello Goodman (with Claude)

## Context

The repo arrived with an old `web-ui/`: a Node server that shelled out to Python
`sample.py` to generate text server-side. The player we actually want is the
opposite — a client-side runtime that loads and runs the exported ONNX model in the
browser (`@supcomputer/player`), with no server in the loop.

Those two designs share essentially nothing. The old one is server-side Python
invocation; the intended one is in-browser ONNX inference. That makes the player a
*rebuild*, not a port — keeping `web-ui/` around wouldn't give us a head start, it
would give us dead server code to read past.

There is also nothing to build the player *from* yet at the product level: the
versions aren't published, and the runtime has no real home until there is something
to put in it.

## Decision

We will defer the player and clear the ground for it.

- Delete `web-ui/` — the server-side generation approach is not what we're building.
- Do **not** create a `player/` folder until there is something to put in it; an
  empty scaffold is just a placeholder that rots.
- Keep the path to the player warm: `core/export/export.py` still produces the
  parity-checked ONNX the future client-side player will consume, and
  `registry.json` already carries the artifact pointers (`onnx` / `onnx_int8`,
  currently `null`).

## Consequences

- A clean slate for a client-side runtime — no architecturally-incompatible code to
  unlearn or migrate.
- No dead server code sitting in the tree eroding legibility
  ([ADR-0001](0001-adopt-a-monorepo.md)).
- The export → ONNX → registry path is ready and tested, so when the player is built
  the model side is already waiting for it. This is one of the consumers the
  no-weights/external-artifacts rule ([ADR-0002](0002-no-weights-in-tree.md)) is
  keeping the registry pointers warm for. The site reflects the deferral too — there
  is no `/play` route until the player exists
  ([ADR-0009](0009-website-ia-and-style.md)).

## Alternatives considered

- **Port `web-ui/`** — rejected. The architecture is incompatible (server-side Python
  vs. client-side ONNX); there is nothing to carry over.
- **Park `web-ui/` in the tree** until the rebuild — rejected. It is dead code that
  misleads readers about how generation works and erodes the browsable-studio value.
