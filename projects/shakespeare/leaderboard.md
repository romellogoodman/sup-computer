# LLM-Assisted Research Leaderboard

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

## Results

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

## Caveat: results are single-seed

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

## 🏆 Best model: `r3-bpe` — BPC 1.919

The overall winner is Round 3, which already combines all three productive levers
(full data + modern architecture + BPE tokenizer). End-to-end: **BPC 2.395 → 1.919,
a 20% reduction** over the controlled baseline. The Round-4 "champion" experiment
showed the next intuitive step makes it worse.

**This model is released as `shakespeare-nanogpt-2` (v2)** — the original baseline
is `shakespeare-nanogpt-1` (v1). See [`MODELS.md`](MODELS.md) for both specs
and rebuild commands.

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

## Snapshots (Claude cumulative tokens, for computing per-round deltas)

| Marker | output | all-in |
|--------|--------|--------|
| before Round 1 | 254,743 | 17,062,778 |
| after Round 1  | 321,302 | 23,301,423 |
| after Round 2  | 372,137 | 27,986,409 |
| after Round 3  | 395,075 | 31,789,759 |
| after Round 4  | 487,653 | 40,400,672 |

## Notes per round

_(round write-ups land here as we go)_
