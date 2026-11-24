# lucky

Two small GPTs trained on every Maryland Pick 3 draw and every Powerball draw
under the current rules, built to show what "no signal" looks like on a
training curve.

Lottery draws are independent random events. A model trained on decades of
them can learn the format of a draw and nothing about the next one. That
makes this a null experiment with an unusual property: the best possible
loss is known before training starts, from the rules of the game alone.

| | `lucky-nanogpt-1` (Lucky) | `lucky-nanogpt-power-1` (Lucky Power) |
|---|---|---|
| Game | Maryland Pick 3 | Powerball |
| Corpus | 28,628 draws: evening since 29 Jul 1976, midday since 1 May 1995 | 1,436 draws under the 69/26 matrix, 7 Oct 2015 to 21 Nov 2026 |
| Possible outcomes | 1,000 | 292,201,338 |
| Floor | log₂ 1,000 = 9.966 bits/draw | log₂ 292,201,338 = 28.122 bits/draw |
| Rules to learn | three digits, repeats allowed | whites 1–69, red 1–26, no repeated white |

Daydream is one game on three board sizes. Lucky is one null on two ticket
sizes: a small flat game, and a big game with rules to learn.

## How it works

**One token per number.** A Pick 3 draw is `d d d \n`, 4 tokens over an
11-token vocabulary. A Powerball draw is `w w w w w | r \n`, 8 tokens over a
71-token vocabulary (`1`–`69` shared by whites and red, `|`, newline). The
loss per draw then reads directly in bits against the floor.

**History, with a control.** Each game is trained twice on the same targets:

- **B, the history version** reads the last 8 real draws and predicts the
  next one. It ships.
- **A, the no-history control** reads nothing and predicts one draw at a
  time. It stays in the project, unreleased.

If the past predicted the future, B's held-out loss would come in under A's.
Examples are cut at draw boundaries ("8 draws → next draw"), the loss covers
only the final draw, and `block_size` is `(8 + 1) × tokens per draw`: 36 for
Pick 3, 72 for Powerball. The control's block holds one draw.

**Whites are shuffled.** Published Powerball results are sorted. A model
trained on sorted draws learns order statistics, so the loader writes the
five whites in a fresh random order every epoch, and every white slot means
what it means in the drum: any unused number from 1 to 69. The eval sums the
model's probability over all 120 orderings of a held-out draw's whites, so
the reported number compares to the 28.12-bit set floor.

**The model picks numbers; the harness makes the ticket.** `harness.py` asks
for exactly five whites, writes the separator, asks for one red, and sorts
the whites. The numbers are never masked. Sampling is temperature 1 from a
seed; an attempt with an out-of-range number or a repeated white is a
reject, and the ticket is the first valid attempt (attempt *n* uses seed +
*n*). Rejects are printed, the way Daydream renders its near-misses.

**The tape.** The prompt is the last 8 real draws, frozen at the end of the
corpus. Picking several draws ahead rolls forward: each pick joins the tape
for the next.

## Pipeline

```
data/fetch.py        two sources per game -> data/raw/ (gitignored)
data/crosscheck.py   compare them -> data/<game>/draws.csv + data/provenance.json
precheck.py          chi-square tests on the draws -> research/precheck.json
data/prepare.py      draws.csv -> data/<game>/tokenized/{draws.bin, meta.pkl}
train.py             config/<run>.py -> runs/<run>/{ckpt.pt, ckpt_final.pt, log.jsonl}
evaluate.py          held-out bits/draw vs the floor, the A − B gap -> research/eval-<game>.json
harness.py           pick a ticket; raw valid-ticket rate; memorization check
```

Run everything from the **repo root** via `uv run`:

```bash
uv run python projects/lucky/data/fetch.py          # ~100 min: the Maryland site asks for a 10 s crawl delay
uv run python projects/lucky/data/crosscheck.py
uv run python projects/lucky/precheck.py
uv run python projects/lucky/data/prepare.py --game pick3
uv run python projects/lucky/data/prepare.py --game powerball
for run in lucky_control lucky_history power_control power_history; do
  uv run python projects/lucky/train.py projects/lucky/config/$run.py
done
uv run python projects/lucky/evaluate.py --game pick3
uv run python projects/lucky/evaluate.py --game powerball
uv run python projects/lucky/harness.py pick --ckpt projects/lucky/runs/power-history
```

The draws are committed (`data/pick3/draws.csv`, `data/powerball/draws.csv`),
so everything after `crosscheck.py` runs without the network. The split is by
time: the oldest 80% of draws train, the next 10% pick the stopping step, and
the most recent 10% are the held-out test every reported number comes from.

lucky carries its own `train.py`. The shared loop in `core/` cuts examples at
random token offsets; this project needs them cut at draw boundaries, with
the whites reshuffled every epoch. The model and the checkpoint shape are
still the shared engine's.

## The data

Draw machines made this corpus, and no model wrote any of it.
[`data/provenance.json`](data/provenance.json) records every source URL, the
fetch date, the draw counts, and every draw the two sources disagree on.

| Game | Primary | Second | Draws | Agree | Differ | Primary only | Second only |
|---|---|---|---|---|---|---|---|
| Pick 3 | Maryland Lottery, winning-numbers search | LotteryCorner yearly pages | 28,628 | 28,603 | 18 | 7 | 73 |
| Powerball | New York open data | Texas Lottery file | 1,436 | 1,436 | 0 | 0 | 1 |

