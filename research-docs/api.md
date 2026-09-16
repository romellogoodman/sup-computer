---
title: The inference API
summary: >-
  Run any released model over HTTP at supcpu.com/api — the roster, a
  streaming generate call, and a health check. Public, read-only, no key.
---

# The inference API

Every released model answers over HTTP. Three routes under
`https://www.supcpu.com/api/`, JSON in and out, CORS open, no key: the same
models the instruments run in your browser and `sup` runs in your terminal,
served from one small CPU function. Ask a series by name and the newest
runnable release replies.

## The roster

```bash
curl https://www.supcpu.com/api/models
```

Returns `models` — one entry per runnable lineage with its `id`, greeting
`alias`, `series`, `version`, `tagline`, `params`, `tokenizer`,
`block_size`, and the demo `prompt` — plus `series` and `aliases`, the
names `generate` accepts. It is `sup list` over HTTP.

## Generate

```bash
curl -N https://www.supcpu.com/api/generate \
  -H 'content-type: application/json' \
  -d '{"model": "shakespeare", "tokens": 120}'
```

`model` is a release id (`kenosha-kid-nanogpt-2`), a series
(`shakespeare-nanogpt`), a prefix of one (`shakespeare`), or a greeting alias
(`daydream-micro`). Where a series has several releases the newest runnable
one answers, and where sibling tiers share a version the bare series line
wins — the same rules as the terminal greeting. `prompt` defaults to the
release's demo prompt; leading whitespace in those prompts is load-bearing,
so pass your own exactly as you want the model to see it.

| field | default | range |
|---|---|---|
| `prompt` | the release's demo prompt | up to 4,000 characters |
| `temp` | 0.8 | 0.05 – 2.5 |
| `topk` | 40 | 0 – 1000 (0 turns top-k off) |
| `tokens` | 200 | 1 – 512 |
| `seed` | — | any integer; same seed, same text |
| `stream` | `true` | `false` for one JSON body |

Streaming is server-sent events, `text/event-stream`. One event per decoded
piece, then a summary:

```text
data: {"token":"\n"}
data: {"token":"So"}
data: {"token":" shall"}
…
data: {"done":true,"model":"shakespeare-nanogpt-3","prompt":"  ROMEO:","text":"\n\nSo shall the sky.…","tokens":120,"temp":0.8,"topk":40}
```

With `"stream": false` the summary is the whole reply:

```json
{"model":"kenosha-kid-nanogpt-2","prompt":"You never did the Kenosha Kid","text":".\nNever did Kenosha Kid you the\nYou? Nev","tokens":40,"temp":0.8,"topk":40,"seed":1}
```

`text` is the continuation only; `prompt` is returned beside it so the two
concatenate to what the model saw and said. `tokens` counts new tokens
sampled.

Errors are JSON with an `error` line: 400 for a body that isn't an object,
a non-number where a number is due, or a name that matches several series;
404 for a name that matches nothing, with `valid` listing every name that
does; 405 for anything but POST.

## Health

```bash
curl https://www.supcpu.com/api/health
```

`{"ok": true, "loaded": [...]}` — the model ids this instance holds in
memory. The function scales to zero between visits, so the list is a
snapshot, not a promise.

## What to expect

A cold instance downloads the release's int8 ONNX graph and tokenizer from
the studio's artifact bucket before the first token, then keeps them in
memory. A warm instance answers the small models in tens of milliseconds
per token; glyph, the largest at 48M parameters, takes about 65 ms per
token on a laptop core and longer on the function's. One CPU generates
serially, so simultaneous requests for one model wait their turn.

The text is the model's own. These are corpus models with no filter in
front of them; what they say is what they learned.

## Where it comes from

The function is the same three pieces as the terminal runner: the `sup`
CLI's name resolution and artifact cache, the player's sampling loop, and
onnxruntime-node injected as the backend. Nothing model-specific lives in
it — a new release appears in the roster the moment its artifact URLs fill
in. The decision record is
[ADR-0036](../docs/adr/0036-hosted-inference-api.md); the code is
[`website/api/`](../website/api/) and
[`website/lib/inference.js`](../website/lib/inference.js).
