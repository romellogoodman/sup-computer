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
---

# Model Card — `daydream-chess-nanogpt-1` (v1, Regular)

A chess-move GPT that doesn't play chess so much as *hallucinate* it. Legal
moves snap into focus; illegal moves render as dim near-misses instead of
being masked or rejection-sampled away — the sampler is the aesthetic
decision, not a correctness filter. First release in the
[`daydream`](../../projects/daydream/README.md) series, and the standard
8×8 board tier — "Regular," the implicit default among Micro (5×5) and
Grand (12 files × 10 ranks).

> **Render illegal moves, don't discard them.** Most chess-model work treats
> illegal output as failure to be masked or rejection-sampled away. Daydream
> inverts that: a candidate move is either legal (it snaps into focus and
> becomes the game's actual move) or illegal (a rejected dream, kept rather
> than thrown away). The sampler's resample-until-legal loop is the artwork's
> mechanism, not a bug-fix on top of it.

## Model details

| | |
|---|---|
| **Version / git tag** | `daydream-chess-nanogpt-1` (research run `regular-r1`) |
| **Architecture** | modern char-level (RoPE, RMSNorm, bias-free) on the shared `core` engine — no vendored base engine |
| **Size** | 6 layers · 6 heads · 192 embedding dim · 256 context · dropout 0.1 · ~2.66M params |
| **Tokenizer** | character-level, 21-char vocabulary over UCI move text (files a–h, ranks 1–8, promotion letters q/r/b/n, space, newline) — `meta.pkl` is the contract ([ADR-0012](../../docs/adr/0012-pluggable-tokenization.md)) |
| **Checkpoint** | `projects/daydream/models/daydream-chess-nanogpt-1/` (weights not committed — regenerates deterministically below) |
| **Built on** | the monorepo's shared [`core`](../../core/) engine |
| **Developed with** | Claude ([Claude Code](https://claude.com/claude-code)) |
| **License** | MIT |

## Intended use

An exhibit exploring what a chess-move model looks like when illegal output
is rendered rather than hidden. Not intended to play strong chess — legality
and interestingness of the near-misses are the point, not playing strength.
Pairs with `harness.py`, which plays the model against Fairy-Stockfish,
resampling on illegal moves until one lands (or forcing a random legal move
once a resample cap is hit, so games always complete).

**Out of scope.** Not a chess engine and not evaluated as one — no win-rate
claims are made or should be inferred. Not a general-purpose language model;
its entire vocabulary is UCI chess-move syntax.

## Training data

15,000 games from the [Lichess open database](https://database.lichess.org/)
(January 2018 monthly dump), filtered to games where both players are
rated 1400–1800 Elo — deliberately mid-band: strong enough for coherent
positional shape, loose enough to produce the near-miss texture the dream
mechanic needs. Elite/engine games were explicitly rejected as a corpus
source elsewhere in this project's design — too-clean play kills the texture.
Streamed and filtered directly from the compressed dump (zstd decode + Elo
filter in one pass via `python-chess`) without ever storing the full ~5.5GB
file. Converted from SAN to UCI move notation. Corpus is downloaded, not
committed (regenerates via `fetch_filtered.py`); only derived artifacts
(`*.bin`, `*.pkl`, `*.pt`) are gitignored.

## Training procedure

- **Optimizer:** AdamW, LR 3e-4 with cosine decay to 3e-5, 100 warmup iters, β₂ 0.99, batch size 64.
- **Run:** 3,000 iterations, best val loss 0.858 (`always_save_checkpoint`).
- **Hardware:** Apple Silicon Mac (MPS / Metal backend), `torch.compile` disabled.

## Evaluation

Verification runs `harness.py`: the model plays full games against a
skill-limited Fairy-Stockfish opponent, resampling on illegal moves. The two
automated gate metrics — nothing else is an automated gate, per this
project's design:

| Metric | Result (30 games) |
|---|---|
| **Clean completion rate** | 30/30 (100%) — every game reached a natural end (checkmate/stalemate/ply cap) with no pipeline crash |
| **Legal-move rate (first try)** | 258/731 (35.3%) — over a third of the model's move proposals are legal in the current position on the very first sample, with no resampling |

### What 35.3% means here

This is not a chess-strength number — win rate against the opponent is
explicitly not part of this project's release gate. It's a legality-learning
number: roughly one in three raw samples from the model, with no rejection
sampling applied, land on a real legal move in the actual current position.
The other two-thirds are the dream — syntactically valid UCI strings
(`e2e4`-shaped) that are illegal here, rendered rather than discarded by the
harness's resample loop.

## Limitations

- **Not evaluated for playing strength**, deliberately — this project's gate
  is legality and completion, not win rate.
- **Legality is learned, not guaranteed.** Even the harness's resample loop
  has a cap; beyond it, a uniformly random legal move is forced so the game
  still completes. That fallback move is not the model's "dream" — it's the
  harness's safety valve.
- **UCI-only vocabulary.** No SAN, no natural language, no commentary — 21
  characters, chess moves and nothing else.
- **No weights in the tree** ([ADR-0002](../../docs/adr/0002-no-weights-in-tree.md)).

## How to reproduce

```bash
cd projects/daydream/models/daydream-chess-nanogpt-1
python fetch_filtered.py      # -> games.txt (network; Lichess Jan 2018 dump)
python prepare.py             # -> regular/{train,val}.bin + meta.pkl
python train.py config.py     # -> ./ckpt.pt (3000 iters, val ~0.86)
python harness.py --games 30  # verification: legal-move rate, clean-completion rate
```

Experiment write-up: [Can a chess model's illegal moves be the point?](../reports/illegal-moves-are-the-point.md)

Requires Fairy-Stockfish on `PATH` (`brew install fairy-stockfish`) for
`harness.py` — see
[ADR-0021](../../docs/adr/0021-daydream-fairy-stockfish-dependency.md).

## Citation / credits

- The shared `core` engine (modern nanoGPT lineage — RoPE, RMSNorm, bias-free).
- [Fairy-Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish) — legality arbiter and self-play engine for the sibling Micro/Grand tiers.
- The [Lichess open database](https://database.lichess.org/) — corpus source.
- Set up and trained with Claude ([Claude Code](https://claude.com/claude-code)).