The corpus is the primary source, draw for draw. Where the two disagree the
official value stands, and a draw only the second source lists is left out:
the official search answers "no drawings" for those dates (23 of the 73 are
Sunday evenings in the first half of 1998). Nothing is repaired by hand.
Powerball whites are compared as sets, since New York sorts them and Texas
keeps draw order; the one Texas-only draw is 23 Nov 2026, which New York had
not posted at fetch time.

One trap for anyone re-fetching: the Maryland search drops every evening-only
day from a range that also holds midday draws. `fetch.py` makes a second,
one-day-per-request pass to get them back
([`research/log.md`](research/log.md)).

**The pre-check.** Before any training, `precheck.py` ran 46 chi-square tests
on the draws: Pick 3 digit frequency by position, by era and by decade, all
1,000 combinations, lag-1 dependence between consecutive draws, and
Powerball's red and white frequencies. None rejects uniformity at the
Bonferroni threshold; 2 fall below 0.05 uncorrected, against 2.3 expected by
chance ([`research/precheck.json`](research/precheck.json)). The null is
clean in every era tested.

## Versions

Released `lucky-nanogpt-*` versions. Weights are never committed; everything
needed to rebuild them is.

| Version | Folder | Game | What it is | Headline metrics |
|---|---|---|---|---|
| `lucky-nanogpt-1` | [`models/lucky-nanogpt-1/`](models/lucky-nanogpt-1/) | Maryland Pick 3 | history version, early-stopped at step 1100 | 9.9709 bits/draw held out against a 9.9658 floor; 99.99% valid |
| `lucky-nanogpt-power-1` | [`models/lucky-nanogpt-power-1/`](models/lucky-nanogpt-power-1/) | Powerball | history version, early-stopped at step 300 | 28.687 bits/draw held out against a 28.122 floor; 80.2% valid |

Each rebuilds in place from its frozen folder:

```bash
cd models/lucky-nanogpt-power-1
python prepare.py && python train.py && python eval.py
python harness.py pick
```

Model cards:
[Lucky](../../research-docs/model-cards/lucky-nanogpt-1.md) ·
[Lucky Power](../../research-docs/model-cards/lucky-nanogpt-power-1.md).
Experiment write-up:
[What does a model learn from fifty years of lottery draws?](../../research-docs/reports/fifty-years-of-lottery-draws.md)

## Leaderboard

Per-run scoreboard. The journal (why) is in [`research/log.md`](research/log.md);
the predictions, committed before any run, are in
[`research/predictions.md`](research/predictions.md).

The score is held-out bits per draw on the test split (the most recent 10% of
draws) against the floor. Lower is better and the floor is the limit.
Powerball is scored at set level. All four runs share one body (4 layers, 4
heads, 128 wide, no dropout, 0.80M parameters), 3,000 steps, seed 1337, CPU.

| game | run | reads | stop step | held-out bits/draw | above floor | at step 3000 | valid tickets (raw) | verdict |
|---|---|---|---|---|---|---|---|---|
| Pick 3 (floor 9.9658) | lucky-history | last 8 draws | 1100 | 9.9709 | +0.0051 | 9.9844 | 99,994/100,000 | **released → lucky-nanogpt-1** |
| Pick 3 | lucky-control | nothing | 1700 | 9.9707 | +0.0049 | 9.9750 | 99,994/100,000 | control, unreleased |
| Powerball (floor 28.1224) | power-history | last 8 draws | 300 | 28.6868 | +0.5644 | 36.2509 | 802,007/1,000,000 | **released → lucky-nanogpt-power-1** |
| Powerball | power-control | nothing | 400 | 28.5048 | +0.3824 | 31.7887 | 830,183/1,000,000 | control, unreleased |

**The A − B gap** (control minus history, paired per held-out draw, 95%
bootstrap interval; positive would mean history helped):

| game | held-out draws | A − B, bits/draw | interval |
|---|---|---|---|
| Pick 3 | 2,862 | −0.0002 | [−0.0052, +0.0046] |
| Powerball | 143 | −0.182 | [−0.243, −0.120] |

**Memorization** (Powerball, valid samples that match a past draw number for
number, against the count expected by chance):

| checkpoint | valid samples | full-ticket matches | expected by chance |
|---|---|---|---|
| power-history, step 300 (released) | 802,007 | 1 | 3.9 |
| power-control, step 400 | 830,183 | 1 | 4.1 |
| power-history, step 3000 | 642,206 | 8 | 3.2 |
| power-control, step 3000 | 848,231 | 804 | 4.2 |

**Against the predictions.** Lucky lands inside the registered 1% band; Lucky
Power does not (2.0% above its floor, 1.4% for its control). The A − B
interval contains zero for Pick 3 and excludes it for Powerball, where the
history version is the worse one. Lucky Power's held-out loss drifts up with
continued training, as predicted.

Evidence: [`research/eval-pick3.json`](research/eval-pick3.json),
[`research/eval-powerball.json`](research/eval-powerball.json),
`research/rate-*.json`, and the run logs in `research/runs/`.

## Credits

See each model card in `research-docs/model-cards/` for researcher
attribution ([ADR-0013](../../docs/adr/0013-attribution-of-the-ai-researcher.md)).
The corpus credits no generator: draw machines are described, not credited
([ADR-0037](../../docs/adr/0037-crediting-the-corpus-generators.md)).
