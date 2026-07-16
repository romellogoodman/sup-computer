---
license: mit
language:
  - en
library_name: nanogpt
pipeline_tag: text-generation
tags:
  - daydream
  - nanogpt
  - char-level
  - gpt
  - chess
  - uci
  - minichess
---

# Model Card — `daydream-chess-nanogpt-micro-1` (v1, Micro)

The smallest tier in the [`daydream`](../../projects/daydream/README.md)
family: a chess-move GPT trained on **Gardner minichess**, a real 5×5 chess
variant — one each of King/Queen/Rook/Bishop/Knight per side, five pawns.
Same mechanic as the rest of the series: legal moves snap into focus,
illegal moves render as dim near-misses instead of being discarded.

> **A smaller board means a smaller book to memorize.** The animating
> thesis behind the daydream series is that repetition (opening theory,
> memorized lines) is where a model is most "in focus" and least
> interesting. Micro tests the far end of that: with only 25 squares and 6
> non-pawn pieces per side, there's very little room for memorized
> structure at all — almost everything the model does here, it has to
> generalize from a comparatively tiny, self-play-only corpus.

## Model details

| | |
|---|---|
| **Version / git tag** | `daydream-chess-nanogpt-micro-1` (research run `micro-r1`) |
| **Architecture** | modern char-level (RoPE, RMSNorm, bias-free) on the shared `core` engine |
| **Size** | 4 layers · 4 heads · 128 embedding dim · 128 context · dropout 0.1 · ~0.79M params |
| **Tokenizer** | character-level, 15-char vocabulary over UCI move text on a 5×5 board (files a–e, ranks 1–5, promotion letters n/q/r, space, newline) |
| **Checkpoint** | `projects/daydream/models/daydream-chess-nanogpt-micro-1/` (weights not committed) |
| **Built on** | the monorepo's shared [`core`](../../core/) engine |
| **Developed with** | Claude ([Claude Code](https://claude.com/claude-code)) |
| **License** | MIT |

## Intended use

Same exhibit posture as Regular, scaled to the smallest board in the
series. Pairs with `harness.py` (this folder), which plays the model
against Fairy-Stockfish under the built-in `gardner` variant.

**Out of scope.** Not a chess engine, not evaluated for playing strength.
Vocabulary and board are Gardner-minichess-specific — moves here are
meaningless on Regular's or Grand's boards and vice versa (see
[ADR-0022](../../docs/adr/0022-daydream-three-tier-sampler-prober-shape.md)
on why tiers never share a vocabulary).

## Training data

No human corpus exists for 5×5 chess, so this tier is entirely synthetic:
4,135 self-play games between two Fairy-Stockfish instances under the
engine's built-in `gardner` variant — bounded-depth search, not
strength-reduced (see
[ADR-0021](../../docs/adr/0021-daydream-fairy-stockfish-dependency.md)).
Fixed-depth search alone is fully deterministic; the first attempt produced
identical games every time. The fix: randomized opening plies, sourcing
random legal openings from the engine's own `go perft 1` move list, plus a
repetition-window cutoff for games that fell into shuffling loops. Corpus
is vendored in-folder as `games.txt` — synthetic, seeded, code-owned,
committed, the same treatment as kenosha-kid's `raw.txt`.

## Training procedure

- **Optimizer:** AdamW, LR 3e-4 with cosine decay to 3e-5, 100 warmup iters, β₂ 0.99, batch size 64.
- **Run:** 2,500 iterations, best val loss 0.718.
- **Hardware:** Apple Silicon Mac (MPS / Metal backend), `torch.compile` disabled.

## Evaluation

| Metric | Result (30 games) |
|---|---|
| **Clean completion rate** | 30/30 (100%) |
| **Legal-move rate (first try)** | 121/309 (39.2%) |

Micro's legal-move rate (39.2%) is somewhat higher than Regular's (35.3%,
[`daydream-chess-nanogpt-1`](daydream-chess-nanogpt-1.md)). One reading: a
smaller board and smaller per-position legal-move count is an easier
legality-learning problem. But the two aren't a strict apples-to-apples
comparison — different corpora, different vocab sizes, different training
run lengths.

## Limitations

- **Not evaluated for playing strength**, deliberately.
- **Synthetic corpus only** — no human Gardner-minichess games exist to
  compare against; the training distribution is entirely a product of
  bounded-depth Fairy-Stockfish self-play plus randomized openings.
- **Legality is learned, not guaranteed** — same resample-then-force-random
  fallback as every tier in this series.
- **No weights in the tree** ([ADR-0002](../../docs/adr/0002-no-weights-in-tree.md)).

## How to reproduce

```bash
cd projects/daydream/models/daydream-chess-nanogpt-micro-1
python prepare.py             # -> micro/{train,val}.bin + meta.pkl
python train.py config.py     # -> ./ckpt.pt (2500 iters, val ~0.72)
python harness.py --games 30  # verification
```

Requires Fairy-Stockfish on `PATH` (`brew install fairy-stockfish`).

Experiment write-up: [Can a chess model's illegal moves be the point?](../reports/illegal-moves-are-the-point.md)

## Citation / credits

- The shared `core` engine (modern nanoGPT lineage — RoPE, RMSNorm, bias-free).
- [Fairy-Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish) — self-play corpus generator and legality arbiter, via its built-in `gardner` variant.
- Set up and trained with Claude ([Claude Code](https://claude.com/claude-code)).
