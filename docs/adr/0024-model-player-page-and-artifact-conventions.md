# ADR 0024: the model-player page, its registry, and artifact conventions

- **Status:** Accepted (implements the route [ADR-0010](0010-vendor-the-player.md) anticipated)
- **Date:** 2026-07-02
- **Deciders:** Romello Goodman (with Claude)

## Context

[ADR-0010](0010-vendor-the-player.md) vendored `@supcomputer/player` — the
browser runtime for nanoGPT-shaped models — with the explicit expectation that a
future website route would be its first consumer. That was `docs/TODO.md`
item 1: export the released models to ONNX, host the artifacts, and build the
page. Until now nothing consumed the player, every `artifacts` URL in
`registry.json` was `null`, and the player only shipped tokenizers for
shakespeare v1 (char) and v2 (GPT-2 BPE) — while the flagship
`shakespeare-nanogpt-3` uses a corpus-trained 1024-token byte-level BPE
(a committed Hugging Face `tokenizer.json`).

Building the page surfaced four decisions worth recording.

## Decision

**1. The page is `/model-player`, and a new top-level `player-registry.json`
decides what it shows.** `registry.json` stays the manifest of model *facts*
(architecture, tokenizer, params, artifact URLs). The player needs two things
that are neither model facts nor site presentation constants: a starter prompt
the corpus actually contains, and the release's `block_size` (the sampling
window; the ONNX graph's RoPE cache physically cannot run past it). Those live
in `player-registry.json`, keyed by model id. The file is also **authoritative
for the list**: the page shows exactly the ids in it, in file order — one entry
per series, swapped at release time (a step added to `docs/releasing.md`).
Getting `block_size` wrong is not cosmetic: the demo crashes mid-generation
with an ONNX reshape error the moment the context outgrows the RoPE cache.

**2. Tokenizer files are derived from the ONNX URL, not separate registry
fields.** `core/export/export.py` writes `<name>.vocab.json` next to
`<name>.onnx` for char models; the corpus-BPE releases commit an HF
`tokenizer.json` in their frozen folder, published as
`<name>.tokenizer.json` next to the ONNX. The site derives both URLs by
swapping the `.onnx` suffix. One URL field per model in `registry.json`;
the *naming convention* is the contract, enforced at publish time.

**3. The player grew a `ByteLevelBPETokenizer`** that loads an HF
`tokenizer.json` (BPE model + ByteLevel pre-tokenizer) and implements the GPT-2
algorithm in plain JS — split regex, byte-to-unicode alphabet, ranked merges.
Verified byte-exact (encode ids and decoded text) against the Python
`tokenizers` reference on multi-line, odd-whitespace, and unicode samples.
This unlocks every corpus-trained BPE release, present and future, with no
per-model code.

**4. Bundling onnxruntime-web under Next.js needs two webpack overrides**, set
in `website/next.config.mjs`:

- `resolve.conditionNames = ["onnxruntime-web-use-extern-wasm", "..."]` picks
  ORT's extern-wasm build, which fetches its `.wasm` backend from the player's
  pinned CDN `wasmPaths` at runtime instead of inlining the emscripten loader
  (the inlined loader is emitted as a raw `static/media/*.mjs` asset that the
  minifier cannot parse — `'import.meta' cannot be used outside of module
  code`).
- a module rule turning off `url`/`worker` parsing for `onnxruntime-web/dist`,
  because ORT also spawns its proxy worker via `new Worker(new
  URL(import.meta.url))`, which makes webpack emit the module itself as another
  unparseable asset.

The ORT chunk stays behind a dynamic `import()` that only loads when the user
presses generate.

## Artifacts and hosting

Exports are reproducible on demand: stage the release's run checkpoint into its
frozen folder (`ckpt.pt` and `meta.pkl` are gitignored there), run
`core/export/export.py`, which parity-checks the graph against PyTorch. For
local development the six current artifacts are served from
`website/public/artifacts/` (gitignored — [ADR-0002](0002-no-weights-in-tree.md)
still holds). Production hosting is Cloudflare R2, per `registry.json`'s
standing note; the bucket needs a CORS policy allowing the site origin because
the browser fetches the ONNX cross-origin.

## Consequences

- The player has a real consumer; its README scope is now "any release in
  `player-registry.json`" rather than the shakespeare series.
- Releasing gains one small step (swap the series' player-registry entry), and
  forgetting it means the new release simply doesn't appear in the player —
  safe failure.
- WASM inference runs on the browser's main thread, so the tab janks during
  generation (seconds, at these model sizes). Worker-based inference is the
  known fix and is queued in `docs/TODO.md`.
- The derived-URL convention means artifact uploads must keep the
  `<name>.onnx` / `<name>.vocab.json` / `<name>.tokenizer.json` names side by
  side, or char/BPE models fail to load with a fetch error.
