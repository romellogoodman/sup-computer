# oblique

> **A tiny GPT trained on synthetic aphorisms in two registers, sideways
> creative prompts and sincere fortunes, under one control token. The
> question it exists to answer: is oblique a place on the sampler's dial?**

```
[s] paint with the non-dominant hand until the first honest line appears.
[s] what would this look like if it were delivered by mail?
[f] ask for help and watch the world lean toward you.
[f] notice what returns to you each season.
```
*(four lines of the corpus, each behind its register token)*

The name is the quality the project measures. *Oblique Strategies* is Brian
Eno and Peter Schmidt's title and the deck is theirs. This model is in its
spirit and borrows none of its cards: no card was shown to a generator, and
none is in the corpus (§ Corpus).

## The question

There is no checker for "sideways". The studio's way around a quality that
can't be checked is to put it on a dial and watch where it lives: gatsby did
it for obsession, daydream for dreaminess, kenosha-kid for drift.

The hypothesis is that an aphorism model produces platitudes when sampled
cold and noise when sampled hot, and that somewhere between, a band of
settings produces lines a human reader rates as strange and usable at once.
A line rated 4 or more on both is a **keeper**. If the keeper rate peaks in
the middle and the peak holds on a second seed, oblique is a sampler
setting. If it never peaks, the answer is no, and that is the finding.

The fortune register is the control. A fortune is an aphorism with the
strangeness turned off: the same length, the same address, minus the
sideways move. One model with both lets the harness ask whether the token
keeps them apart, and gives the human judge a blind test of the same thing.

The predictions (P1–P4) and the kill criteria were committed before the
first training run: [`research/predictions.md`](research/predictions.md).

## State

Released as `oblique-nanogpt-1`, with the answer no. The write-up is
[Is oblique a temperature?](../../research-docs/reports/is-oblique-a-temperature.md)

| | Result |
|---|---|
| P1, the register token takes | holds: 96.5% at temperature 1.0, against a bar of 85% |
| P2, keepers peak in the middle | fails: `[s]` keepers of 20 were 8, 2, 6, 0, 2 across 0.6 to 1.4, highest at the cold end |
| P3, fortunes are the floor | half: fortunes rate less strange at every temperature, and less usable at the lowest (1.85 against 3.30) |
| P4, memorization arrives before oblique | fails: the lowest-loss checkpoint copies 0.2% of its lines |
| Kill criterion 1, no well-formed cell | did not fire on the brief's wording (below) |
| Kill criterion 3, P2 fails | **fired**: oblique is not a temperature; the model releases with the dial at 0.6, where the keeper rate was highest |
| Kill criterion 4, deck leakage | did not fire: 0 matches |

Three things a reader should know before trusting that table.

**The judge was a model.** The brief made the human rating seat the
experiment. Romello Goodman passed the seat to the Claude Fable 5.2 session
managing the project, which rated all three sheets blind from the sheet
files. The answer is about that model's taste. The human seat is still open:
the sheets, keys and scorer are here for a later pass (§ For a human rater).

**The registered checkpoint bar was missed.** The rule fixed before training
asked for under 10% exact memorization in the dial cells and at least 90%
well-formed lines at temperature 1.0 and below. Every checkpoint clears the
first. None clears the second: step 12,000 scores 88.6%. The shortfall is
lines that run a word or two past the corpus's eleven-word edge. The 90%
figure was the researcher's, not the brief's, and the brief's kill criterion
1 did not fire. The managing session accepted step 12,000 as a fallback while
the owner was away. He can overrule it.

**The numbers are small.** 20 lines a cell on the first seed and 10 on the
second. The two seeds swap ranks at the temperatures they share.

## For a human rater

The three sheets in [`research/sheets/`](research/sheets/README.md) are
committed as the model judge filled them. To rate them fresh, copy each sheet,
blank its rating columns, fill them without opening a `KEY-*.csv`, and score:

```bash
uv run python projects/oblique/score_sheets.py \
    --dial my-dial.csv --register my-register.csv --seed2 my-seed2.csv \
    --out my-ratings-scored.json
```

