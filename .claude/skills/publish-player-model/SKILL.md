---
name: publish-player-model
description: Export a released model to ONNX and publish it — R2 for the website's /model-player page, and a Hugging Face repo under the sup-computer org for the checkpoint + card. Use when a new model version is released, when the player needs to pick up a release, when artifact URLs in registry.json need filling, or when re-uploading fixed artifacts.
---

# Publish a model to the player (and Hugging Face)

Turn a released model version into browser-runnable artifacts on Cloudflare R2,
a Hugging Face release under [`sup-computer`](https://huggingface.co/sup-computer),
and wire it into the `/model-player` page. Conventions are recorded in
[ADR-0024](../../../docs/adr/0024-model-player-page-and-artifact-conventions.md);
the release process itself is [`docs/releasing.md`](../../../docs/releasing.md).

## Preconditions

- The release is frozen: `projects/<project>/models/<id>/` exists with its own
  `model.py`, `config.py`, `prepare.py`, and a `registry.json` entry.
- The trained checkpoint exists locally (in `projects/<project>/runs/<run>/` or
  reproducible by re-running the frozen folder's `train.py`). Weights are never
  in git — a fresh clone must retrain or copy the checkpoint in.
- `uv sync --extra export` has been run (installs `onnx` + `onnxruntime`).

## 1. Stage the checkpoint and tokenizer metadata

The exporter (`core/export/export.py`) requires `ckpt.pt` — and, for char
models, `meta.pkl` — **in the frozen folder root** (both gitignored there).

```bash
cp projects/<project>/runs/<run>/ckpt.pt projects/<project>/models/<id>/ckpt.pt
uv run python projects/<project>/models/<id>/prepare.py
```

- Identify the right run by matching `model_args` (vocab_size, n_layer,
  block_size) in the checkpoint against the registry entry — do not guess:
  `torch.load(p, map_location="cpu", weights_only=True)["model_args"]`.
- `prepare.py` usually writes `meta.pkl` into a data subdir
  (e.g. `kenosha/`, `regular/`); copy it up: `cp <frozen>/<subdir>/meta.pkl <frozen>/meta.pkl`.
- Corpus-BPE releases (e.g. shakespeare-nanogpt-3) have no `meta.pkl` char
  vocab; their tokenizer is the **committed** HF `tokenizer.json` in the frozen
  folder — never retrain it.

## 2. Export (parity-checked)

```bash
uv run python core/export/export.py projects/<project>/models/<id> projects/<project>/dist
```

Confirm the output says `parity ok` (ONNX vs PyTorch logits). Products in
`projects/<project>/dist/` (gitignored): `<id>.onnx`, `<id>.int8.onnx`,
`<id>.vocab.json` (char models only), `<id>.manifest.json`.

## 3. Upload to R2 — naming is a contract

Bucket `sup-computer-artifacts`, public at
`https://pub-3a641239948a4381a0343fce77d6ecb8.r2.dev` (CORS for the site origin
and localhost:3000 is already configured; wrangler is OAuth'd on this machine —
`npx wrangler whoami` to check).

Every upload sets a one-week `Cache-Control` (decided 2026-07-04): long
enough that reloads stop re-downloading 40MB graphs, short enough that a
fixed artifact re-uploaded at the same URL self-heals within a week —
deliberately not `immutable`, since overwrite-in-place stays on the table.

```bash
CC="public, max-age=604800"
npx wrangler r2 object put "sup-computer-artifacts/<id>.onnx" --file projects/<project>/dist/<id>.onnx --cache-control "$CC" --remote
# char models:
npx wrangler r2 object put "sup-computer-artifacts/<id>.vocab.json" --file projects/<project>/dist/<id>.vocab.json --cache-control "$CC" --remote
# corpus-BPE models (note the rename):
npx wrangler r2 object put "sup-computer-artifacts/<id>.tokenizer.json" --file projects/<project>/models/<id>/<data-dir>/tokenizer.json --cache-control "$CC" --remote
# always — the export manifest (frozen config incl. block_size):
npx wrangler r2 object put "sup-computer-artifacts/<id>.manifest.json" --file projects/<project>/dist/<id>.manifest.json --cache-control "$CC" --remote
```

Tokenizer URLs derive from the `.onnx` name by suffix swap —
`player/src/registry.js`'s `resolveBundle` owns that contract (ADR-0024,
ADR-0028) — so the `<id>.vocab.json` / `<id>.tokenizer.json` names next to
`<id>.onnx` are load-bearing. The manifest upload is part of the bundle too:
the `sup` CLI uses it as the cross-check fallback for `block_size`. Only
`char`, `bpe` (HF tokenizer.json), and `gpt2-bpe` tokenizer types are
supported by `@supcomputer/player` — a new tokenizer scheme needs a new class
in `player/src/tokenizers.js` plus its entry in `player/src/registry.js`'s
`SUPPORTED_TOKENIZERS` first.

## 4. Publish the Hugging Face release

One HF model repo per frozen release: `sup-computer/<id>` (a new research round
= a new repo, same as a new frozen folder). Auth: `uvx --from
'huggingface_hub[cli]' hf auth whoami` — log in via `hf auth login` if needed.

Stage a directory containing:

- `README.md` — staged by the checked-in script (never rewrite links by
  hand; glyph-nanogpt-1 shipped broken relative links that way):

  ```bash
  node tools/hf-stage/stage.mjs <id> <staged-dir>/README.md
  ```

  It takes the card from `research-docs/model-cards/<id>.md`, inserts the
  standard pointer line after the H1, rewrites every repo-relative link
  through `website/lib/content.js`'s own rules, and fails loudly if any
  relative link survives.
- `ckpt.pt` — the full training checkpoint (HF is the home for weights; git
  and R2 deliberately are not).
- `<id>.onnx`, `<id>.int8.onnx`, and the tokenizer file (same names as R2).

```bash
uvx --from 'huggingface_hub[cli]' hf repo create "sup-computer/<id>" --repo-type model
uvx --from 'huggingface_hub[cli]' hf upload "sup-computer/<id>" <staged-dir> . \
  --repo-type model --commit-message "release: <id> (checkpoint + ONNX + tokenizer + model card)"
```

## 5. Wire the registry

Everything lands in `registry.json` — the only registry (ADR-0028); the
`/model-player` roster and the `sup` CLI derive newest-runnable-per-lineage
from it, so the release appears in both the moment these fields fill:

- `artifacts.onnx` — the full public R2 URL; `artifacts.checkpoint` — the HF
  resolve URL (`https://huggingface.co/sup-computer/<id>/resolve/main/ckpt.pt`).
- `block_size` — from the frozen `config.py` (should already be in the entry
  from release step 4; cross-check against `<id>.manifest.json`). **Getting
  this wrong crashes the demo mid-generation** — the ONNX RoPE cache
  physically ends at block_size, and the JS window cap is the only guard
  (symptom: an OrtRun reshape error like `{N,16}` vs `{1,1,N+1,16}`).
- `demo.prompt` — a string the training corpus actually contains (check the
  corpus, don't invent one; leading whitespace is load-bearing).

For local dev without the network, also copy the artifacts into the gitignored
`website/public/artifacts/` and use `/artifacts/<file>` URLs temporarily.

## 6. Verify in the browser, then commit

```bash
cd website && node scripts/sync-content.mjs   # dev server picks registries up
```

Open `http://localhost:3000/model-player/`, select the model, generate, and let
it run **past the block_size boundary** (prompt + max tokens > block_size) to
prove the sliding window works. Expect main-thread jank while it generates —
known limitation, see `docs/TODO.md` item 1.

Commit the `registry.json` change (small, focused commit). Weights, `dist/`,
and `website/public/artifacts/` stay untracked.
