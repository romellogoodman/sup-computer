# sup

**An ollama for the studio's tiny GPTs.** `sup` downloads a released model's
public artifacts (the ONNX graph + tokenizer sidecar `registry.json` points at)
and runs it in your terminal — forward pass on
[onnxruntime-node](https://onnxruntime.ai/), sampling loop and tokenizers from
[`@supcomputer/player`](../player/) with the ORT backend injected
([ADR-0025](../docs/adr/0025-sup-cli-and-injectable-player-backend.md)).

The invocation is a greeting. Say hi to a model and it answers its starter
prompt in its own voice:

```bash
sup shakespeare                      # series greeting -> newest runnable release
sup kenosha-kid-nanogpt-2            # greet a specific release
sup daydream "e2e4 "                 # your prompt instead of the starter
```

## Setup

Not published to npm — this runs from the clone (ADR-0025):

```bash
cd cli && npm install
node bin/sup.js list        # or: npm exec sup -- list
```

Optionally `npm link` to put `sup` on your PATH.

## Commands

```
sup <model|series> [prompt]   greet a model
sup run <model> [prompt]      the explicit form
sup list                      what's runnable (and what isn't yet)
sup pull <model> | --all      download artifacts without running; --all doubles
                              as an integrity check of every published bundle
sup rm <model> | --all        clear the cache
```

Flags for run/greeting: `--temp` (0.8), `--topk` (40), `--tokens` (200), and
`--seed` for a reproducible generation.

Artifacts download once into `~/.cache/supcomputer/<model-id>/` (respects
`XDG_CACHE_HOME`). Generated text goes to stdout, status to stderr, so
`sup shakespeare > sonnet.txt` captures only the text. Ctrl-C stops generation
cleanly.

## Where things come from

- **What exists:** `registry.json` at the repo root — model facts and artifact
  URLs (R2). Tokenizer sidecars are derived from the ONNX URL by suffix swap
  (`.vocab.json` for char models, `.tokenizer.json` for corpus BPE) — the
  ADR-0024 naming convention; this CLI is its second consumer.
- **How to greet it:** `player-registry.json` — starter prompt and
  `block_size` per release, shared with the website's `/model-player` page.

A note on daydream: the chess models stream *dreamed* moves — nothing here
checks legality, same as the browser player. That's the point.
