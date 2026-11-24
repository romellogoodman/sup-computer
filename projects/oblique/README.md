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

In progress. The corpus is done and committed. Training was interrupted at
step 4,000 of 12,000 on the first seed and is being resumed; the harness
numbers, the checkpoint choice and the rating sheets follow it.

## Pipeline

Run everything from the **repo root** via `uv run`.

```
data/generate.py     ->  data/raw.txt + manifest.json + costs.jsonl   (paid; tools/synthgen, OpenRouter)
data/fetch_deck.py   ->  data/deck/                                   (the published cards, gitignored)
data/filter.py       ->  data/corpus.txt + filter-log.json
data/prepare.py      ->  data/oblique/{train,val}.bin + meta.pkl
sweep.py             ->  runs/<run>/ckpt-<step>.pt, every 500 steps
harness.py           ->  research/harness-<run>.json
sheets.py            ->  research/sheets/*.csv                        (blind sheets + keys)
score_sheets.py      ->  research/ratings-scored.json                 (after the human seat)
```

```bash
uv run python projects/oblique/data/fetch_deck.py
uv run python projects/oblique/data/filter.py        # rebuilds corpus.txt from the committed raw.txt
uv run python projects/oblique/data/prepare.py
uv run python projects/oblique/sweep.py --seed 1337 --run seed1337
uv run python projects/oblique/harness.py --run seed1337 --steps 500,1000,2000 \
    --out projects/oblique/research/harness-seed1337.json
```

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

## Leaderboard

Filled when the sweep and the harness finish.

## Versions

None released. `oblique-nanogpt-1` waits on the human ratings.

## Credits

- The shared [`core`](../../core/) engine (modern nanoGPT lineage: RoPE,
  RMSNorm, bias-free).
- Brian Eno and Peter Schmidt, *Oblique Strategies* (1975): the idea of a
  card that comes at a problem from the side. None of their cards is used.
- Corpus written by `anthropic/claude-haiku-5.5`, `openai/gpt-6-luna`,
  `deepseek/deepseek-v4.1-flash` and `meta/muse-ember`, served by OpenRouter.
- Design brief by Romello Goodman. Built and run by Claude Fable 5.2
  ([Claude Code](https://claude.com/claude-code)).
