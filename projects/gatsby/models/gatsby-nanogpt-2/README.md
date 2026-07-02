# gatsby-nanogpt-2

The **green-light dial** model, with the same behaviour as
[`gatsby-nanogpt-1`](../gatsby-nanogpt-1/) — a character-level GPT that can't stop
reaching for **Jay Gatsby's green light**, with a `[green=N]` intensity dial baked
into the data — but its corpus is written by a **mixture of four local open
models** instead of the Claude API. Research run `mix-2k-r2`; see
[Experiment 04](../../../../research-docs/reports/mixture-of-models.md).

This folder is a **frozen, self-contained snapshot** of exactly the code + corpus
that produces v2, copied out of the project root so the working pipeline can keep
evolving without changing how this released version is built
(see [ADR-0003](../../../../docs/adr/0003-frozen-self-contained-releases.md) and
[`docs/releasing.md`](../../../../docs/releasing.md)). It runs **in place** with
**no API key and no LM Studio** — the corpus is vendored here as `raw.txt`.

- Tokenizer: character-level (80-char vocab, derived from the corpus)
- Data: synthetic TinyStories-register corpus, **2000 stories / ~1.53M chars**, vendored as `raw.txt`. Written by a **local mixture** — Olmo 3 .30 / Ministral 3 .30 / Gemma 4 .20 / Granite 4.1 .20 — via [`tools/synthgen`](../../../../tools/synthgen/README.md) ([ADR-0014](../../../../docs/adr/0014-synthgen-local-llm-pipeline.md)). **$0** marginal cost.
- Architecture: base char-level nanoGPT (LayerNorm, learned position embeddings, biases)
- Size: 6 layers · 6 heads · 384 embd · 512 context · ~10.65M params
- Best checkpoint: val loss **0.622** @ step ~2000 (MPS) — trained 60% deeper than Round 1 before overfitting
- Model card: [`research-docs/model-cards/gatsby-nanogpt-2.md`](../../../../research-docs/model-cards/gatsby-nanogpt-2.md)
- Research journal: [`../../research/`](../../research/)
- Git tag: `gatsby-nanogpt-2`

## Reproduce

Everything runs in place from this folder; generated files (`train.bin`,
`val.bin`, `meta.pkl`, `ckpt.pt`) stay here and are gitignored. The vendored
`raw.txt` is committed — no model is downloaded and no generation is run.

```bash
cd models/gatsby-nanogpt-2
python prepare.py     # raw.txt -> train.bin / val.bin / meta.pkl (here)
python train.py       # trains -> ./ckpt.pt (best-val ~step 2000; knobs in config.py)
python sample.py --start="[green=5] [green=5] [green=5] obsession=total
topic: a dog and a balloon
"
```

The corpus was written by `../../generate_mixture.py` (the gatsby driver) over
[`tools/synthgen`](../../../../tools/synthgen/README.md) + LM Studio. That
**generation** path is not vendored here (it needs LM Studio + the four models);
it is not needed to reproduce the model, which trains from the vendored `raw.txt`.

## Priming format (the contract)

Identical to v1 — the v3 "louder" control line, repeated 3× plus a per-level word:

```
[green=N] [green=N] [green=N] obsession=<word>
topic: <anything>
```

where `N ∈ 1..5` and the word is `1=faint 2=soft 3=strong 4=heavy 5=total`.
`prime.py` is the single source of truth for this string.

## The dial (r2 result)

Average green-light mentions per **480** generated tokens, swept across levels.
The endpoints separate (a working knob, recovered from Round 1's flat dial by
rebalancing the model mixture); the middle is compressed:

| level | 1 | 2 | 3 | 4 | 5 |
|-------|------|------|------|------|------|
| avg green mentions | 3.72 | 4.78 | 4.67 | 4.50 | 6.06 |

`python eval_dial.py` reproduces this against `./ckpt.pt` (uses the vendored
`prime.py`, no external dependency). Obsession is reliable on arbitrary topics;
topic-honoring is unreliable and coherence is rough (baseline-level, inherited
from v1) — see the model card and journal for the honest limitations.

## Files

| File | Role |
|------|------|
| `model.py` | the GPT architecture (base char-level nanoGPT) |
| `config.py` | this model's hyperparameters (auto-loaded by `train.py`) |
| `train.py` | training loop; writes `ckpt.pt` here |
| `sample.py` | generate text from `ckpt.pt` given a `[green=N] ...` prime |
| `prepare.py` | build the dataset into this folder from `raw.txt` |
| `prime.py` | the `[green=N] ... obsession=<word>` control-line builder (single source of truth) |
| `eval_dial.py` | sweep green=1..5 and count green-light mentions (the dial) |
| `configurator.py` | nanoGPT's `--key=value` override helper |
| `raw.txt` | the vendored mixture corpus (2000 stories; committed, not regenerated) |
