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
  - chess-variant
---

# Model Card — `daydream-chess-nanogpt-grand-1` (v1, Grand)

<div class="takeaways">
<p class="takeaways-label">Key takeaways</p>
<ul>
<li>A 4.73M-param char-level GPT trained on a custom 12-file × 10-rank chess variant with Chancellor and Archbishop pieces added — the largest, most complex board in the <a href="../../projects/daydream/README.md">daydream</a> family.</li>
<li>The board spec was <strong>corrected mid-build against the live engine</strong>, not trusted from research: real Grand Chess has one Chancellor and one Archbishop per side (not two, as an earlier web search claimed), and the installed Fairy-Stockfish caps board ranks at 10 even though files go to 12 — so this is 12×10, not 12×12.</li>
<li>100% clean completion, 36.7% legal-move rate on first try — in line with Regular's 35.3% and Micro's 39.2%, a <strong>consistent legality-learning signal</strong> across all three board sizes despite very different vocabularies and piece sets.</li>
<li>Promotion needed <strong>zero new tokenizer characters</strong>: Capablanca-style six-way promotion (Q/Chancellor/Archbishop/R/B/N) is fully covered by letters already in the 12-file alphabet (a–l) plus n/q/r, landing on a 27-character vocabulary.</li>
</ul>
</div>

The largest, most structurally novel tier in the
[`daydream`](../../projects/daydream/README.md) family: a chess-move GPT
trained on a custom variant extending real Grand Chess to 12 files × 10
ranks, with two Chancellor (rook+knight) and two Archbishop (bishop+knight)
pieces per side. Same mechanic as the rest of the series: legal moves snap
into focus, illegal moves render as dim near-misses instead of being
discarded.

> **A wider board needs denser pieces, not just more empty squares.**
> Historical large-board chess variants (Capablanca Chess, real Grand
> Chess) don't just spread the standard 16 pieces over more squares — they
> add compound pieces to keep tactical density proportional to the board.
> Grand extrapolates that logic one step further than its 10×10
> namesake, adding a second Chancellor and Archbishop pair to keep density
> proportional at 12 files.

## Model details

| | |
|---|---|
| **Version / git tag** | `daydream-chess-nanogpt-grand-1` (research run `grand-r1`) |
| **Architecture** | modern char-level (RoPE, RMSNorm, bias-free) on the shared `core` engine |
| **Size** | 6 layers · 8 heads · 256 embedding dim · 512 context · dropout 0.1 · ~4.73M params |
| **Tokenizer** | character-level, 27-char vocabulary over UCI move text on a 12×10 board (files a–l, ranks 1–10, promotion letters n/q/r — c/a/b already covered by file names) |
| **Checkpoint** | `projects/daydream/models/daydream-chess-nanogpt-grand-1/` (weights not committed) |
| **Built on** | the monorepo's shared [`core`](../../core/) engine |
| **Developed with** | Claude ([Claude Code](https://claude.com/claude-code)) |
| **License** | MIT |

## Intended use

Same exhibit posture as Regular and Micro, at the largest board in the
series. Pairs with `harness.py` (this folder), which plays the model
against Fairy-Stockfish under the vendored custom `grand12` variant.

**Out of scope.** Not a chess engine, not evaluated for playing strength.
Vocabulary and board are `grand12`-specific — Chancellor and Archbishop
moves and this board's square names are meaningless on Regular's or
Micro's boards and vice versa.

## Training data

No human corpus exists for this board, so it's entirely synthetic:
2,101 self-play games between two Fairy-Stockfish instances under the
project's custom `grand12` variant (vendored as `variants.ini` in this
folder), bounded-depth search with randomized opening plies for diversity.
Corpus vendored in-folder as `games.txt` (synthetic, seeded, code-owned —
committed).

### The board, exactly

Extends real Grand Chess (10×10) rather than inventing a new design from
scratch. The base variant, confirmed by querying the live engine rather
than trusted from documentation, has rooks alone in the back-rank corners,
a mirror-asymmetric second rank with one Chancellor and one Archbishop
sitting off-center next to the king, and pawns filling the entire third
rank. Grand's 12×10 extension makes the second rank fully mirror-symmetric
by adding a second Chancellor/Archbishop pair: **Knight, Bishop,
Chancellor, Archbishop, Queen, King, Archbishop, Chancellor, Bishop,
Knight** across files b–k (a and l stay empty, matching the base variant's
corners), with rooks at a1/l1 and a full pawn rank at rank 3. 24 non-pawn
pieces plus 12 pawns per side.

## Training procedure

- **Optimizer:** AdamW, LR 3e-4 with cosine decay to 3e-5, 100 warmup iters, β₂ 0.99, batch size 48.
- **Run:** 3,000 iterations, best val loss 1.053.
- **Hardware:** Apple Silicon Mac (MPS / Metal backend), `torch.compile` disabled.

## Evaluation

| Metric | Result (30 games) |
|---|---|
| **Clean completion rate** | 30/30 (100%) |
| **Legal-move rate (first try)** | 230/627 (36.7%) |

Consistent with the other two tiers (Regular 35.3%, Micro 39.2%): roughly
a third of raw, unresampled samples land legal regardless of board size or
vocabulary. One reading: legality-learning difficulty is fairly stable
across this project's board-size range rather than scaling sharply with
board complexity.

## Limitations

- **Not evaluated for playing strength**, deliberately.
- **Smallest corpus of the three tiers** (2,101 games vs. Micro's 4,135 and
  Regular's 15,000) — self-play on this larger, slower board took
  meaningfully longer per game to generate within this build's time budget.
- **Legality is learned, not guaranteed** — same resample-then-force-random
  fallback as every tier in this series.
- **No weights in the tree** ([ADR-0002](../../docs/adr/0002-no-weights-in-tree.md)).

## How to reproduce

```bash
cd projects/daydream/models/daydream-chess-nanogpt-grand-1
python prepare.py             # -> grand/{train,val}.bin + meta.pkl
python train.py config.py     # -> ./ckpt.pt (3000 iters, val ~1.05)
python harness.py --games 30  # verification
```

Requires Fairy-Stockfish on `PATH` (`brew install fairy-stockfish`) —
Grand needs the vendored `variants.ini`, unlike Micro which uses a
built-in variant. See
[ADR-0021](../../docs/adr/0021-daydream-fairy-stockfish-dependency.md).

Experiment write-up: [Can a chess model's illegal moves be the point?](../reports/illegal-moves-are-the-point.md)

## Citation / credits

- The shared `core` engine (modern nanoGPT lineage — RoPE, RMSNorm, bias-free).
- [Fairy-Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish) — self-play corpus generator and legality arbiter, extending its built-in `grand` variant.
- Set up and trained with Claude ([Claude Code](https://claude.com/claude-code)).
