# synthgen — local-LLM synthetic-corpus pipeline

A small, dependency-free generator that drives **local LLMs served by LM Studio**
to produce synthetic text corpora for training tiny GPTs. It dedups the output
and writes a project-ready `raw.txt` plus a provenance `manifest.json`.

**This is the single engine every synthetic corpus goes through** — the
generation analog of [`tools/dataviz`](../dataviz/) (the single source of every
chart). When a project needs an LLM-generated corpus, it drives `synthgen`; it
doesn't hand-roll its own LM Studio client. (Procedural / non-LLM corpora — like
`kenosha-kid` — generate themselves and don't belong here; see the ADR.)

It's part of this monorepo: the training engine lives in [`core/`](../../core/),
and this subdirectory turns local models into the `raw.txt` a project's
`prepare.py` tokenizes into `train.bin`/`val.bin`.

> The tool name is provisional. It's deliberately self-contained (one engine
> module + one CLI + this README), so a rename is a trivial `git mv`.

## The research idea — mixture of models

The lever is **mixture-of-models** generation: run several *different* local
models so the corpus carries diverse "voices." Distilling a single teacher into
a tiny GPT is circular — the student can only inherit one model's habits.
Mixing models breaks that, the way a varied human corpus would. `synthgen`
discovers every chat model loaded in LM Studio and, by default, generates across
all of them, recording which model produced each document.

## Backend — LM Studio (OpenAI-compatible)

LM Studio runs an OpenAI-compatible server at `http://localhost:1234/v1`
(override with `SYNTHGEN_BASE_URL`). `synthgen` talks to it with stdlib
`urllib` — no `requests`, no `openai` dependency, matching dataviz's
zero-dependency ethos.

- **Discovery** (`GET /v1/models`) filters out embedding models (id contains
  `embed`).
- **Generation** is `POST /v1/chat/completions`.

### The reasoning_effort gotcha (read this)

The local models are reasoning / "thinking" models. **Without suppression they
spend the entire token budget on a hidden reasoning trace and return EMPTY
`content`.** The only lever that worked is passing **`"reasoning_effort":
"none"`** in the request body — `enable_thinking: false` and `/no_think` did
**not** work. It is the default here (`synthgen.REASONING_EFFORT`) and is
overridable per call / via `--reasoning-effort`. If you see empty samples in the
CLI's warning, this is almost always the cause.

A cold model's first call is slow (JIT load, ~10–25s); the HTTP timeout is
generous (600s) and transient errors are retried.

## Layout

```
synthgen.py     # the engine: discover / generate / dedup / manifest + corpus writers
build.py        # the CLI: discover -> generate across the mix -> dedup -> write
output/         # generated raw.txt + manifest.json (gitignored)
```

## Usage — CLI

```bash
cd tools/synthgen

python3 build.py --list                       # what chat models are loaded?

# demo: 4 samples per loaded model, dedup, write to ./output/
python3 build.py --n 4 --prompt "Write a 3-sentence bedtime story."

# mixture-of-models straight into a project's data dir (drop-in for prepare.py)
python3 build.py --n 50 \
    --models qwen/qwen3.6-27b,granite-4.1-8b,olmo-3-7b-instruct \
    --prompt-file prompt.txt \
    --out ../../projects/gatsby/data
```

`--out` is the target directory; point it at a project's `data/` and the run
writes `raw.txt` + `manifest.json` there. Default is `./output` (gitignored).

## Usage — as a library

```python
import synthgen as sg

models = sg.discover()                       # ["qwen/qwen3.6-27b", ...]
samples = []
for m in models:
    samples += sg.generate(m, "Write a tiny story.", n=10, temperature=0.9)

kept, dropped = sg.dedup(samples, jaccard_threshold=0.85)
for d in dropped:
    print("dropped", d.reason, d.preview)     # never silent

sg.write_corpus(kept, "output/raw.txt")
manifest = sg.build_manifest(samples, kept, dropped,
                             prompt="Write a tiny story.",
                             params={"jaccard_threshold": 0.85},
                             corpus_path="output/raw.txt")  # verifies the offsets
sg.write_manifest(manifest, "output/manifest.json")
```

