---
type: experiment
number: 5
produced: "→ daydream-chess-nanogpt-1, -micro-1, -grand-1"
title: "Can a chess model's illegal moves be the point?"
date: 2026-07-02T06:22:19-04:00
series: daydream
researcher: claude-sonnet-5
models: [daydream-chess-nanogpt-1, daydream-chess-nanogpt-micro-1, daydream-chess-nanogpt-grand-1]
summary: "A three-tier chess-move GPT family (5x5, 8x8, and a custom 12x10 board) built around a single inversion: illegal moves are rendered as dim near-misses instead of being masked away by the sampler. All three tiers land in a tight band of legal-move rate (35-39% on a raw, unresampled first try) despite very different board sizes, vocabularies, and corpus sources -- and two separate facts in the original design plan turned out to be wrong when checked against the live engine instead of trusted from web research."
status: published
---
[← all experiments](README.md) · **Experiment 05** · Runs regular-r1, micro-r1, grand-r1 · `→ daydream-chess-nanogpt-1, -micro-1, -grand-1` · July 2026

# Can a chess model's illegal moves be the point?

The fifth research round in the studio, and the first in a new faculty:
[`daydream`](../../projects/daydream/README.md) isn't a text-generation
project like shakespeare, gatsby, or kenosha-kid — it's the studio's first
**sampler/prober** project, where the interesting behavior is what happens
to a model's *incorrect* output, not its generation quality.

<div class="takeaways">
<p class="takeaways-label">Key takeaways</p>
<ul>
<li>Three independently trained chess-move GPTs — Micro (5×5 Gardner minichess, 0.79M params), Regular (8×8 standard, 2.66M params), Grand (12×10 custom variant, 4.73M params) — built around one inversion: illegal moves are <strong>rendered as dim near-misses</strong>, not masked away by the sampler.</li>
<li>All three land in a <strong>tight band of legal-move rate</strong> on a raw, unresampled first try — 35.3% (Regular), 39.2% (Micro), 36.7% (Grand) — despite wildly different board sizes, vocabularies, and corpus sources. Legality-learning difficulty didn't scale sharply with board complexity in this build.</li>
<li>Two facts in the original design plan were <strong>wrong when checked against the live engine</strong> instead of trusted from a web search: real Grand Chess has one Chancellor and one Archbishop per side (not two), and the installed Fairy-Stockfish caps board ranks at 10 even though files go to 12 — so Grand shipped as 12×10, not 12×12.</li>
<li>The release gate for this series is <strong>not win rate</strong>. It's two automated checks — clean game completion and legal-move rate — deliberately decoupled from chess strength, which was never the point.</li>
</ul>
</div>

## The inversion

Most chess-model work treats illegal output as failure: mask it, reject
and resample it, penalize it during training. Daydream inverts that
framing entirely. A candidate move from the model is either legal — it
snaps into focus and becomes the actual move played — or illegal, a
rejected dream that the harness keeps rather than discards. The sampler's
resample-until-legal loop *is* the artwork's mechanism, not a bug-fix
layered on top of it.

That reframing is what makes this a genuinely different kind of project
for the studio: shakespeare, gatsby, and kenosha-kid are all measured on
how well they generate; daydream is measured on the *shape of its
failure*.

## Three boards, three models, one mechanism

| Tier | Board | Params | Corpus | Vocab |
|---|---|---|---|---|
| Micro | 5×5 (Gardner minichess) | 0.79M | 4,135 Fairy-Stockfish self-play games | 15 chars |
| Regular | 8×8 standard | 2.66M | 15,000 Lichess games, ~1400–1800 Elo | 21 chars |
| Grand | 12 files × 10 ranks, custom | 4.73M | 2,101 Fairy-Stockfish self-play games | 27 chars |

Each tier is a fully independent corpus, tokenizer, and trained model — UCI
square names depend on board dimensions, so nothing is shareable across
tiers. Micro uses Gardner minichess's real, balance-tested arrangement
directly. Grand extends real Grand Chess (10×10) to 12 files by mirroring a
second Chancellor and Archbishop pair onto the board, keeping non-pawn
piece density roughly proportional to the wider board — the same logic
historical variants like Capablanca Chess used when a plain 16-piece army
made a bigger board too sparse and slow.

## What "verified" means here

