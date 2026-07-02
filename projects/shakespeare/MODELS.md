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

| | `shakespeare-nanogpt-1` (v1) | `shakespeare-nanogpt-2` (v2) |
|---|---|---|
| **What it is** | the original char-level baseline — data-starved on purpose | the first research experiment's winner: modern arch + BPE on the Complete Works |
| **Git tag** | `shakespeare-nanogpt-1` | `shakespeare-nanogpt-2` |
| **Frozen code** | [`models/shakespeare-nanogpt-1/`](models/shakespeare-nanogpt-1/) | [`models/shakespeare-nanogpt-2/`](models/shakespeare-nanogpt-2/) |
| **Model card** | [v1 card](../../research-docs/model-cards/shakespeare-nanogpt-1.md) | [v2 card](../../research-docs/model-cards/shakespeare-nanogpt-2.md) |
| **Held-out test BPC** | 2.395* | **1.919** |

\* v1's regime figure: the controlled data-starved baseline the experiment set
out to beat. (v1's own headline was its Tiny-Shakespeare val loss of **1.46** —
different tokenizers make raw losses incomparable, which is why the series
yardstick is BPC on the fixed `test.txt`.)

## How v1 became v2

More data (the win), modern architecture, BPE — and the regularization round
that regressed and was rejected. The full story, round by round, is the report
[Can a big model improve a small one?](../../research-docs/reports/improve-a-small-model.md).

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

A research round that finds a real improvement becomes v3 (and so on): a new
frozen `models/shakespeare-nanogpt-N/` folder, a git tag, a scored leaderboard
row, a registry entry, and a model card — the checklist is
[`docs/releasing.md`](../../docs/releasing.md). The clearest next direction is
**data**: Round 4 showed regularization cannot substitute for it.

_(A Hugging Face release of these versions is planned but not yet done.)_
