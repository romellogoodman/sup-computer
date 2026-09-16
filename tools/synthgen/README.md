# synthgen — the LLM synthetic-corpus pipeline

*The LLM synthetic-corpus engine — every LLM-generated corpus goes through it, local via LM Studio or hosted via OpenRouter (ADR-0014, ADR-0038).*

A small, dependency-free generator that drives LLMs — local models served by
LM Studio, or hosted models over OpenRouter — to produce synthetic text
corpora for training tiny GPTs. It dedups the output and writes a
project-ready `raw.txt`, a provenance `manifest.json`, and one line of
`costs.jsonl`.

**This is the single engine every synthetic corpus goes through** — the
generation analog of [`tools/dataviz`](../dataviz/) (the single source of every
chart). When a project needs an LLM-generated corpus, it drives `synthgen`; it
doesn't hand-roll its own client. (Procedural / non-LLM corpora — like
`kenosha-kid` — generate themselves and don't belong here; see the ADR.)

It's part of this monorepo: the training engine lives in [`core/`](../../core/),
and this subdirectory turns models into the `raw.txt` a project's
`prepare.py` tokenizes into `train.bin`/`val.bin`.

> The tool name is provisional. It's deliberately self-contained (one engine
> module + one CLI + this README), so a rename is a trivial `git mv`.

## The research idea — mixture of models

The lever is **mixture-of-models** generation: run several *different*
models so the corpus carries diverse "voices." Distilling a single teacher into
a tiny GPT is circular — the student can only inherit one model's habits.
Mixing models breaks that, the way a varied human corpus would. On LM Studio,
`synthgen` discovers every chat model loaded and, by default, generates across
all of them; on OpenRouter you name the mix. Either way it records which model
produced each document.

## Backends

Two backends, one engine. Both speak the OpenAI-compatible
`POST /chat/completions` over stdlib `urllib` — no `requests`, no `openai`
dependency, matching dataviz's zero-dependency ethos. `--backend` picks one;
the default is unchanged, so every existing call site behaves as it did.

| | LM Studio (`lmstudio`, default) | OpenRouter (`openrouter`) |
|---|---|---|
| Where | `http://localhost:1234/v1` (override `SYNTHGEN_BASE_URL`) | `https://openrouter.ai/api/v1` |
| Cost | free per token — the manifest records `0.0` | paid — `usage.cost` from every response, in US dollars |
| Models | discovered (`--list`), or `--models` | `--models` is required; there is no discovery |
| Auth | none | `OPENROUTER_API_KEY` |
| Reasoning lever | `"reasoning_effort": "none"` | `"reasoning": {"effort": "none"}` |

### The key

OpenRouter needs `OPENROUTER_API_KEY`. `synthgen` reads it from the process
environment first, then the repo-root `.env.local`, then the repo-root `.env`
— the first non-empty value wins. Both files are gitignored; `.env.example`
at the repo root shows the one line. The parser is stdlib (`KEY=value`,
quotes and `#` comments tolerated). A missing key fails before any request
is made. The key is never printed and never written to a manifest.

### Models are always named on OpenRouter

`--models vendor/model,vendor/model` is required. There is no default, no
`openrouter/auto`, no fallback list: the studio names the models it pays for,
every run, and the manifest records exactly those ids. `--list` is LM Studio
only and errors out on OpenRouter.

### Cost and budget

Cost is first-class. OpenRouter returns `usage.cost` on every response (its
credits are denominated in dollars, and the old `usage: {include: true}`
request flag is documented as a no-op); `synthgen` records it per sample as
`cost_usd`, sums it per model and per run as `total_cost_usd`, and appends one
line per run to `costs.jsonl` beside the manifest — the same fields gatsby's
Claude-API log uses where they apply. LM Studio runs write `0.0` so the
manifest shape is identical everywhere. A dropped duplicate still counts: cost
is summed over everything generated, not only what was kept.

`--budget <usd>` caps a run. Before each request the engine checks whether
the cumulative spend plus the mean cost so far would pass the ceiling and, if
it would, stops cleanly: the manifest is written with what was generated and
`budget_hit: true`. A run can overshoot by one sample's noise, never by a
sample it could have foreseen.

```bash
cd tools/synthgen

python3 build.py --backend openrouter \
    --models mistralai/mistral-nemo,meta-llama/llama-3.1-8b-instruct \
    --n 50 --budget 2.00 \
    --prompt-file prompt.txt \
    --out ../../projects/<name>/data
```

### The reasoning lever (read this)

