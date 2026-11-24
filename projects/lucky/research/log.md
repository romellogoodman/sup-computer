# lucky — research log

The why behind the numbers in the README's Leaderboard. Newest entry last.

## 2026-11-23 — the draws

**Two sources per game.** Pick 3 comes from the Maryland Lottery's own
winning-numbers search (primary) and LotteryCorner's yearly pages (second).
Powerball comes from New York's open-data file (primary) and the Texas
Lottery's file (second). The design named powerball.com as the Powerball
cross-check; it has no bulk history, so a second official state file stands
in for it. Every disagreement is listed in `data/provenance.json`.

**The official Pick 3 search drops days.** The first pass asked for one year
per request and came back 632 draws short of the second source. The cause is
in the endpoint, not the archive: when a queried range holds any midday
draws, it omits every day that has an evening draw and no midday draw. The
1995 request returned nothing before 1 May (the first midday draw), and no
Sunday evening from 1995 to 2004 came back in any yearly request, though a
one-day request returns each of them. `data/fetch.py` now makes a second
pass: every date from 1995 on with no evening draw in the yearly pass is
requested alone. That is about 495 extra requests at the site's 10-second
crawl delay.

**Powerball agrees exactly.** All 1,436 draws from 2015-10-07 to 2026-11-21
match between New York and Texas as sets (New York sorts the whites, Texas
keeps draw order).

## 2026-11-23 — decisions the design left to the build

- **Tokens per draw.** Pick 3 is `d d d \n`, 4 tokens, so the history model's
  block is 36 as designed. Powerball is `w w w w w | r \n`, which is 8 tokens,
  not the 7 the design's arithmetic assumed, so the history block is 72, not 63. The design
  keeps both the separator and the newline in the training data; 8 is what
  that costs.
- **Three splits, not two.** The design holds out the most recent 10% and
  early-stops on it. Picking the stopping step on the same draws that get
  reported would let the reported number dip under the floor by selection.
  So: oldest 80% train, next 10% pick the stopping step, newest 10% are the
  test. Every reported number is from the test split.
- **Loss on the final draw only.** A history example is 9 draws; only the
  ninth is a target. The control sees the same targets with no context, so
  both versions get the same number of gradient signals per epoch and differ
  only in what they can read.
- **History draws are read sorted.** At eval and at pick time the 8 tape
  draws go in as published (whites sorted). Training shows every ordering.
- **One body for all four runs**: 4 layers, 4 heads, 128 wide, no dropout,
  0.80M parameters. Daydream Micro's size.
- **"On the floor" means within 1%.** Fixed in `predictions.md` before any
  run.

## 2026-11-24 — infrastructure

- The machine restarted mid-build with three agents training on one GPU. No
  lucky run had started. All four models now train on CPU.
- `train.py` grew an exact resume: an epoch's order and white shuffles derive
  from (seed, epoch), and a run resumed from `ckpt_last.pt` reproduced an
  uninterrupted run to the last digit on synthetic draws.
- The rate command's first draft expanded a 20,000-sample attention cache at
  once and held over 20 GB. It samples 500 at a time now, about 1 GB peak.
- The pipeline was smoke-tested on synthetic uniform draws only, so no real
  result was seen before the predictions were committed.