## Pipeline

Run everything from the **repo root** via `uv run`.

```
data/generate.py     ->  data/raw.txt + manifest.json + costs.jsonl   (paid; tools/synthgen, OpenRouter)
data/fetch_deck.py   ->  data/deck/                                   (the published cards, gitignored)
data/filter.py       ->  data/corpus.txt + filter-log.json
data/prepare.py      ->  data/oblique/{train,val}.bin + meta.pkl
sweep.py             ->  runs/<run>/ckpt-<step>.pt, every 500 steps
harness.py           ->  research/harness-<run>.json
choose.py            ->  research/choice-<run>.json                   (the registered checkpoint rule)
sheets.py            ->  research/sheets/*.csv                        (blind sheets + keys)
score_sheets.py      ->  research/ratings-scored.json                 (after the rating seat)
```

```bash
uv run python projects/oblique/data/fetch_deck.py
uv run python projects/oblique/data/filter.py        # rebuilds corpus.txt from the committed raw.txt
uv run python projects/oblique/data/prepare.py
uv run python projects/oblique/sweep.py --seed 1337 --run seed1337
uv run python projects/oblique/harness.py --run seed1337 --caps none \
    --steps 500,1000,2000,3000,4000,6000,8000,12000 \
    --out projects/oblique/research/harness-seed1337.json
uv run python projects/oblique/harness.py --run seed1337 --steps 12000 --caps 8 \
    --out projects/oblique/research/harness-seed1337.json    # then 4, then 2
uv run python projects/oblique/choose.py --run seed1337
uv run python projects/oblique/sheets.py --run seed1337 --step 12000
uv run python projects/oblique/sheets.py --run seed1338 --step 12000 --seed2 0.4,0.6,0.8
uv run python projects/oblique/score_sheets.py                # the committed, rated sheets
uv run python projects/oblique/test_score_sheets.py           # the scorer, on synthetic ratings
```

Training and harness sampling use the GPU. On the studio machine every such
command runs under the shared lock, one job at a time:
`lockf -k ~/.cache/sup-computer/gpu.lock uv run python ...`. A killed sweep
continues with `--resume`.

`generate.py` costs money and takes `--budget` on every run. The corpus is
committed, so nothing downstream needs it.

## Corpus

LLM-written, through [`tools/synthgen`](../../tools/synthgen/) on the
OpenRouter backend (ADR-0038). Four models, named by the owner, each wrote
both registers. 968 requests of 50 lines cost $0.36 in total.

The prompts describe the shape and show no example. A strategy is "a short
instruction to a stuck artist that approaches the problem from the side;
never advice, never a platitude; under twelve words." A fortune is "a
one-line fortune, sincere, second person, under twelve words, no proper
nouns." Each request also carries two plain theme words (door, river, salt)
from one list of 160 shared by both registers, so the registers differ in
the move they make and not in what they are about.

| Generator | Raw lines | Length | Proper noun | Duplicates | Balance | Kept `[s]` | Kept `[f]` | Cost |
|---|---|---|---|---|---|---|---|---|
| `anthropic/claude-haiku-5.5` | 12,261 | 4,956 | 22 | 923 | 882 | 2,921 | 2,556 | $0.127 |
| `openai/gpt-6-luna` | 12,045 | 49 | 1 | 2,254 | 1,377 | 4,181 | 4,183 | $0.060 |
| `deepseek/deepseek-v4.1-flash` | 11,968 | 54 | 6 | 3,114 | 1,258 | 3,599 | 3,928 | $0.079 |
| `meta/muse-ember` | 11,574 | 50 | 3 | 1,504 | 1,383 | 4,299 | 4,333 | $0.094 |
| **total** | 47,848 | 5,109 | 32 | 7,795 | 4,900 | 15,000 | 15,000 | $0.359 |

Two more lines failed the character set and 10 matched a line in the other
register. Haiku lost 40% of its lines to the length band: it writes past
eleven words.

**Which teacher repeats itself.** Each generator's lines, deduplicated
alone, exact and near together:

