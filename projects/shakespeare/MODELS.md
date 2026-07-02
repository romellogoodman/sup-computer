# Model versions

This is a **living, versioned series of models**, refined over time through
LLM-assisted research — Claude acting as the researcher, implementing, testing,
and evaluating changes under human direction (deliberately *not*
[recursive self-improvement](https://www.anthropic.com/institute/recursive-self-improvement)).
Each version is a checkpoint in that ongoing process, pinned to a git tag and
scored on the same fixed held-out test (`test.txt`) in bits-per-character, so
progress is comparable across the entire series.

Per [ADR-0020](../../docs/adr/0020-one-home-per-fact.md) this file is the
series *index*; each fact's detail lives in its one home — specs in
[`registry.json`](../../registry.json), scores in
[`leaderboard.md`](leaderboard.md), each version's narrative in its
[model card](../../research-docs/model-cards/).

| | `shakespeare-nanogpt-1` (v1) | `shakespeare-nanogpt-2` (v2) | `shakespeare-nanogpt-3` (v3) |
|---|---|---|---|
| **What it is** | the original char-level baseline — data-starved on purpose | the first research experiment's winner: modern arch + BPE on the Complete Works | the r6 float32 winner: a 1024-vocab corpus-trained BPE on an enlarged corpus, at ~1/3 v2's params |
| **Git tag** | `shakespeare-nanogpt-1` | `shakespeare-nanogpt-2` | `shakespeare-nanogpt-3` |
| **Frozen code** | [`models/shakespeare-nanogpt-1/`](models/shakespeare-nanogpt-1/) | [`models/shakespeare-nanogpt-2/`](models/shakespeare-nanogpt-2/) | [`models/shakespeare-nanogpt-3/`](models/shakespeare-nanogpt-3/) |
| **Model card** | [v1 card](../../research-docs/model-cards/shakespeare-nanogpt-1.md) | [v2 card](../../research-docs/model-cards/shakespeare-nanogpt-2.md) | [v3 card](../../research-docs/model-cards/shakespeare-nanogpt-3.md) |
| **Held-out test BPC** | 2.395* | 1.919 | **1.831** |

\* v1's regime figure: the controlled data-starved baseline the experiment set
out to beat. (v1's own headline was its Tiny-Shakespeare val loss of **1.46** —
different tokenizers make raw losses incomparable, which is why the series
yardstick is BPC on the fixed `test.txt`.)

## How v1 became v2

More data (the win), modern architecture, BPE — and the regularization round
that regressed and was rejected. The full story, round by round, is the report
[Can a big model improve a small one?](../../research-docs/reports/improve-a-small-model.md).

## How v2 became v3

The architecture didn't change (v2 already had RoPE + RMSNorm + bias-free). v3
changes **data, tokenizer, and precision**:

- **A 1024-vocab byte-level BPE trained on the corpus itself**, replacing v2's
  50k-vocab GPT-2 BPE. The Shakespeare domain never uses most of GPT-2's
  vocabulary; a small corpus-trained vocab drops the embedding table from ~19.3M
  to ~0.4M parameters, taking the model from ~29.9M to **~11.0M — about 1/3 the
  size**.
- **An enlarged corpus** — Shakespeare's Complete Works plus public-domain
  contemporary drama (Marlowe, Jonson, Kyd, Webster, Dekker). More data
  eliminated the overfit that defined v2's rounds (val loss now falls
  monotonically). The held-out `test.txt` is unchanged, so BPC stays comparable.
- **float32 training**, which removed an MPS float16 large-vocab logit overflow
  and let every vocabulary train cleanly at `lr=1e-3`.

Result: **BPC 1.919 → 1.831 at ~1/3 the params.** v3 also matches-or-beats a
fresh float32 GPT-2-vocab control (1.843, 29.9M), though that particular edge
(−0.012) is within single-seed noise — the clean wins are the parameter
efficiency and beating the prior champion. Multi-seed replication is the next
step. See the [v3 model card](../../research-docs/model-cards/shakespeare-nanogpt-3.md).

## Rebuild a version

Weights are gitignored; regenerate them from the committed code. Each version's
frozen folder runs **in place** with no arguments — the commands, the folder
layout, and how `models/` relates to the living `core/` engine are in
[`models/README.md`](models/README.md). To see the exact repo state that
shipped a version:

```bash
git checkout shakespeare-nanogpt-2   # the project as v2
git checkout main                    # back to latest
```

## New versions

A research round that finds a real improvement becomes v4 (and so on): a new
frozen `models/shakespeare-nanogpt-N/` folder, a git tag, a scored leaderboard
row, a registry entry, and a model card — the checklist is
[`docs/releasing.md`](../../docs/releasing.md). The clearest next direction is
**multi-seed replication**: v3's win over the fresh float32 control (and the
`bpe1k`-vs-`bpe4k` gap) is within single-seed noise and needs seed-replication to
resolve.

_(A Hugging Face release of these versions is planned but not yet done.)_