A **project control line** (e.g. gatsby's `[green=N] topic: ...` prime) is added
without baking project logic into the engine — pass `prefix_fn` to
`write_corpus` / `build_manifest`. The manifest's per-doc offsets are recomputed
from `separator`/`prefix_fn`, so **pass the same two arguments to both calls** —
`corpus_path` makes a mismatch a loud error instead of silently wrong provenance:

```python
sg.write_corpus(kept, "data/raw.txt",
                prefix_fn=lambda s: f"[model={s.model}]\n")
manifest = sg.build_manifest(samples, kept, dropped, prompt=..., params=...,
                             prefix_fn=lambda s: f"[model={s.model}]\n",
                             corpus_path="data/raw.txt")
```

## How it maps to `prepare.py`

A project's `prepare.py` reads `data/raw.txt` as **one character stream**,
derives the char vocab from its unique characters, and splits 90/10 into
`train.bin`/`val.bin` + `meta.pkl`. `synthgen` writes `raw.txt` as the
documents concatenated, each terminated by a blank line (`\n\n`) — the same
shape the sibling projects use. So the output is a **drop-in**:

```
synthgen build.py  ->  data/raw.txt  ->  prepare.py  ->  train.bin/val.bin/meta.pkl
```

Derived artifacts (`*.bin`, `*.pkl`) are gitignored repo-wide and rebuild from
`raw.txt`. Whether the *corpus itself* is committed is the project's call (gatsby
commits its corpus + cost log as the research record).

## Dedup

Real near-duplicates show up across and within models. `dedup`:

1. drops **empty** samples (usually a reasoning-suppression miss),
2. drops **exact** duplicates (normalized text — casefold + collapsed
   whitespace),
3. drops **near** duplicates (token-set **Jaccard** ≥ threshold, default 0.85)
   against an already-kept sample; first occurrence wins.

It is **never silent**: every removal is returned as a `Drop` record (reason,
the kept sample it matched, similarity, a preview) and the CLI logs each one.

## The manifest — the reproducibility record

`manifest.json` is the crown jewel. It records:

- a **run header**: timestamp (injectable for tests), backend + base URL, the
  prompt, params (temperature, max_tokens, `reasoning_effort`, jaccard
  threshold), the model mix, and counts (generated / kept / dropped /
  corpus_chars, plus per-model generated/kept) and total token usage;
- **per-sample provenance**: source model, prompt, temperature, prompt/
  completion token counts, a `sha1` of the text, and the `offset`/`length` of
  each document **into `raw.txt`** so every corpus document is locatable;
- the full **dedup ledger** (what was dropped and why).

Generation is non-deterministic (temperature), so the manifest — not a re-run —
is the record of which voice produced which document.

## Optional — downloading models (`lms get`)

`synthgen.download(url)` wraps LM Studio's `lms get` CLI. Two lessons are baked
in:

- **Pass full HuggingFace URLs.** A bare repo id (`Qwen/Qwen3-8B`) is treated as
  a fuzzy search term and lowercased → fail. Use
  `https://huggingface.co/Qwen/Qwen3-8B`.
- **Verify the repo exists first.** `hf_repo_exists(repo)` checks that
  `https://huggingface.co/api/models/<id>` returns 200; `download(..., check=True)`
  does this before starting.
- **The download is daemon-owned.** It keeps running even if the `lms` CLI / this
  process is killed; cancelling needs an explicit action in the app (or deleting
  the partial model folder).

## Open questions / deferred

- **Promotion to `core/curation/`.** This lives in `tools/`, not `core/`, on
  purpose — one consumer isn't enough signal to design the shared abstraction.
  See [ADR-0014](../../docs/adr/0014-synthgen-local-llm-pipeline.md) and
  [ADR-0011](../../docs/adr/0011-vendor-gatsby.md).
- **Cost accounting.** Local generation has no dollar cost, so there's no
  `costs.jsonl` analog; the manifest records token counts and latency instead.
  If wall-clock/GPU accounting becomes interesting, it belongs in the manifest.
- **Stdlib-only.** Kept deliberately dependency-free. A retry/transport library
  or a faster near-dup index (MinHash/SimHash) would be the first things to
  reach for if scale demands — noted, not added.