| Generator | `[s]` duplicate rate | `[f]` duplicate rate |
|---|---|---|
| `anthropic/claude-haiku-5.5` | 10.7% | 13.6% |
| `meta/muse-ember` | 10.9% | 12.1% |
| `openai/gpt-6-luna` | 14.0% | 21.6% |
| `deepseek/deepseek-v4.1-flash` | 24.2% | 24.4% |

Most duplicates are a generator repeating itself. Of deepseek's 3,114
dropped duplicates, 2,724 matched another deepseek line.

**Deck leakage: 0.** Every line that survived the length and proper-noun
rules, 42,705 of them, was compared against 247 distinct published cards
from six transcriptions. None matched exactly and none came within 0.85
normalized edit similarity. The closest surviving line sits at 0.789. Kill
criterion 4 did not fire.

The corpus is 30,000 lines, 1.53M characters, a 38-symbol vocabulary, a mean
of 8.3 words and 46 characters a line. `data/raw.txt` is every response as
it came back; `data/manifest.json` is synthgen's record of which model wrote
which response and what it cost; `data/filter-log.json` is every drop.

## Model

Char-level, kenosha scale: 4 layers, 4 heads, 128 embedding, block 128,
about 0.79M parameters, on the shared [`core`](../../core/) engine. One
recipe. The research variable is when to stop, so a single 12,000-step run
keeps its checkpoint every 500 steps and the harness reads along it.

A line in training is `[s] ` or `[f] ` and then the aphorism. A sample is
primed with a newline and a token and runs to the next newline.

## Choices the brief left open

The design brief fixed the shape and left values open. Claude Fable 5.2
chose these. The ones that bear on the predictions were committed with them,
before training.

| Choice | Value | Why |
|---|---|---|
| Lines per request | 50, at temperature 1.0 | Enough to amortize the prompt, short enough that a generator hasn't started repeating itself inside one response. |
| Theme words | two per request, one list for both registers | Without a nudge, 240 identical requests converge on the same lines. One shared list keeps topic from becoming the register signal. |
| "Do not quote or adapt any existing card deck" | in both prompts | Lowers leakage without naming the deck or any card. |
| Length band | 2–11 words, 8–80 characters | The prompts say under twelve words. 80 characters keeps a line with its token under 100, inside the 128 block. |
| Proper noun | a capital that doesn't open a sentence, the pronoun I excepted, or a line that opens on a day or month | Cheap and checkable. A proper noun that opens a line gets through. |
| Lowercase | the whole corpus | Keeps the vocabulary at 38 symbols, under the brief's 60. With proper nouns stripped a capital only marked a sentence start. |
| Near-duplicate | normalized Levenshtein similarity ≥ 0.85 on letters and spaces | The brief asks for edit distance under a threshold. 0.85 is synthgen's own near-duplicate default, and on a 46-character line it is about one changed word. |
| Dedup order | one seeded shuffle across generators | First occurrence wins, so a fixed order would have charged every shared line to whichever generator came second. |
| Cross-register match | dropped from both registers | A line both tokens claim teaches the token nothing. |
| Balance | 15,000 per register, the larger cut down | 50/50, and the top of the brief's 8,000–15,000 range. |
| Deck check bar | exact, or ≥ 0.85 similarity to any card | The same bar as a duplicate. |
| Reasoning | off; `minimal` for `meta/muse-ember` | That endpoint refuses to disable reasoning. The manifest records the value sent on every response. |
| Split | 90/10 by whole line | A held-out line is never half-seen, so held-out lines can calibrate the memorization metrics. |
| Training length | 12,000 steps, checkpoints every 500 | About 70 passes over the training split. |
| Temperatures | 0.6, 0.8, 1.0, 1.2, 1.4 | P2 puts the peak between 0.8 and 1.2 and needs an end on each side to fail against. |
| Soft-cap grid | off, 8, 4, 2 | daydream's grid; off is the default. |
| 8-gram overlap | character 8-grams, read against held-out corpus lines | The model writes characters, and ordinary English shares most of its 8-grams: held-out lines score 88%. |
| Garble | a word 3 or more edits from every corpus word | kenosha's line between a near-miss and a garble. |
| Checkpoint rule | lowest validation loss among checkpoints under 10% exact memorization in every dial cell and at least 90% well-formed at temperature 1.0 and below | Written down before training so the choice couldn't follow the results. |
| Sheet lines | exactly as sampled, unfiltered, first letter capitalized | A garbled line at a hot setting is what that setting produces. The key flags it. |
| Register test | 30 lines per register at temperature 1.0 | P1's temperature. |
| Rating anchors | the wording in `research/sheets/README.md` | The brief names the two axes and the keeper bar; the one-line anchors for 1 and 5 are the researcher's. |
| Soft-cap sweep after the ratings | off, 64, 32, 24, 16, 12 at temperature 0.6, automatic metrics only | The first grid showed 8 already breaks the model, so the sweep at the winning temperature looks above it. No line from it was rated. |

