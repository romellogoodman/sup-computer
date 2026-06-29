---
type: note
series: player
status: published
date: 2026-06-28
researcher: claude-opus-4-8
title: "The logits oracle: running small models in the browser"
summary: "Don't serve a model — export only its forward pass as a static ONNX graph (tokens in, last-position logits out) and keep the autoregressive loop, sampling, and tokenization in JS, so a small model becomes a static asset that runs client-side with no server."
---
[← all reports](README.md) · **Note 01** · series: player · June 2026

# The logits oracle: running small models in the browser

A design note, not an experiment. The [experiment reports](README.md) are about
making small models *better* or *stranger*; this one is about *shipping* them —
how a 10-million-parameter model trained on a laptop becomes something a stranger
can run from a static file with no server behind it. It is the engineering that
makes the studio's "small and legible" thesis concrete, written down next to the
experiments because it is part of the same argument.

<div class="takeaways">
<p class="takeaways-label">Key takeaways</p>
<ul>
<li><strong>Don't serve a small model.</strong> Export only its <strong>forward pass</strong> as a static ONNX graph — tokens in, last-position logits out — a "logits oracle" with no memory.</li>
<li>The forward pass is a <strong>pure function</strong>; the autoregressive loop, sampling, and tokenization stay in plain JS. The model stops being a process you run and becomes a <strong>static asset you fetch</strong>.</li>
<li><strong>No KV cache</strong> — at 256–512-token context that's the right call, not a compromise: it keeps the graph stateless and cacheable.</li>
<li>The exporter enforces the contract or refuses to ship — last-position logits, <code>int64</code> tokens, and a PyTorch↔ONNX <strong>parity check</strong>. This is what makes "small and legible" shippable.</li>
</ul>
</div>

## 1. Don't serve a model

The instinct, when you have a trained model, is to *serve* it: stand up a process
that holds the weights in memory, accepts a prompt, runs the generation loop
inside itself, and streams text back. That process is now a server you own, a cost
you pay per token, and a thing that can go down. For a studio whose whole point is
that the models are small, that is a strange amount of infrastructure to wrap
around a 40-megabyte file.

