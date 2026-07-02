# Models

A registry of released `daydream-chess-nanogpt-*` versions — spec, git tag,
and the commands to rebuild each. Weights are never committed; everything
needed to reproduce them is. Three independent tiers, not one model
generalized across board sizes — see the project
[`README.md`](README.md).

| Tier | Folder | Board | What it is | Headline metrics |
|---|---|---|---|---|
| Regular | [`models/daydream-chess-nanogpt-1/`](models/daydream-chess-nanogpt-1/) | 8×8 | trained on 15k Lichess games, ~1400–1800 Elo | 100% clean completion, 35.3% legal-move rate (first try) |
| Micro | [`models/daydream-chess-nanogpt-micro-1/`](models/daydream-chess-nanogpt-micro-1/) | 5×5 (Gardner) | trained on 4,135 Fairy-Stockfish self-play games | 100% clean completion, 39.2% legal-move rate (first try) |
| Grand | [`models/daydream-chess-nanogpt-grand-1/`](models/daydream-chess-nanogpt-grand-1/) | 12 files × 10 ranks | trained on 2,101 Fairy-Stockfish self-play games | 100% clean completion, 36.7% legal-move rate (first try) |

The quality metric for this project is **not** val loss — it's the two-part
verification gate run by `harness.py`: **clean completion rate** (games
finish without crashing) and **legal-move rate** (fraction of the model's
raw samples that are legal in the current position, no resampling). Win
rate against an opponent and dream-rendering quality are explicitly *not*
automated gates — see each model card's Evaluation section.

## `daydream-chess-nanogpt-1` (Regular, run `regular-r1`)

A ~2.66M-parameter char-level GPT trained on real human chess games,
mid-rating band. See the
[model card](../../research-docs/model-cards/daydream-chess-nanogpt-1.md)
for the full write-up.

### Rebuild

```bash
cd models/daydream-chess-nanogpt-1
python fetch_filtered.py && python prepare.py && python train.py config.py
python harness.py --games 30
```

## `daydream-chess-nanogpt-micro-1` (Micro, run `micro-r1`)

A ~0.79M-parameter char-level GPT trained on Fairy-Stockfish self-play under
Gardner minichess (5×5) — no human corpus exists for this board size. See
the [model card](../../research-docs/model-cards/daydream-chess-nanogpt-micro-1.md).

### Rebuild

```bash
cd models/daydream-chess-nanogpt-micro-1
python prepare.py && python train.py config.py
python harness.py --games 30
```

## `daydream-chess-nanogpt-grand-1` (Grand, run `grand-r1`)

A ~4.73M-parameter char-level GPT trained on Fairy-Stockfish self-play under
a custom 12-file × 10-rank variant extending real Grand Chess with a second
Chancellor and Archbishop per side. See the
[model card](../../research-docs/model-cards/daydream-chess-nanogpt-grand-1.md).

### Rebuild

```bash
cd models/daydream-chess-nanogpt-grand-1
python prepare.py && python train.py config.py
python harness.py --games 30
```