Two calls were not the researcher's. The second seed's temperatures (0.4,
0.6, 0.8) and the acceptance of the fallback checkpoint were the managing
session's.

## Leaderboard

Both seeds ran the one recipe to 12,000 steps. Validation loss fell at every
eval and never turned.

| Run | Seed | Steps | Train loss | Val loss | Note |
|---|---|---|---|---|---|
| `seed1337` | 1337 | 12,000 | 0.7238 | 0.7689 | harnessed; the sheets come from its last checkpoint |
| `seed1338` | 1338 | 12,000 | 0.7245 | 0.7691 | trained only; its sheet waits on the first seed's peak |

### The sweep, seed 1337

Five dial cells per checkpoint (temperatures 0.6 to 1.4, soft-cap off), 500
lines per register per cell. "Worst exact" is the highest exact-memorization
rate in any dial cell for either register. "Register" is the share of the
1,000 samples at temperature 1.0 whose token the corpus-trained classifier
recovers; the same classifier scores 98.3% on held-out corpus lines.
Held-out corpus lines score 88.0% on 8-gram overlap and 0.7% on near match,
which is what a line that was never trained on looks like.

| Step | Train loss | Val loss | Worst exact | Well-formed, T ≤ 1.0 | Well-formed at 1.4 | Near at 1.0 | 8-gram at 1.0 | Register at 1.0 |
|---|---|---|---|---|---|---|---|---|
| 500 | 1.1905 | 1.1899 | 0.0% | 58.1% | 27.6% | 0.0% | 43.3% | 71.4% |
| 1,000 | 1.0142 | 1.0243 | 0.0% | 77.6% | 55.1% | 0.0% | 62.0% | 79.2% |
| 2,000 | 0.9121 | 0.9264 | 0.0% | 76.6% | 69.9% | 0.0% | 72.4% | 87.4% |
| 3,000 | 0.8517 | 0.8747 | 0.0% | 81.6% | 71.1% | 0.1% | 72.6% | 91.8% |
| 4,000 | 0.8240 | 0.8511 | 0.0% | 80.9% | 76.1% | 0.0% | 75.0% | 93.8% |
| 6,000 | 0.7801 | 0.8155 | 0.0% | 88.0% | 78.4% | 0.1% | 78.0% | 94.8% |
| 8,000 | 0.7513 | 0.7954 | 0.2% | 89.4% | 81.9% | 0.1% | 79.2% | 96.4% |
| **12,000** | 0.7238 | 0.7689 | 0.2% | 88.6% | 83.0% | 0.2% | 80.7% | 96.5% |

The model does not memorize. At step 12,000 it copies 1 line in 1,000 at
its coldest setting, and its 8-gram overlap at temperature 1.0 sits under
the held-out corpus's own. No checkpoint reaches the registered 90%
well-formedness bar (§ State).

### Every cell, step 12,000

The mean of the two registers, 500 lines each. "Length-only" is the share of
lines whose single fault is the length band.

