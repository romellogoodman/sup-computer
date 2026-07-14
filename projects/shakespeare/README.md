# shakespeare-nanogpt

A tiny character-level GPT trained from scratch on the works of Shakespeare.
Give it a few characters and it continues them in gibberish but
convincingly-styled Early Modern English — character by character.

This is a personal learning project: my first time training a language model.

```
ROMEO:
Thou hadst to do it.

CORIOLANUS:
That art sure to my husband, and I
Am come to this day.
```
*(actual output from this model, prompted with "ROMEO:")*

---

## What this is

- A **character-level GPT** ([nanoGPT](https://github.com/karpathy/nanoGPT) by
  Andrej Karpathy, vendored), trained on Shakespeare on a laptop in minutes.
- A small, ongoing **LLM-assisted research series**: Claude acts as the
  researcher (under human direction) improving the model version over version.
- Three released versions so far — v1 (the base char-level baseline), v2
  (modern architecture + GPT-2 BPE, BPC 1.919), and v3 (the current champion:
  a corpus-trained 1k-vocab BPE that beats v2 at a third the size, BPC 1.831).
  Full specs, git tags, and rebuild commands are in [Versions](#versions) below.

It's deliberately *not* recursive self-improvement — a human sets direction and
keeps oversight while Claude implements, tests, and measures. The full story is in
[`research-docs/reports/`](../../research-docs/reports/).

## Repository structure

This project lives in a monorepo. Its own folder holds the datasets, configs, run
outputs, and released models; the shared engine and the shared docs/charts live
alongside it:

```
projects/shakespeare/
├── models/            Released versions — each a FROZEN, self-contained, runnable
│   ├── shakespeare-nanogpt-1/   folder (model · config · train · sample · eval ·
│   ├── shakespeare-nanogpt-2/   prepare). Run any of them in place; no shared deps.
│   └── shakespeare-nanogpt-3/
│
├── config/            Training configs for new experiment rounds.
├── data/              The datasets (each with its own prepare.py).
├── runs/              Per-round experiment outputs (configs, logs, eval results).
├── test.txt           The fixed held-out test every version is scored on.
├── README.md          This file — including the version index and leaderboard.
└── CLAUDE.md          Rules for agents (and humans) editing the project.

Elsewhere in the monorepo:
../../core/            The shared nanoGPT engine (modern architecture by default):
                       training, sampling, eval, export. New versions are developed
                       here, then snapshotted into this project's models/.
../../tools/dataviz/   Zero-dependency chart pipeline (matches the website's
                       document style) — the single source of every chart.
../../research-docs/   The WRITE-UPS (prose, not code):
  ├── reports/           frozen experiment reports + charts
  └── model-cards/       a Hugging Face-style card per version
```

Two ideas drive the layout:

- **`models/` vs the shared engine** — releases vs. the lab. The engine in
  `../../core/` keeps changing; a released version copies its code into
  `models/<version>/` so it stays reproducible forever (the duplication is
  intentional).
- **Weights are never committed.** Everything needed to *rebuild* them is — the
  `prepare.py` scripts auto-download the corpora on first run.

## Quick start

One-time setup (Python 3.9+; an Apple Silicon Mac for fast training):

```bash
uv sync   # creates .venv and editable-installs the shared engine + this project
```

Train and sample the base model (v1) — everything runs inside its folder:

```bash
cd models/shakespeare-nanogpt-1
python prepare.py    # downloads Tiny Shakespeare, builds the dataset here
python train.py      # ~12–15 min on Apple Silicon -> ./ckpt.pt
python sample.py --start="ROMEO:" --num_samples=1 --max_new_tokens=1000
```

`python train.py` with no arguments reproduces the version; hyperparameters (and
the main quality dial, `max_iters`) live in that folder's `config.py`, and any
knob can be overridden inline, e.g. `python train.py --max_iters=5000`. The same
four commands rebuild v2 and v3 in their own `models/` folders — see
[Versions](#versions).

To run a *new* experiment round against the shared engine (the modern
architecture is the default now), use the monorepo's `core/` from the repo root:

```bash
uv run python core/nanogpt_core/train.py projects/shakespeare/config/train_shakespeare_mac.py \
    --out_dir=projects/shakespeare/runs/r1
uv run python core/eval/eval.py projects/shakespeare/runs/r1 \
    --test projects/shakespeare/test.txt --data_root projects/shakespeare/data
```

The latest release also runs in the browser — the studio site's
`/model-player` page runs it client-side via
[`@supcomputer/player`](../../player/) ([ADR-0024](../../docs/adr/0024-model-player-page-and-artifact-conventions.md)) —
and in the terminal via the [`sup` CLI](../../cli/). The sample commands above
remain the offline path.

## Versions

This is a **living, versioned series of models**, refined over time through
LLM-assisted research — Claude acting as the researcher, implementing, testing,
and evaluating changes under human direction. Deliberately *not*
[recursive self-improvement](https://www.anthropic.com/institute/recursive-self-improvement).
Each version is a checkpoint in that ongoing process, pinned to a git tag and
scored on the same fixed held-out test (`test.txt`) in bits-per-character, so
progress is comparable across the entire series.

Per [ADR-0020](../../docs/adr/0020-one-home-per-fact.md) this section is the
series *index*; each fact's detail lives in its one home — specs in
[`registry.json`](../../registry.json), scores in the
[leaderboard](#leaderboard) below, each version's narrative in its
[model card](../../research-docs/model-cards/).

| | `shakespeare-nanogpt-1` (v1) | `shakespeare-nanogpt-2` (v2) | `shakespeare-nanogpt-3` (v3) |
|---|---|---|---|
| **What it is** | the original char-level baseline — data-starved on purpose | the first research experiment's winner: modern arch + BPE on the Complete Works | the r6 float32 winner: a 1024-vocab corpus-trained BPE on an enlarged corpus, at ~1/3 v2's params |
| **Git tag** | `shakespeare-nanogpt-1` | `shakespeare-nanogpt-2` | `shakespeare-nanogpt-3` |
| **Frozen code** | [`models/shakespeare-nanogpt-1/`](models/shakespeare-nanogpt-1/) | [`models/shakespeare-nanogpt-2/`](models/shakespeare-nanogpt-2/) | [`models/shakespeare-nanogpt-3/`](models/shakespeare-nanogpt-3/) |
| **Model card** | [v1 card](../../research-docs/model-cards/shakespeare-nanogpt-1.md) | [v2 card](../../research-docs/model-cards/shakespeare-nanogpt-2.md) | [v3 card](../../research-docs/model-cards/shakespeare-nanogpt-3.md) |
| **Held-out test BPC** | 2.395* | 1.919 | **1.831** |

\* v1's regime figure: the controlled data-starved baseline the experiment set
out to beat. (v1's own headline was its Tiny-Shakespeare val loss of 1.46 —
different tokenizers make raw losses incomparable, which is why the series
yardstick is BPC on the fixed `test.txt`.)

### How v1 became v2

More data (the win), modern architecture, BPE — and the regularization round
that regressed and was rejected. The full story, round by round, is the report
[Can a big model improve a small one?](../../research-docs/reports/improve-a-small-model.md).

### How v2 became v3

The architecture didn't change (v2 already had RoPE + RMSNorm + bias-free). v3
changes **data, tokenizer, and precision**:

- **A 1024-vocab byte-level BPE trained on the corpus itself**, replacing v2's
  50k-vocab GPT-2 BPE. The Shakespeare domain never uses most of GPT-2's
  vocabulary; a small corpus-trained vocab drops the embedding table from ~19.3M
  to ~0.4M parameters, taking the model from ~29.9M to ~11.0M — about 1/3 the
  size.
- **An enlarged corpus** — Shakespeare's Complete Works plus public-domain
  contemporary drama (Marlowe, Jonson, Kyd, Webster, Dekker). More data
  eliminated the overfit that defined v2's rounds (val loss now falls
  monotonically). The held-out `test.txt` is unchanged, so BPC stays comparable.
- **float32 training**, which removed an MPS float16 large-vocab logit overflow
  and let every vocabulary train cleanly at `lr=1e-3`.

Result: BPC 1.919 → 1.831 at ~1/3 the params. v3 also matches-or-beats a
fresh float32 GPT-2-vocab control (1.843, 29.9M), though that particular edge
(−0.012) is within single-seed noise — the clean wins are the parameter
efficiency and beating the prior champion. Multi-seed replication is the next
step. See the [v3 model card](../../research-docs/model-cards/shakespeare-nanogpt-3.md).

### Rebuild a version

Weights are gitignored; regenerate them from the committed code. Each version's
frozen folder runs **in place** with no arguments (the Quick start above shows
the four commands). To see the exact repo state that shipped a version:

```bash
git checkout shakespeare-nanogpt-2   # the project as v2
git checkout main                    # back to latest
```

### New versions

A research round that finds a real improvement becomes v4 (and so on): a new
frozen `models/shakespeare-nanogpt-N/` folder, a git tag, a scored leaderboard
row, a registry entry, and a model card — the checklist is in
[`docs/handbook.md`](../../docs/handbook.md#releasing-a-version). The clearest
next direction is **multi-seed replication**: v3's win over the fresh float32
control (and the `bpe1k`-vs-`bpe4k` gap) is within single-seed noise and needs
seed-replication to resolve.

## Leaderboard

A log of every attempt by Claude Opus 4.8 (the "researcher") to improve the
small Shakespeare GPT. This is **LLM-assisted research** — Claude as an
automated researcher under human direction — deliberately *not* recursive
self-improvement, which [Anthropic defines](https://www.anthropic.com/institute/recursive-self-improvement)
as an AI autonomously designing its own successor; we are not there yet. The
goal: drive **held-out test loss** down, while tracking **two costs** per
round —

- **Model train tokens** — tokens the nanoGPT processed = `tokens/iter × iters`
  (`tokens/iter = batch_size × block_size × grad_accum`). The *training* cost.
- **Claude tokens** — tokens Claude burned designing/implementing/analyzing the
  round, measured from the session transcript via `../../tools/claude_cost.py`
  (delta between the snapshot before and after the round). The *researcher* cost.

The question this answers: **how much intelligence does each unit of
improvement cost, and is that ratio getting better or worse over rounds?**

### Results

| Run | Change | Dataset | **Test BPC** | token_loss | Model train tok | Train time | Claude tok (out / all-in) |
|-----|--------|---------|-----------|-----------|-----------------|-----------|---------------------------|
| `baseline` (out-shakespeare-char) | original baby GPT | Tiny (1.1MB) | — (val 1.4565)* | — | 32.8M | ~16 min | (setup session) |
| `r1-data-small` | control: 1MB subset | Full-1MB | 2.395 | 1.660 | 32.8M | ~16 min | — |
| **`r1-data-full`** ⭐ | **treatment: full 5MB** | Full-5MB | **2.036** | 1.411 | 32.8M | ~16 min | R1 total: +66.6K / +6.24M |

| **`r2-arch-modern`** ⭐ | RoPE + RMSNorm + bias-free | Full-5MB | **2.004** | 1.389 | 32.8M | ~16 min | R2: +50.8K / +4.68M |

**Round 1 verdict:** more data wins big — **BPC 2.395 → 2.036 (−15%)**. The control
overfit (train 1.08 / test 2.395); the full model generalized (train 1.23 /
test 2.036). `shakespeare_full` carries forward as the dataset for later rounds.
Researcher efficiency: **0.359 BPC reduction per 66.6K Claude output tokens.**

| **`r3-bpe`** ⭐ | char → GPT-2 BPE (modern arch) | Full-BPE | **1.919** | 4.100 | 32.8M | ~20 min | R3: +22.9K / +3.80M |

**Round 2 verdict:** modern architecture beats the original on identical data —
**BPC 2.036 → 2.004 (−1.6%)**. Real but small. Researcher efficiency collapsed to
**0.032 BPC per 50.8K tokens (~0.63 BPC / M-out)** — roughly **10× less efficient
than Round 1**. Classic diminishing returns: same researcher effort, far less
payoff once the data bottleneck is fixed. `model_modern` (now the canonical
`core/nanogpt_core/model.py`) carries forward.

| `r4-champion` | + dropout 0.3 + 4000 iters (fight R3 overfit) | Full-BPE | 1.947 ❌ | 4.160 | 65.5M | ~50 min | R4: +92.6K / +8.61M (incl. report) |

**Round 3 verdict:** BPE beats char-level — **BPC 2.004 → 1.919 (−4.3%)** — despite
overfitting (val loss bottomed at step ~1000 then rose; the save-best-val policy
auto-kept the early checkpoint). 30M params (3× bigger, 50k vocab). Efficiency
**rebounded to 3.76 BPC / M-out** because the modern stack was reused — marginal
researcher cost was low. BPE + modern + full data **is** the champion.

**Round 4 verdict — instructive FAILURE.** The attempt to push past R3 with more
dropout + longer training **regressed**: BPC 1.919 → 1.947. The extra dropout did
not stop the overfit (val rose monotonically 4.58 → 5.06 across 4000 iters) and
slowed convergence, so the best checkpoint was worse than R3's. Samples collapsed
into "Romeo, Romeo" loops. **The data bottleneck dominates — you cannot regularize
away too few tokens.** A wrong researcher intuition, caught by verification.

### Rounds 5–6 — the XL data + small-vocab + float32 round (researcher: Claude Fable 5)

Acting on Round 4's lesson ("data is the ceiling"), Round 5 **enlarged the corpus**
(Shakespeare + public-domain Marlowe/Jonson/Kyd/Webster/Dekker) and swapped GPT-2's
50k vocab for a **byte-level BPE trained on the corpus itself**. Round 6 re-ran every
vocabulary at **dtype=float32** to remove an MPS float16 large-vocab logit overflow
that had confounded Round 5's larger-vocab controls. Same block_size=256, 2000 iters,
best-val checkpoint; scored on the same `test.txt`.

| Run | Change | Tokenizer | Params | **Test BPC** |
|-----|--------|-----------|-------:|-----------|
| **`r6-fp32-bpe1k`** ⭐ | enlarged corpus + 1024-vocab corpus-trained BPE, float32 | bpe1024 | 11.02M | **1.831** |
| `r6-fp32-bpe4k` | same, 4096-vocab (unreleased) | bpe4096 | 12.19M | 1.813 |
| `r6-fp32-gpt2` (control) | same corpus, GPT-2 vocab, float32 | gpt2-50257 | 29.94M | 1.843 |

**Rounds 5–6 verdict.** The corpus-trained small vocabularies **match or beat** the
50k-vocab GPT-2 model at **~1/3 the parameters** — the clean result is
params-efficiency. All three float32 models also beat the prior champion's 1.919
(float32 alone lifts the GPT-2 control to 1.843). The BPC edge of `bpe1k` over the
fresh float32 control (−0.012) and its gap to `bpe4k` (+0.018) are **within
single-seed noise**; the next round is multi-seed to resolve them. `r6-fp32-bpe1k`
is released as **`shakespeare-nanogpt-3`** (smallest; BPC tied-best within noise).

### Caveat: results are single-seed

Every run above used the **same fixed RNG seed** (`torch.manual_seed(1337)`), so the
table reports **one sample per recipe with no run-to-run variance estimate**.
Training is stochastic (random weight init + batch order), so each BPC is a point
draw, not a fixed property of the recipe.

- The **large** deltas — R1's −0.359 (more data) and R3's −0.085 (BPE) — are well
  outside any plausible seed-to-seed wobble and are almost certainly real signal.
- The two **small** deltas — R2's −0.032 (modern arch) and R4's +0.028 (champion
  regression) — are within the range a different seed could plausibly produce.
  Read them as *direction uncertain*, not clean win/loss, until backed by a
  multi-seed run.

**Going forward**, the seed is now an explicit, recorded knob (`--seed=N` on
`train.py`, logged in each run's config), and future rounds report results across
**multiple seeds** so every delta can be compared against its own noise band.

### 🏆 Best model: `r6-fp32-bpe1k` — BPC 1.831 (released as `shakespeare-nanogpt-3`)

> **Superseded.** Rounds 5–6 (above) took the series best from 1.919 to **1.831**
> at **~1/3 the parameters** by enlarging the corpus, training a 1024-vocab BPE on
> it, and using float32. `r6-fp32-bpe1k` is released as
> **`shakespeare-nanogpt-3` (v3)**. The Experiment-01 winner below (`r3-bpe`,
> released as v2) remains the historical record of that first four-round experiment.

The overall winner is Round 3, which already combines all three productive levers
(full data + modern architecture + BPE tokenizer). End-to-end: **BPC 2.395 → 1.919,
a 20% reduction** over the controlled baseline. The Round-4 "champion" experiment
showed the next intuitive step makes it worse.

**This model is released as `shakespeare-nanogpt-2` (v2)** — the original baseline
is `shakespeare-nanogpt-1` (v1); see [Versions](#versions).

### Researcher-efficiency curve (BPC reduction per 100K Claude output tokens)

| Round | ΔBPC | Claude out tok | Efficiency (ΔBPC / 100K) |
|-------|------|----------------|--------------------------|
| 1 Data | −0.359 | 66.6K | **0.539** (huge — real bottleneck) |
| 2 Architecture | −0.032 | 50.8K | 0.063 (~10× worse — polishing) |
| 3 Tokenization | −0.086 | 22.9K | 0.376 (rebounds — reused work) |
| 4 Champion | +0.028 | 92.6K | **negative** (spent tokens, got worse) |

\* baseline's `1.4565` is val loss on Tiny Shakespeare's own val split — a
different test set than the research rounds use, so it's a reference point, not a
directly-comparable row. From Round 1 on, every model is scored by `../../core/eval/eval.py`
on the **same held-out test set** carved from the Complete Works.

### Snapshots (Claude cumulative tokens, for computing per-round deltas)

| Marker | output | all-in |
|--------|--------|--------|
| before Round 1 | 254,743 | 17,062,778 |
| after Round 1  | 321,302 | 23,301,423 |
| after Round 2  | 372,137 | 27,986,409 |
| after Round 3  | 395,075 | 31,789,759 |
| after Round 4  | 487,653 | 40,400,672 |

## Learn more

- **[`research-docs/reports/`](../../research-docs/reports/)** — the experiment write-ups
  with charts (start with [Can a big model improve a small one?](../../research-docs/reports/improve-a-small-model.md)).
- **[`research-docs/model-cards/`](../../research-docs/model-cards/)** — per-version model
  cards (intended use, data, evaluation, limitations).

## Credits

- [nanoGPT](https://github.com/karpathy/nanoGPT) by Andrej Karpathy (MIT License,
  retained in `LICENSE`) — the model and training code.
- The Tiny Shakespeare dataset, via Karpathy's `char-rnn`.
- Set up, trained, and wired up end-to-end with **Claude Opus 4.8**
  ([Claude Code](https://claude.com/claude-code)).
