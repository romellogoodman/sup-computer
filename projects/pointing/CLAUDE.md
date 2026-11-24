# CLAUDE.md — rules for agents working in pointing

Facts live in [`README.md`](README.md): the task, the format, the corpus, the
split, the version index and the scoreboard. This file is only the rules
(ADR-0030).

## Don't relitigate

- **The model emits marks, never words.** One slot per gap, an anchor letter
  before each word's slot, 2n + 1 symbols for n words. Don't switch to a copy
  format unless kill criterion 1 in `research/predictions.md` triggers.
- **`data/strip.py` is the only definition of a mark.** The corpus build, the
  harness and any instrument strip through it. An apostrophe or hyphen with a
  letter on both sides is a letter. Casing is not in v1.
- **Held out by whole work.** A work is in exactly one of train, val and
  test, and `data/split_manifest.json` says which. Never split by line. A new
  round scores on the same nine test works so versions stay comparable.
- **Score at temperature 0.** Sampling is for an instrument, not for a number.
- **Well-formedness is reported before any mark score**, and mark scores say
  how many lines they cover.
- **Predictions are frozen.** `research/predictions.md` was committed before
  the first run. Score against it; never edit it to fit a result. A new round
  registers new predictions in a new file.
- **The corpus is the shakespeare xl corpus.** The source list is read from
  `projects/shakespeare/data/_xl_corpus.py`; don't fork the list here, and
  don't edit that project from this one.

## Conventions

- Run everything from the repo root via `uv run`.
- `data/raw/`, `data/corpus/`, `data/tokenized/` and `runs/` are gitignored
  and rebuild from the committed scripts. The split manifest, the result
  JSONs and the training logs under `research/` are committed evidence.
- Training goes through `train_curve.py` and follows the `babysit-training`
  skill; the two arms run one after the other on MPS.
- Document as you go: `research/log.md` (why) and README § Leaderboard
  (numbers), committed with the run.
- Credit the researcher — root [`CLAUDE.md`](../../CLAUDE.md), ADR-0013.