| Soft-cap | Temperature | Exact | Near | 8-gram | Well-formed | Length-only | Register |
|---|---|---|---|---|---|---|---|
| off | 0.6 | 0.1% | 1.4% | 91.6% | 86.7% | 13.2% | 98.7% |
| off | 0.8 | 0.0% | 0.6% | 87.5% | 89.1% | 10.8% | 97.5% |
| off | 1.0 | 0.0% | 0.2% | 80.7% | 90.0% | 8.9% | 96.5% |
| off | 1.2 | 0.0% | 0.2% | 73.0% | 87.2% | 7.2% | 94.0% |
| off | 1.4 | 0.0% | 0.0% | 64.1% | 83.0% | 5.8% | 90.8% |
| 8 | 0.6 | 0.0% | 0.1% | 73.6% | 76.8% | 6.8% | 93.0% |
| 8 | 0.8 | 0.0% | 0.1% | 54.2% | 63.1% | 3.6% | 85.7% |
| 8 | 1.0 | 0.0% | 0.0% | 35.0% | 41.6% | 2.6% | 76.6% |
| 8 | 1.2 | 0.0% | 0.0% | 20.8% | 28.9% | 1.4% | 66.4% |
| 8 | 1.4 | 0.0% | 0.0% | 11.3% | 15.7% | 2.1% | 59.6% |
| 4 | 0.6 | 0.0% | 0.0% | 5.2% | 7.2% | 0.8% | 57.0% |
| 4 | 0.8 | 0.0% | 0.0% | 2.0% | 5.1% | 1.7% | 52.1% |
| 4 | 1.0 | 0.0% | 0.0% | 0.8% | 2.7% | 1.4% | 50.3% |
| 4 | 1.2 | 0.0% | 0.0% | 0.4% | 1.8% | 1.5% | 50.0% |
| 4 | 1.4 | 0.0% | 0.0% | 0.2% | 1.4% | 1.3% | 50.6% |
| 2 | 0.6 | 0.0% | 0.0% | 0.1% | 0.9% | 1.0% | 49.7% |
| 2 | 0.8 | 0.0% | 0.0% | 0.0% | 0.6% | 1.1% | 50.8% |
| 2 | 1.0 | 0.0% | 0.0% | 0.0% | 0.6% | 1.5% | 50.3% |
| 2 | 1.2 | 0.0% | 0.0% | 0.0% | 0.7% | 1.0% | 50.1% |
| 2 | 1.4 | 0.0% | 0.0% | 0.0% | 0.1% | 1.3% | 49.9% |

The soft-cap grid borrowed from daydream is too strong for this model. A cap
of 8 already halves well-formedness at temperature 1.0, and 4 and 2 are
noise with the classifier at chance. The sweep the brief plans at the
winning temperature needs caps above 8.

### The ratings

Rated blind by Claude Fable 5.2 from `research/sheets/`, scored by
`score_sheets.py` into `research/ratings-scored.json`. A keeper is a line
rated 4 or more on both axes.

| Register | Temperature | Keepers of 20 | Mean strange | Mean usable |
|---|---|---|---|---|
| `[s]` | 0.6 | 8 | 3.85 | 3.30 |
| `[s]` | 0.8 | 2 | 3.95 | 2.80 |
| `[s]` | 1.0 | 6 | 4.10 | 2.65 |
| `[s]` | 1.2 | 0 | 3.95 | 2.05 |
| `[s]` | 1.4 | 2 | 4.05 | 1.80 |
| `[f]` | 0.6 | 0 | 2.10 | 1.85 |
| `[f]` | 0.8 | 0 | 2.30 | 2.30 |
| `[f]` | 1.0 | 0 | 2.80 | 1.60 |
| `[f]` | 1.2 | 0 | 2.90 | 1.55 |
| `[f]` | 1.4 | 0 | 3.65 | 1.30 |

Strange is flat across the sweep for `[s]` and usable falls at every step,
so the keeper rate has no middle to peak in.

Second seed (`seed1338`, step 12,000), 10 lines per register per temperature:

