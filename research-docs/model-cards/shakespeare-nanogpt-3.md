---
license: mit
language:
  - en
library_name: nanogpt
pipeline_tag: text-generation
tags:
  - shakespeare
  - nanogpt
  - bpe
  - gpt
  - rope
  - rmsnorm
  - educational
datasets:
  - shakespeare-complete-works
---

# Model Card — `shakespeare-nanogpt-3` (v3)

<div class="takeaways">
<p class="takeaways-label">Key takeaways</p>
<ul>
<li>The new series best: an enlarged early-modern-drama corpus + a <strong>1024-token, corpus-trained byte-level BPE</strong> + float32 training, reaching held-out <code>BPC 1.831</code> at just 11.02M params.</li>
<li>The headline is <strong>parameter efficiency</strong>: it beats the prior champion v2 (1.919 at 29.9M) and matches-or-beats a fresh float32 GPT-2-vocab control (1.843 at 29.9M) at ~1/3 the parameters.</li>
<li>The BPC edge over that fresh control is only −0.012 — <strong>within single-seed noise</strong>. The clean wins are the params efficiency and beating the prior champion; a multi-seed run is the stated next step.</li>
</ul>
</div>

The current best model in the [`shakespeare-nanogpt`](../../projects/shakespeare/README.md)
series: held-out BPC 1.831 at ~11.02M params, about a third the size of the
champion it beats. Where [v2](shakespeare-nanogpt-2.md) established the modern
architecture (RoPE, RMSNorm, bias-free) on the Complete Works with GPT-2 BPE,
**v3 changes the data and the tokenizer, not the architecture**: it trains a
small vocabulary *on the corpus itself*, enlarges that corpus with contemporary
early-modern drama, and trains in float32. This remains LLM-assisted research —
Claude as the *researcher* under human direction — not recursive
self-improvement.