Release for each tier is gated on two automated checks, run by a shared
`harness.py` that plays the checkpoint against a skill-limited
Fairy-Stockfish opponent, resampling the model's raw output on illegal
moves (and forcing a random legal move if a resample cap is hit, so a game
never gets stuck):

| Tier | Clean completion | Legal-move rate (first try) |
|---|---|---|
| Regular | 30/30 (100%) | 258/731 (35.3%) |
| Micro | 30/30 (100%) | 121/309 (39.2%) |
| Grand | 30/30 (100%) | 230/627 (36.7%) |

Win rate against the opponent is deliberately **not** part of this gate —
this project was never about playing strength. Legal-move rate is a
legality-learning signal: roughly a third of the model's raw samples, with
zero rejection sampling applied, land on a real legal move in the actual
current position. The rest are the dream.

### The surprising consistency

Given how different the three boards are — 25 squares vs. 64 vs. 120, 6
vs. 16 vs. 24 non-pawn pieces per side, corpora ranging from 2,101 to
15,000 games — the legal-move rates land in a strikingly tight band (35.3%
to 39.2%). This wasn't designed for; it just happened. One reading: the
difficulty of "learn this board's local movement grammar from a few
thousand games" doesn't scale sharply with board size in this range, at
least not at these small model scales. Another reading: it's a coincidence
of this particular set of training-run lengths and model sizes, and a
different set of hyperparameters per tier could easily separate the three.
Worth another round to find out which.

## Two corrections, found by asking the engine instead of the internet

Daydream's design plan (written before any code existed) leaned on a web
search to spec Grand's board — and two of those facts were wrong.

**Wrong claim 1**: real Grand Chess has two Chancellors and two Archbishops
per side. **Actual**: querying the live Fairy-Stockfish engine
(`setoption name UCI_Variant value grand` + `d`) shows the real base
variant has exactly **one** of each, sitting off-center next to the king —
not the clean, symmetric layout the search summary implied.

**Wrong claim 2**: Fairy-Stockfish supports boards up to 36×36, so a 12×12
Grand was buildable. **Actual**: the installed build's `Rank` option type
caps at 10 even though `File` goes to 12 — confirmed the hard way, when
`stockfish check` rejected the first 12×12 config outright.

Both were corrected by querying the actual running binary rather than
trusting either the original web research or the design document that
inherited it. Grand shipped as 12 files × 10 ranks, with a second
Chancellor/Archbishop pair added deliberately (not copied from a
misremembered base) to keep the board's piece density proportional at the
wider size. The lesson generalizes past this one project: for any claim
about a live tool's actual behavior or limits, check the tool, not a
summary of documentation about the tool.

## Limitations

- **None of the three tiers were evaluated for chess strength**, on
  purpose — that was never this project's gate.
- **Grand's corpus is the smallest of the three** (2,101 games) — self-play
  on the larger, slower board took longer to generate within this build's
  time budget than Micro's or Regular's corpora did.
- **Legal-move rate is a first-try, single-config snapshot** — sampled at
  one temperature and no soft-cap tuning. Daydream's design treats logit
  soft-capping as an aesthetic "dreaminess" knob still to be explored;
  none of these three checkpoints have had that knob swept yet.
- **The tight legal-move-rate band across tiers is observational, not
  causally established** — see "the surprising consistency" above.

## How to reproduce

Each tier's frozen release folder rebuilds independently and in place:

```bash
cd projects/daydream/models/daydream-chess-nanogpt-1        # Regular
cd projects/daydream/models/daydream-chess-nanogpt-micro-1  # Micro
cd projects/daydream/models/daydream-chess-nanogpt-grand-1  # Grand

python prepare.py && python train.py config.py
python harness.py --games 30
```

Requires Fairy-Stockfish on `PATH` (`brew install fairy-stockfish`) — see
[ADR-0021](../../docs/adr/0021-daydream-fairy-stockfish-dependency.md) and
[ADR-0022](../../docs/adr/0022-daydream-three-tier-sampler-prober-shape.md)
for the full architectural rationale.

## Credits

- The shared `core` engine (modern nanoGPT lineage — RoPE, RMSNorm, bias-free).
- [Fairy-Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish) — self-play corpus generation and the legality-check primitive shared by all three tiers.
- The [Lichess open database](https://database.lichess.org/) — Regular's corpus source.
- Set up and trained with Claude ([Claude Code](https://claude.com/claude-code)).