Local models under LM Studio are reasoning / "thinking" models. Without
suppression they spend the entire token budget on a hidden reasoning trace
and return EMPTY `content`. The only lever that worked there is
**`"reasoning_effort": "none"`** in the request body — `enable_thinking: false`
and `/no_think` did *not* work. On OpenRouter the documented lever is the
`reasoning` object: `{"reasoning": {"effort": "none"}}` disables reasoning
entirely (`exclude: true` would only hide a trace that is still billed —
[reasoning tokens](https://openrouter.ai/docs/use-cases/reasoning-tokens)).
`"none"` is the default on both; `--reasoning-effort` overrides it on both,
and every sample's `reasoning_control` records which field and value were
sent. If you see empty samples in the CLI's warning, this is almost always
the cause.

A cold local model's first call is slow (JIT load, ~10–25s); the HTTP timeout
is generous (600s) and transient errors are retried. HTTP 4xx — a bad key, an
unknown model, an empty balance — is not retried.

## Layout

```
synthgen.py     # the engine: backends / discover / generate / dedup / manifest + corpus + cost writers
build.py        # the CLI: discover or name -> generate across the mix -> dedup -> write
output/         # generated raw.txt + manifest.json + costs.jsonl (gitignored)
```

## Usage — CLI

```bash
cd tools/synthgen

python3 build.py --list                       # what chat models are loaded? (LM Studio)

# demo: 4 samples per loaded model, dedup, write to ./output/
python3 build.py --n 4 --prompt "Write a 3-sentence bedtime story."

# mixture-of-models straight into a project's data dir (drop-in for prepare.py)
python3 build.py --n 50 \
    --models qwen/qwen3.6-27b,granite-4.1-8b,olmo-3-7b-instruct \
    --prompt-file prompt.txt \
    --out ../../projects/gatsby/data

# the same run on the paid backend, capped at two dollars
python3 build.py --backend openrouter --budget 2.00 --n 50 \
    --models mistralai/mistral-nemo,meta-llama/llama-3.1-8b-instruct \
    --prompt-file prompt.txt \
    --out ../../projects/gatsby/data
```

`--out` is the target directory; point it at a project's `data/` and the run
writes `raw.txt` + `manifest.json` there and appends to `costs.jsonl`. Default
is `./output` (gitignored).

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

The OpenRouter path is the same calls with a backend object and a budget:

```python
be = sg.get_backend("openrouter")            # resolves the key, or raises
budget = sg.Budget(limit_usd=2.00)
samples = sg.generate("mistralai/mistral-nemo", "Write a tiny story.", n=10,
                      backend=be, budget=budget)   # stops early if budget.hit
manifest = sg.build_manifest(samples, kept, dropped, prompt=..., params=...,
                             backend=be, budget=budget, corpus_path=...)
sg.append_cost_record(sg.cost_record(manifest, "output/raw.txt"),
                      "output/costs.jsonl")
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

A project's `prepare.py` reads `data/raw.txt` as one character stream,
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
3. drops **near** duplicates (token-set Jaccard ≥ threshold, default 0.85)
   against an already-kept sample; first occurrence wins.

It is **never silent**: every removal is returned as a `Drop` record (reason,
the kept sample it matched, similarity, a preview) and the CLI logs each one.

## The manifest — the reproducibility record

`manifest.json` is the crown jewel. It records:

- a **run header**: timestamp (injectable for tests), backend (name, base
  URL, `served_by`), the prompt, params (temperature, max_tokens,
  `reasoning_effort`, jaccard threshold), the model mix, counts (generated /
  kept / dropped / corpus_chars, plus per-model generated / kept / cost),
  total token usage, `total_cost_usd`, and the budget (`budget_usd`,
  `budget_hit`);
- **`generators`**: one entry per model in the mix, in the shape
  [ADR-0037](../../docs/adr/0037-crediting-the-corpus-generators.md)'s
  roster uses — `{id, model_id, backend, served_by}`, the `id` a slug
  (vendor prefix stripped, dots to hyphens: `google/gemma-4-26b-a4b-qat` →
  `gemma-4-26b-a4b-qat`) and `model_id` the exact upstream id — so a corpus
  built here drops into `registry.json` without hand-copying;
- **per-sample provenance**: source model and backend, prompt, temperature,
  prompt/completion token counts, `cost_usd`, the `reasoning_control` field
  and value that were sent, a `sha1` of the text, and the `offset`/`length`
  of each document into `raw.txt` so every corpus document is locatable;
- the full **dedup ledger** (what was dropped and why).

Generation is non-deterministic (temperature), so the manifest — not a re-run —
is the record of which voice produced which document, and what it cost.

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
- **Wall-clock accounting.** Dollar cost is recorded now
  ([ADR-0038](../../docs/adr/0038-synthgen-openrouter-backend.md)); a local
  run's cost is still only token counts and latency. If GPU-hours become
  interesting, they belong in the manifest.
- **Stdlib-only.** Kept deliberately dependency-free. A retry/transport library
  or a faster near-dup index (MinHash/SimHash) would be the first things to
  reach for if scale demands — noted, not added.