> **Series note.** Successor to [`shakespeare-nanogpt-2`](shakespeare-nanogpt-2.md).
> All versions and the full story are in [`MODELS.md`](../../projects/shakespeare/README.md#versions);
> the scoreboard is [`leaderboard.md`](../../projects/shakespeare/README.md#leaderboard).

## Model details

| | |
|---|---|
| **Version / git tag** | `shakespeare-nanogpt-3` |
| **Origin** | LLM-assisted research, round 6 float32 re-run (`projects/shakespeare/runs/r6-fp32-bpe1k`) |
| **Architecture** | modern — RoPE, RMSNorm, bias-free (`core/nanogpt_core/model.py`, vendored into the frozen folder) |
| **Size** | ~11.02M params (6 layers · 6 heads · 384 embd · 256 context) |
| **Tokenizer** | 1024-vocab byte-level BPE, trained on the enlarged corpus (committed `tokenizer.json`; the `meta.pkl` seam, ADR-0012) |
| **Precision** | float32 (eliminates the MPS float16 large-vocab logit overflow that confounded round 5) |
| **Checkpoint** | `models/shakespeare-nanogpt-3/ckpt.pt` (weights not committed — rebuild below) |
| **Built on** | [nanoGPT](https://github.com/karpathy/nanoGPT) by Andrej Karpathy (MIT) |
| **Developed with** | Claude Fable 5 ([Claude Code](https://claude.com/claude-code)) as researcher, human oversight |
| **License** | MIT |

## Intended use

A **learning project** and a demonstration of LLM-assisted model development
(measured honestly, version over version). Given a few characters it continues
them in gibberish-but-convincingly-styled Early Modern English. v3's samples pick
up conventions from the wider corpus — speaker labels and the italic `_Name._`
stage-direction convention of the Marlowe/Webster editions.

**Out of scope:** real use of the text; any presentation of output as genuine
Shakespeare (or Marlowe, Jonson, etc.) or as fact. No instruction following, no
safety tuning. This is mimicry only.

## Training data

The **enlarged early-modern-drama corpus**: Shakespeare's Complete Works
(Gutenberg #100, ~5 MB) plus public-domain contemporary drama — Marlowe (*Doctor
Faustus*, both *Tamburlaine*s, *Edward II*, *The Jew of Malta*), Jonson
(*Volpone*, *The Alchemist*, *Every Man in His Humour*), Kyd (*The Spanish
Tragedy*), Webster (*The Duchess of Malfi*, *The White Devil*), and Dekker. Total
training text ~7.85M characters; the tokenizer is trained on the training split
only.

Crucially, the **held-out test set is unchanged**: the same fixed
250k-character Shakespeare slice (`projects/shakespeare/test.txt`) every version
in the series is scored on. It is excluded from training and never duplicated —
so v3's BPC stays directly comparable to v1 and v2 despite the larger, broader
training corpus. Enlarging the corpus also eliminated the overfit that defined
v2's rounds: validation loss fell monotonically instead of bottoming early.

## Training procedure

Trained with the vendored `train.py` on Apple Silicon (MPS), `dtype=float32`,
`lr=1e-3`, `block_size=256`, 2000 iterations, best-val checkpoint. Float32 is the
load-bearing change: round 5 hit a float16 instability on MPS (the CUDA-only
`GradScaler` is disabled there, so large-vocab logits overflowed and forced the
larger vocabularies to a crippled learning rate). Re-running every vocabulary at
float32 removed the overflow and let `bpe1k` vs the GPT-2 control finally be
compared apples-to-apples.

## Evaluation

Scored on the fixed held-out test in **bits-per-character (BPC)** — a
tokenizer-agnostic metric (total NLL of the test text ÷ its character count ÷
ln 2), so char-level, GPT-2-BPE, and custom-BPE models are all directly
comparable. Lower is better.

| Model | Tokenizer | Params | Test BPC |
|-------|-----------|-------:|---------:|
| `shakespeare-nanogpt-1` (v1) | char (65) | 10.66M | 2.395 |
| `shakespeare-nanogpt-2` (v2) | GPT-2 BPE (50257) | 29.94M | 1.919 |
| r6 float32 GPT-2 control | GPT-2 BPE (50257) | 29.94M | 1.843 |
| **`shakespeare-nanogpt-3` (v3)** | **BPE (1024)** | **11.02M** | **1.831** |
| r6 float32 `bpe4k` (unreleased) | BPE (4096) | 12.19M | 1.813 |

Two clean results and one honest caveat:

- **Parameter efficiency (clean win).** v3 reaches equal-or-better BPC than the
  50k-vocab models at ~1/3 the parameters. Of v2's 29.9M parameters, ~19.3M
  *was* the GPT-2 embedding table; a 1024-vocab embedding is ~0.4M. That budget
  buys capability instead of a giant vocabulary the Shakespeare domain never uses.
- **Beats the prior champion (clean win).** 1.831 < v2's 1.919 (−4.6%). All three
  float32 models clear 1.919 — partly because float32 helps every vocabulary (the
  GPT-2 control alone improves 1.919 → 1.843).
- **The edge over the fresh control is within noise (the caveat).** v3's −0.012
  over the float32 GPT-2 control (1.831 vs 1.843) is smaller than the series' known
  single-seed wobble; the `bpe4k` run is even lower (1.813) but likewise unreplicated.
  Read the *vs-control* and *bpe1k-vs-bpe4k* gaps as **directionally promising, not
  decisive.**

> **Chart to add (dataviz pipeline).** A grouped horizontal bar chart, *held-out
> BPC vs. parameter count* for the five rows above, would make the efficiency
> headline visible at a glance — v3 and the unreleased `bpe4k` sitting lowest on
> BPC while also furthest left on params, the two 29.9M GPT-2-vocab models to
> their right. Per repo convention this must be generated by
> [`dataviz/`](../../tools/dataviz/README.md) (add it to `build.py`), not
> hand-authored; it is described here rather than embedded because that build step
> is deferred.

## Limitations

- **Single-seed measurements.** Every score is one training run at a fixed seed
  (`1337`), no variance estimate. v3's win over the *fresh float32 control* and its
  gap to the unreleased `bpe4k` are within plausible run-to-run noise. The clear
  results (params efficiency; beating the prior champion) do not depend on that
  narrow margin. Multi-seed replication is the explicit next step — it is what
  would turn "bpe1k is tied-best" into "bpe1k is best."
- **`bpe1k` was still improving.** In round 5 its validation loss had not
  plateaued at 2000 iterations; more iterations would likely lower BPC further, so
  1.831 is an under-trained floor, not a tuned optimum.
- **Domain-narrow test, broadened train.** The training corpus now includes
  non-Shakespeare drama, but the test set is still pure Shakespeare — the metric
  rewards Shakespeare mimicry specifically.
- **Still mimicry:** fluent early-modern *texture*, but no meaning, knowledge, or
  factuality; no instruction following or safety tuning.

## How to use

The BPE steps need the Hugging Face `tokenizers` library, provided ad hoc:

```bash
# self-contained v3 folder (weights are gitignored — rebuild them)
cd projects/shakespeare/models/shakespeare-nanogpt-3
uv run --with tokenizers python prepare.py   # downloads the enlarged corpus, encodes here
uv run python train.py                        # -> ./ckpt.pt (zero-arg run reproduces v3)
uv run --with tokenizers python eval.py       # score on the shared held-out test (expect BPC ~1.831)
uv run --with tokenizers python sample.py --start="ROMEO:"
```

The 1024-token `tokenizer.json` is committed and never retrained — `prepare.py`
only re-encodes with it, pinning the exact vocabulary.

## Citation / credits

- nanoGPT by Andrej Karpathy (MIT) — model + training code.
- The Complete Works of Shakespeare and the contemporary early-modern drama
  (Marlowe, Jonson, Kyd, Webster, Dekker) — all public domain (Project Gutenberg).
- LLM-assisted research run with Claude Fable 5 (Claude Code) as researcher, human oversight.