| Register | Temperature | Keepers of 10 | Mean strange | Mean usable |
|---|---|---|---|---|
| `[s]` | 0.4 | 1 | 3.70 | 3.10 |
| `[s]` | 0.6 | 2 | 3.70 | 3.20 |
| `[s]` | 0.8 | 4 | 4.00 | 3.10 |
| `[f]` | 0.4 | 0 | 1.80 | 2.30 |
| `[f]` | 0.6 | 1 | 2.10 | 2.30 |
| `[f]` | 0.8 | 0 | 2.20 | 1.70 |

Its `[s]` peak is at 0.8, within 0.2 of the first seed's 0.6. 0.4 was rated
on the second seed only, so seed and temperature are confounded there.

Register test, 60 lines at temperature 1.0: the rater named the token behind
52 (87%) and agreed with the corpus-trained classifier on 50 (83%). The
classifier named the token behind 58.

### The soft-cap above 8, temperature 0.6

Automatic metrics only, 500 lines per register per cap. Not rated.

| Soft-cap | Exact | 8-gram | Well-formed | Register |
|---|---|---|---|---|
| off | 0.1% | 92.0% | 85.7% | 97.6% |
| 64 | 0.0% | 91.4% | 86.6% | 97.8% |
| 32 | 0.1% | 91.2% | 85.3% | 98.6% |
| 24 | 0.0% | 90.4% | 85.5% | 98.8% |
| 16 | 0.1% | 89.6% | 85.8% | 98.2% |
| 12 | 0.0% | 87.7% | 86.4% | 98.0% |

Nothing moves down to 12, and the first grid shows the fall from 8. The
soft-cap is a cliff here, not a second dial.

### What still doesn't work

- **The model overruns the length band.** 8.9% to 13.2% of lines at
  temperature 1.0 and below run past eleven words. The corpus has a hard
  edge there and a character model has no way to see it.
- **The registered checkpoint bar was missed**, by 1.4 points at step 12,000
  and 0.6 at step 8,000. The fallback was accepted by the managing session.
- **The judge was a model and the cells are small.** One rater, 20 lines a
  cell, no repeat pass.
- **The fortune register failed as a control.** No `[f]` line was a keeper on
  the dial sheet; a slipped word turns a fortune into a broken sentence.
- **P4's premise didn't happen.** There is no memorization for oblique to
  arrive before, so training length chose nothing: the last checkpoint is
  the best on loss and on register accuracy.
- **The proper-noun filter misses a name that opens a line.** It keys on
  capitals inside a sentence.
- **Fortunes run long.** At temperature 0.6, 17.0% of `[f]` lines break the
  length band against 9.4% of `[s]` lines, so length alone hints at the
  register.

## Versions

| Version | Folder | What it is | Headline |
|---|---|---|---|
| v1 | [`models/oblique-nanogpt-1/`](models/oblique-nanogpt-1/) | step 12,000 of `seed1337`, both registers, dial at 0.6 | 96.5% register recovery, 0.2% exact copies, `[s]` keeper rate 8 of 20 at 0.6 |

### `oblique-nanogpt-1`

797,312 parameters, 38-symbol vocabulary, block 128. The frozen folder runs
in place: `python prepare.py && python train.py config.py && python sample.py`.
The dial setting is the best of five noisy ones, labeled as such.

Model card: [`research-docs/model-cards/oblique-nanogpt-1.md`](../../research-docs/model-cards/oblique-nanogpt-1.md).
Report: [Is oblique a temperature?](../../research-docs/reports/is-oblique-a-temperature.md)

## Credits

- The shared [`core`](../../core/) engine (modern nanoGPT lineage: RoPE,
  RMSNorm, bias-free).
- Brian Eno and Peter Schmidt, *Oblique Strategies* (1975): the idea of a
  card that comes at a problem from the side. None of their cards is used.
- Corpus written by `anthropic/claude-haiku-5.5`, `openai/gpt-6-luna`,
  `deepseek/deepseek-v4.1-flash` and `meta/muse-ember`, served by OpenRouter.
- Design brief by Romello Goodman. Built and run by Claude Fable 5.2
  ([Claude Code](https://claude.com/claude-code)). Rated by a second Claude
  Fable 5.2 session.
