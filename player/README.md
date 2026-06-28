# nanogpt-player

A tiny browser runtime for small **nanoGPT-shaped** models. It runs the model's
forward pass with [onnxruntime-web](https://onnxruntime.ai/) (WebGPU, WASM
fallback) and keeps everything stateful — the autoregressive loop, sampling,
tokenization — in plain JS.

The ONNX graph is only the **logits oracle**: tokens in, last-position logits
out. No KV cache; for these context lengths re-running the full forward each step
is fine.

Scope today: the [`shakespeare-nanogpt`](../projects/shakespeare/) series (v1
char-level, v2 GPT-2 BPE). See
[ADR-0010](../docs/adr/0010-vendor-the-player.md) for the full design and the
decision to vendor this runtime in-tree.

## Install

This is the in-tree `@supcomputer/player` package. Nothing consumes it yet — the
website's future `/play` route will be the consumer (not yet wired). It depends
on `onnxruntime-web` and `gpt-tokenizer`.

## Use

```js
import { loadModel, generate, CharTokenizer } from '@supcomputer/player';

const session = await loadModel('/shakespeare-nanogpt-1.onnx');
const tok = await CharTokenizer.fromUrl('/shakespeare-nanogpt-1.vocab.json');

await generate(session, tok, 'ROMEO:', {
  maxNewTokens: 300,
  temp: 0.8,
  topk: 40,
  blockSize: 256,                 // the model's block_size
  onToken: (piece) => process.stdout.write(piece), // or append to the DOM
});
```

Lower-level pieces are exported too: `forward(session, ids)` → `Float32Array`
logits, and `sample(logits, { temp, topk })` → token id.

## API

| export | what |
| --- | --- |
| `loadModel(url, opts?)` | create an ORT session (WebGPU → WASM) |
| `forward(session, ids)` | one forward pass → last-position logits (`Float32Array`) |
| `sample(logits, opts?)` | temperature + top-k sample → token id |
| `generate(session, tok, prompt, opts?)` | the AR loop; streams via `onToken` |
| `CharTokenizer` | v1 char vocab (`.fromUrl(vocab.json)`) |
| `BPETokenizer` | v2 GPT-2 BPE (`.create()`) |
| `configureBackend(opts?)` | override `wasmPaths` / thread count |

## Serving ORT's WASM assets

By default the `.wasm` backend files load from a versioned jsDelivr CDN (pinned
to `ORT_VERSION`), so a fresh consumer folder needs no bundler config. To
self-host them, pass `wasmPaths` to `loadModel`/`configureBackend` and copy
`onnxruntime-web/dist/*.wasm` into your static dir.

**Cross-origin isolation:** multithreaded WASM needs COOP/COEP headers
(`Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Embedder-Policy:
require-corp`). Without them the runtime falls back to single-threaded WASM
(fine for these model sizes). WebGPU needs no special headers.

## Getting a model

Models are produced by [`core/export/export.py`](../core/export/export.py)
(PyTorch `.pt` → verified `.onnx` + `vocab.json`). You never ship the `.pt`. The
`.onnx` artifacts are **not** committed to the tree (per
[ADR-0002](../docs/adr/0002-no-weights-in-tree.md), the no-weights rule); they
are referenced by [`registry.json`](../registry.json).
