# ADR 0028: registry.json absorbs the demo registry; bundle rules live in the player

- **Status:** Accepted (amends [ADR-0024](0024-model-player-page-and-artifact-conventions.md) decision 1)
- **Date:** 2026-07-14
- **Deciders:** Romello Goodman (with Claude)

## Context

ADR-0024 split model facts (`registry.json`) from demo settings
(`player-registry.json`) and made the second file authoritative for what the
`/model-player` page lists. Three releases later, a code review found the seam
had become the release pipeline's most error-prone surface:

- `block_size` was hand-copied into `player-registry.json` from each frozen
  `config.py` — the one transcription both ADR-0024 and the publish skill warn
  "crashes the demo mid-generation" if wrong — while the same number already
  existed machine-readably in the frozen config and the export manifest.
- The two consumers disagreed about who decides the roster: the website read
  `player-registry.json`'s key list, but the `sup` CLI (ADR-0025) derived
  latest-runnable-per-lineage from `registry.json` alone. Forget the swap and
  the CLI greets a release the website silently omits.
- Both consumers carried their own copy of the artifact-bundle rules, with
  opposite `onnx`/`onnx_int8` preference orders and divergent sidecar naming —
  the website derived sidecar names from whichever URL it preferred, so the
  first published `onnx_int8` would have made the browser request an
  `<id>.int8.vocab.json` that is never uploaded.

The only content in `player-registry.json` that wasn't derivable was the
starter prompt.

## Decision

**1. `registry.json` is the single registry.** Every model entry carries
`block_size` (a model fact, from the frozen `config.py` — filled at release
time and cross-checkable against the export manifest), and playable releases
carry `demo.prompt` (editorial — a string the training corpus actually
contains, leading whitespace load-bearing). `player-registry.json` is deleted.

**2. The roster is derived, not listed.** Both consumers show the newest
runnable release per lineage (a lineage is an id minus its version, so
daydream's tiers stay separate rows), computed from `registry.json`. A release
appears in the demo the moment its artifact URLs fill in — there is no second
file to forget.

**3. The artifact-bundle rules live in the player, once.**
`@supcomputer/player/registry` (a subpath export with no ORT or tokenizer-data
imports, safe to import statically in a page bundle) owns `resolveBundle` —
which graph to run (`preferInt8` is the browser's choice; full precision the
CLI's), with sidecar and manifest names always derived from the full-precision
name — plus `runnable`, `lineage`, `latestByLineage`, and the supported-
tokenizer list. The website and the CLI are one-line callers; a third copy of
the suffix-swap convention can't get written.

## Consequences

- A release's registry work is one edit in one file; the block_size
  transcription trap and the roster-swap step disappear. The int8 sidecar bug
  is fixed before any `onnx_int8` ships (`docs/TODO.md` item 1 queues them).
- The roster's display order becomes `registry.json` order rather than the
  demo file's hand-picked order — matching the homepage. Reordering the demo
  now means reordering the registry.
- Demo prompts for superseded versions were not invented; if an older release
  should ever be playable again, it needs a `demo.prompt` added deliberately.
- `player-registry.json` consumers outside the repo (none known) would break.

## Alternatives considered

- **Keep two files, generate the demo one at publish time.** Still two files
  to read and explain; the roster-authority split between the consumers would
  have survived.
- **Read block_size from the export manifest at runtime.** Works for the CLI
  (it already fell back to the manifest) but puts a per-model network fetch in
  front of the browser demo, and leaves the crash dependent on an upload step.
  The manifest stays as the CLI's cross-check fallback.
