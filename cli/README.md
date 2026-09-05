# sup

**An ollama for the studio's tiny GPTs.** `sup` downloads a released model's
public artifacts — the ONNX graph + tokenizer sidecar `registry.json` points at
— and runs it in your terminal. The forward pass runs on
[onnxruntime-node](https://onnxruntime.ai/); the sampling loop and tokenizers
come from [`@supcomputer/player`](../player/) with the ORT backend injected
([ADR-0025](../docs/adr/0025-sup-cli-and-injectable-player-backend.md)).

The invocation is a greeting. Say hi to a model and it answers its starter
prompt in its own voice:

```bash
sup shakespeare                      # series greeting -> newest runnable release
sup kenosha-kid-nanogpt-2            # greet a specific release
sup daydream "e2e4 "                 # your prompt instead of the starter
```

## Install

Not published to npm — clone the repo and link the package (ADR-0025):

```bash
git clone https://github.com/romellogoodman/sup-computer.git
cd sup-computer/cli
npm install
npm link          # puts `sup` on your PATH

sup list
sup shakespeare
```

Prefer not to link? `node bin/sup.js …` or `npm exec sup -- …` from `cli/`
work the same.

## Commands

```
sup <model|series> [prompt]   greet a model
sup run <model> [prompt]      the explicit form
sup list [--all]              the greetable roster; --all lists every release by id
sup pull <model> | --all      download artifacts without running; --all doubles
                              as an integrity check of every published bundle
sup rm <model> | --all        clear the cache
sup train <corpus.txt> [...]  train a small GPT on your own text file (needs uv)
```

Flags for run/greeting: `--temp` (0.8), `--topk` (40), `--tokens` (200), and
`--seed` for a reproducible generation.

Artifacts download once into `~/.cache/supcomputer/<model-id>/` (respects
`XDG_CACHE_HOME`). Generated text goes to stdout, status to stderr, so
`sup shakespeare > sonnet.txt` captures only the text. Ctrl-C stops generation
cleanly.

## Train on your own corpus

`sup train` is the one command from a text file to a model: prepare, train,
sample, ONNX export, and a model-card stub, into one run dir.

```bash
sup train ./corpus.txt                           # -> ./runs/corpus/
sup train ./corpus.txt --size tiny --iters 200   # a smoke run: under a minute on a laptop
sup train ./corpus.txt --tokenizer bpe --name my-model --out ./my-run
```

The training itself is Python. The command spawns core's `sup-train` entry
point in the repo's `uv` venv (`uv sync --extra export` once, from the repo
root) and streams its log; flags pass straight through, so `sup train --help`
is the full list. What lands in the run dir — and why a run is not a release —
is in [`docs/handbook.md`](../docs/handbook.md#train-on-your-own-corpus).

## Where things come from

- **What exists:** `registry.json` at the repo root — model facts and artifact
  URLs (R2). Tokenizer sidecars are derived from the ONNX URL by suffix swap
  (`.vocab.json` for char models, `.tokenizer.json` for corpus BPE). That is
  the ADR-0024 naming convention; this CLI is its second consumer.
- **How to greet it:** `player-registry.json` — starter prompt and
  `block_size` per release, shared with the website's `/interfaces` page.
  Historical releases aren't listed there; their `block_size` comes from the
  `<id>.manifest.json` uploaded beside the ONNX (they have no starter prompt,
  so pass one: `sup run shakespeare-nanogpt-1 "ROMEO:"`).

A note on daydream: the chess models stream *dreamed* moves — nothing here
checks legality, same as the browser player. That's the point.
