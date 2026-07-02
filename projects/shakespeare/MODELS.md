# Model versions

This is a **living, versioned series of models**, refined over time through
LLM-assisted research — Claude Opus 4.8 acting as the researcher.
Each version is a checkpoint in that ongoing process, not a finished product.
This is **LLM-assisted research**: Claude implements, tests, and evaluates changes
under human direction. It is deliberately **not** recursive self-improvement, which
[Anthropic defines](https://www.anthropic.com/institute/recursive-self-improvement)
as an AI autonomously designing its own successor — we are not there yet.
`shakespeare-nanogpt-1` is the original baseline; `shakespeare-nanogpt-2` came
out of the first LLM-assisted research experiment (four rounds). New versions (v3, v4, …) will be
added as future rounds find real improvements, each pinned to its own git tag and
documented here. The story of how v1 became v2 is in
[Experiment 01](../../research-docs/reports/improve-a-small-model.md) (all reports: [`research-docs/reports/`](../../research-docs/reports/README.md))
and [`leaderboard.md`](./leaderboard.md).

Each version has a Hugging Face-style **model card** in
[`research-docs/model-cards/`](../../research-docs/model-cards/): [v1](../../research-docs/model-cards/shakespeare-nanogpt-1.md) ·
[v2](../../research-docs/model-cards/shakespeare-nanogpt-2.md) — model details, intended use, data,
evaluation (with charts from [`dataviz/`](../../tools/dataviz/README.md)), and limitations.

Each version is pinned to a **git tag** (so the exact repo state is reproducible)
and maps to a checkpoint **path** (weights are not committed — rebuild with the
commands below).

| | `shakespeare-nanogpt-1` (v1) | `shakespeare-nanogpt-2` (v2) |
|---|---|---|
| **Git tag** | `shakespeare-nanogpt-1` | `shakespeare-nanogpt-2` |
| **Self-contained code** | [`models/shakespeare-nanogpt-1/`](models/shakespeare-nanogpt-1/) | [`models/shakespeare-nanogpt-2/`](models/shakespeare-nanogpt-2/) |
| **Checkpoint** | `models/shakespeare-nanogpt-1/ckpt.pt` | `models/shakespeare-nanogpt-2/ckpt.pt` |
| **Origin** | the original baseline | LLM-assisted research experiment, Round 3 (the winner) |
| **Architecture** | original nanoGPT (LayerNorm, learned position embeddings, biases) | modern (RoPE, RMSNorm, bias-free) |
| **Tokenizer** | character-level (65-char vocab) | GPT-2 BPE (~50k vocab) |
| **Training data** | Tiny Shakespeare (~1.1 MB) | Complete Works (~5 MB) |
| **Parameters** | ~10.7 M | ~29.9 M |
| **Held-out test BPC** | n/a* | **1.919** |

\* v1 and v2 use different tokenizers and were trained in different regimes, so a
single raw loss number is not directly comparable. The rigorous, tokenizer-
agnostic metric is **bits-per-character (BPC)** on the fixed held-out test
(`test.txt`). v1's headline figure is its Tiny-Shakespeare validation loss
of **1.46**, which lives in the same "data-starved character model" regime as the
LLM-assisted research experiment's controlled baseline (BPC **2.395**). The controlled experiment
took that regime down to **1.919** — a 20% reduction — which v2 embodies.

## What changed from v1 → v2

The LLM-assisted research experiment isolated three improvements (and one instructive failure):

1. **More data** — Tiny Shakespeare → the full Complete Works (−15% BPC). v1 was
   overfitting; it was starved for data.
2. **Modern architecture** — RoPE + RMSNorm + bias-free (−1.6%).
3. **BPE tokenizer** — character-level → GPT-2 byte-pair encoding (−4.3%).
4. *(Rejected)* A "champion" round added more dropout + longer training to push
   further; it **regressed** (1.919 → 1.947). The model is data-bottlenecked, and
   you cannot regularize away too little data. v2 is therefore Round 3, not the
   champion.

## Rebuild a version

Weights are gitignored; regenerate them from the committed code. Each version has
a **self-contained folder** under [`models/`](models/README.md) that runs in place
with no arguments — the hyperparameters live in each folder's `config.py`, and
`prepare.py` auto-downloads the corpus on first run.

**v1 — `shakespeare-nanogpt-1`:**
```bash
cd models/shakespeare-nanogpt-1
python prepare.py     # downloads Tiny Shakespeare, builds the dataset here
python train.py       # -> ./ckpt.pt
python eval.py        # score on the shared held-out test (BPC)
python sample.py --start="ROMEO:"
```

**v2 — `shakespeare-nanogpt-2`:**
```bash
cd models/shakespeare-nanogpt-2
python prepare.py     # downloads the Complete Works, BPE-encodes it here
python train.py       # -> ./ckpt.pt
python eval.py        # score on the shared held-out test (expect BPC ~1.919)
python sample.py --start="ROMEO:"
```

> The `models/` folders are the canonical, self-contained way to rebuild a
> version — and `models/shakespeare-nanogpt-1/` is what the player (not yet built)
> will sample from. The shared engine can still re-run v2's recipe directly via
> `core/nanogpt_core/train.py` (writing to `projects/shakespeare/runs/r3-bpe/`, the
> experiment's own output). See [`models/README.md`](models/README.md) for how the
> `models/` and `core/` trees relate.

## Check out a version's exact repo state

```bash
git checkout shakespeare-nanogpt-1   # the project as v1 (baseline, pre-research-lab)
git checkout shakespeare-nanogpt-2   # the project as v2 (adds the LLM-assisted research experiment + v2 recipe)
git checkout main                    # back to latest
```

## An ongoing practice (how new versions happen)

This is not a one-off experiment — it's a repeatable loop, and the intent is to
keep running it: refine the model over time and release new versions as the
research warrants. Each future version will:

- come from one or more new **research rounds** (new data, architectures, tokenizers,
  or training recipes), with Claude as the researcher and a human keeping oversight;
- be scored on the **same fixed held-out test** (`test.txt`) in
  bits-per-character, so progress is comparable across the entire series;
- get its own **git tag** (`shakespeare-nanogpt-N`), a row in
  `leaderboard.md`, an entry in this file, and eventually a Hugging Face
  revision.

The clearest next direction: v2's ceiling is **data**. Round 4 showed that
regularization and longer training cannot substitute for it, so a future version
likely means more or better training data — then re-running the loop from there.

_(A Hugging Face release of these versions is planned but not yet done.)_