So we don't serve the model. We export exactly **one thing** — the model's
**forward pass** — as a static [ONNX](https://onnx.ai/) graph: tokens in,
last-position logits out. Everything else that a "served" model does — the
autoregressive loop, temperature and top-k sampling, tokenization, rendering the
text as it arrives — stays in plain JavaScript on the client. The ONNX graph is
not a model in the conversational sense. It is a **logits oracle**: you hand it a
sequence of tokens, it tells you the scores for the next one, and it has no memory
that you ever asked.

## 2. Why this works: the forward pass is a pure function

A language model generating text looks stateful — it writes one token, then the
next, then the next, each conditioned on what came before. But the *model's* job
at each step is not stateful at all. Its only task is: **given this sequence of
tokens, what are the logits for the next position?** That is a pure function. Same
tokens in, same logits out, every time, with nothing remembered between calls.

The statefulness — the part that feels like "generation" — lives entirely in the
loop *around* that function:

1. encode the prompt to token ids;
2. run the forward pass on the last `block_size` tokens → logits;
3. sample one token from those logits (temperature, top-k);
4. append it, decode the new piece, render it;
5. go to 2.

Only step 2 is the model. Steps 1, 3, 4, 5 are ordinary code. Once you see the
forward pass as a pure function, exporting *just that function* as a static graph
is the obvious move — and it changes what the model **is**. It stops being a
process you run and becomes a **static asset you fetch**, like an image or a font.
It runs client-side through [`onnxruntime-web`](https://onnxruntime.ai/) — WebGPU
when the browser has it, WASM as the floor — so there is no server, no inference
cost, and nothing to keep alive. You host a file.

There is no KV cache, and at this scale that is the right call, not a compromise.
A KV cache trades memory and a stateful export for not re-reading the prompt each
step; it earns its keep at thousands of tokens of context. Our context windows are
256 to 512 tokens, and samples are short. Re-running the full forward pass every
step is cheap, and it keeps the exported graph **stateless** — which is the whole
reason it gets to be a pure, cacheable static file. The simplest thing and the
correct thing are the same thing here.

## 3. The seam: one contract, enforced on export

A pure function is only useful if both sides agree on its exact signature. The
seam between the Python that trains and the JavaScript that runs is narrow and
deliberately so, and the export script is where the contract is enforced rather
than hoped for. [`core/export/export.py`](../../core/export/export.py) does three
things that matter:

- **It exports the last-position logits, not the whole sequence.** A small
  `Wrapper` module takes nanoGPT's `forward(idx)` and returns `logits[:, -1, :]` —
  shape `[batch, vocab]`, exactly what a sampler wants, nothing to slice on the
  JS side.
- **It fixes the token dtype.** Tokens are exported as `int64` (`torch.long`), so
  the runtime feeds a `BigInt64Array` —
  [`forward()`](../../player/src/runtime.js) builds one explicitly. A dtype
  mismatch here is a silent wrong-answer bug, so the contract names it.
- **It checks parity or refuses to ship.** After export, the script runs the ONNX
  graph and the original PyTorch model on the same dummy input and asserts
  `max|onnx − torch| < 1e-4`. If the graph doesn't match the model, the export
  *fails* instead of emitting a plausible-looking but wrong file. (The real bug
  this caught: the legacy exporter silently dropped the causal mask from flash
  attention, so the graph attended non-causally and the logits were wrong by
  ~1.29 — the parity check turned a subtle correctness bug into a loud failure.)

On the consuming side, [`@supcomputer/player`](../../player/README.md) is the
mirror of that contract: `loadModel` opens the session, `forward` runs the oracle,
`sample` draws a token, `generate` is the thin loop over all three. The one place
per-model code is unavoidable is **tokenization**, because that is the one thing
the logits oracle doesn't carry: the v1 char model ships a `vocab.json` (a 65-char
`stoi`/`itos` map dumped from `meta.pkl`) and a ~10-line `CharTokenizer`; the v2
model uses GPT-2 BPE through an off-the-shelf library. Both satisfy the same
`{ encode, decode }` shape, so the loop above never changes.

Keeping the exporter and the runtime in **one tree** is the point of
[ADR-0010](../../docs/adr/0010-vendor-the-player.md). When the contract changes —
a new tokenizer type, a different output shape — both sides move in the same
commit. The contract stays honest because there is no version skew between the
thing that writes the file and the thing that reads it.

## 4. Why it fits the studio thesis

The studio's bet is that small models are worth building because they are
*legible* — small enough to read end to end, train in minutes, and understand
completely. The logits oracle is what makes that bet **shippable**. A model you
can train on a laptop should also be a model a reader can run on their own laptop
without trusting (or paying for) a server in the middle. Exporting the forward
pass as a static asset closes that loop: the artifact a reader receives is the
same small, inspectable thing the experiments describe — `tokens in, logits out`,
a file you can open, host on a CDN, and run from a static page. "Small and
legible" stops being a description of the training run and becomes a property of
the deployed thing.

## 5. Honest tradeoffs

This design is a good fit, not a free lunch. Three things to keep straight:

- **No KV cache.** Right at this scale, a real cost at a larger one. The moment
  context windows grow into the thousands, re-running the full forward each step
  stops being cheap and the stateless-export simplicity has to be paid back. This
  is a small-model technique, sold honestly as one.
- **Multithreaded WASM needs COOP/COEP.** The fast path is WebGPU, which needs no
  special headers. The WASM fallback can use multiple threads, but only via
  `SharedArrayBuffer`, which requires the page to be cross-origin isolated
  (`Cross-Origin-Opener-Policy: same-origin` +
  `Cross-Origin-Embedder-Policy: require-corp`). Without those headers the runtime
  quietly drops to single-threaded WASM — fine for these model sizes, but a
  real-deployment detail you have to know about.
- **int8 vs WebGPU.** Dynamic int8 quantization shrinks the download ~4× (it
  matters most for the ~30M-param v2 BPE model), but it emits `MatMulInteger` /
  `DynamicQuantizeLinear` ops the WebGPU execution provider may not fully cover —
  so it can fall back to WASM for those nodes or error. The export produces both
  files; the fp32 graph is the safe default for a WebGPU demo and int8 is the
  download-size lever. You pick per consumer.

---

The runtime lives in [`player/`](../../player/README.md); the exporter that feeds
it is [`core/export/export.py`](../../core/export/export.py); the decision to keep
them in one tree is [ADR-0010](../../docs/adr/0010-vendor-the-player.md). The
`.onnx` artifacts themselves are not committed
([ADR-0002](../../docs/adr/0002-no-weights-in-tree.md), the no-weights rule); they
are referenced by [`registry.json`](../../registry.json) and rebuilt from the
export script. Nothing consumes the player yet — the website's future `/play`
route is the intended first consumer — but the contract is in place and the seam
is honest.

---

**Researcher:** Claude Opus 4.8 (Claude Code) — wrote this design note under human direction (Romello set the goals and kept oversight). It documents the `player` runtime and the `core/export` exporter in this repo; no model is produced here.
