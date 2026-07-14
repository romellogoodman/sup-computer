# daydream

A chess-move GPT that doesn't play chess so much as *hallucinate* it. Legal
moves snap into focus; illegal moves render as dim near-misses instead of
being masked or rejection-sampled away — the sampler is the aesthetic
decision, not a correctness filter.

Daydream is a **family of three models**, one per board size, named after
the model-tier naming pattern (Haiku/Sonnet/Opus) but keyed to board size
instead of parameter count:

| Tier | Board | Pieces per side | Corpus |
|---|---|---|---|
| **Micro** | 5×5 (Gardner minichess) | K, Q, R, B, N (one each), 5 pawns | Synthetic — Fairy-Stockfish self-play |
| **Regular** | 8×8 standard | Standard 16 | Real — Lichess games, ~1400–1800 Elo |
| **Grand** | 12 files × 10 ranks | K, Q, 2R, 2B, 2N, 2 Chancellor, 2 Archbishop, 12 pawns | Synthetic — Fairy-Stockfish self-play |

Each tier is a fully separate corpus, tokenizer, and trained model — not one
model generalized across board sizes. Switching models in the player is
meant to visibly shrink or grow the board: the constraint (this model only
knows a 5×5 board because that's all it was trained on) is made visible
instead of hidden, the opposite of "model-v1 / model-v2 / model-v3" naming.

## How it works

Moves are UCI (`e2e4`), not SAN (`Nf3`) — a UCI string is well-formed even
when it's illegal in the current position, which is exactly the "syntactically
valid, semantically impossible" texture the dream mechanic needs. Tokenization
is character-level over each tier's own move vocabulary (file letters, rank
digits, promotion-suffix letters), the same `meta.pkl` contract every other
project in this monorepo uses (see
[ADR-0012](../../docs/adr/0012-pluggable-tokenization.md)) — no core changes
were needed to support chess.

Logit soft-capping is treated as a tunable *dreaminess* knob, not just a
training stabilizer: turning it up or down trades off how sharply legal
moves snap into focus versus how much illegal near-misses bleed through.

## Pipeline

```
Regular:  data/regular/fetch_filtered.py (stream+filter a Lichess dump)  -> data/regular/games.txt
Micro:    data/selfplay.py --variant gardner                             -> data/micro/games.txt
Grand:    data/selfplay.py --variant grand12 --variants-ini engine/variants.ini
                                                                         -> data/grand/games.txt

-> data/prepare.py --tier <micro|regular|grand> -> train.bin/val.bin/meta.pkl (per tier)
-> core/nanogpt_core/train.py -> runs/<tier>/ckpt.pt
-> harness.py (plays the checkpoint against Fairy-Stockfish, resamples on
   illegal moves, verifies legal-move rate + clean game completion)
```

`selfplay.py` and `prepare.py` are shared across tiers — one script each,
parameterized, not a copy per tier.

Run everything from the **repo root** via `uv run`.

## External dependency: Fairy-Stockfish

This is the only project in the monorepo with a non-Python, non-pip engine
dependency. Install via Homebrew:

```bash
brew install fairy-stockfish
```

It's used two ways: (1) self-play corpus generation for Micro/Grand under
`engine/variants.ini`'s custom Grand config (Micro uses Fairy-Stockfish's
built-in `gardner` variant directly, no custom config needed), and (2) as
the single-position legality arbiter in `harness.py` — a candidate move is
legal if and only if Fairy-Stockfish's own move generator, given the current
position, includes it. See
[ADR-0021](../../docs/adr/0021-daydream-fairy-stockfish-dependency.md).

## No distillation

A Tier-2-teacher/Tier-1-student distillation layer was explored during
design and explicitly abandoned. Each tier is one training run, nothing
downstream of the frozen model.

## Parked: Really Bad Chess

Randomized starting armies (standard board/rules) was the idea that
originally motivated this project — it kills opening-book memorization so
the model dreams from move one. Set aside as a separate future probe (a
Regime 2 intervention on a frozen model, not a new training run), not part
of this three-tier build.

## Versions

A registry of released `daydream-chess-nanogpt-*` versions — spec, git tag,
and the commands to rebuild each. Weights are never committed; everything
needed to reproduce them is. Three independent tiers, not one model
generalized across board sizes (see above).

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

Each tier rebuilds in place from its frozen folder, e.g.:

```bash
cd models/daydream-chess-nanogpt-1
python fetch_filtered.py && python prepare.py && python train.py config.py
python harness.py --games 30
```

(Micro and Grand skip `fetch_filtered.py` — their corpora come from
`selfplay.py`, vendored in each folder.) Model cards:
[Regular](../../research-docs/model-cards/daydream-chess-nanogpt-1.md) ·
[Micro](../../research-docs/model-cards/daydream-chess-nanogpt-micro-1.md) ·
[Grand](../../research-docs/model-cards/daydream-chess-nanogpt-grand-1.md).

## Leaderboard

Per-run scoreboard. The journal (why) is in [`research/log.md`](research/log.md).
"Score" here is the two-part verification gate — clean completion + legal-move
rate — not val loss. Win rate against the harness's Fairy-Stockfish opponent
is explicitly not part of the gate.

| tier | run | corpus | model (L/H/E, block) | iters | val loss | clean completion | legal-move rate (1st try) | verdict |
|---|---|---|---|---|---|---|---|---|
| Regular | regular-r1 | 15,000 Lichess games, ~1400-1800 Elo | 6/6/192, 256 | 3000 | 0.858 | 30/30 (100%) | 258/731 (35.3%) | **champion → daydream-chess-nanogpt-1** |
| Micro | micro-r1 | 4,135 Fairy-Stockfish self-play (Gardner 5x5) | 4/4/128, 128 | 2500 | 0.718 | 30/30 (100%) | 121/309 (39.2%) | **champion → daydream-chess-nanogpt-micro-1** |
| Grand | grand-r1 | 2,101 Fairy-Stockfish self-play (12x10, Chancellor+Archbishop) | 6/8/256, 512 | 3000 | 1.053 | 30/30 (100%) | 230/627 (36.7%) | **champion → daydream-chess-nanogpt-grand-1** |

## Credits

See each model card in `research-docs/model-cards/` for researcher
attribution ([ADR-0013](../../docs/adr/0013-attribution-of-the-ai-researcher.md)).
