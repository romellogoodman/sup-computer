# pointing

**A small GPT that reads an unpunctuated line and says where the marks go.**
Pointing is the scribal word for adding punctuation to an unpointed text.
The model reads a lowercased line with every mark removed and emits one mark
per gap. It is scored by the corpus itself: strip a human line, ask for the
marks back, diff against what the edition printed. No oracle, no judge.

It is the studio's first conditional text task with a ground truth, and the
first project whose corpus is another project's corpus.

## The question

**Can a small model punctuate a line it has never seen?** And the one that
rides along: which marks does it learn, and in what order? A period at the
end of a prose sentence is close to free. At the end of a verse line it is a
judgment, because verse runs on. A comma is a judgment even for an editor. A
question mark depends on a word that may sit far from where the mark lands.

One caveat caps every number here. The punctuation in these plays is
editorial, not the playwrights'. The model is scored against what an editor
chose, and two editors would not agree with each other.

## Format

The model never copies a word. A line of n words has n + 1 gaps: one before
the first word, one between each pair, one after the last. After the
separator the model emits the leading gap's slot, then for each word its
first letter and the slot for the gap after it. A slot is `_` for nothing or
a single mark.

```
the quick brown fox jumps over the lazy dog|_t_q_b_f_j_o_t_l_d.
o that this too too solid flesh would melt|_o,t_t_t_t_s_f_w_m,
enter hamlet|[e_h.
```

The first letters are **anchors**. Without them the model has to count to
know which slot belongs to which word, and small character models count
badly. With them it matches a letter. The output is 2n + 1 symbols, a
fraction of a copy, and a wrong answer is a wrong mark or a wrong anchor,
never a garbled word.

The last example shows the format's one lossy rule. `[Enter Hamlet.]` puts
two marks in the final gap, and a slot holds one, so the gap keeps the first
in reading order and the bracket is lost. 4.8% of the corpus's marked gaps
hold two or more marks; the harness counts what each mark loses.

## What counts as a mark

All of it is `data/strip.py`.

- Everything is lowercased. Casing is left out of v1.
- **Apostrophes inside words are letters.** `don't` and `o'er` are
  orthography, and a model that had to reinvent every contraction would be
  solving a different problem.
- **Hyphens follow the apostrophe rule.** A hyphen between two letters stays
  a letter and `well-met` stays one word. A dash is a mark: `—`, `--`, or a
  hyphen with a space on either side.
- Sixteen marks: `, . ; : ? !`, the dash `—`, the ellipsis `…`, brackets
  `[ ]`, parentheses `( )`, and two pairs that record a side. `“ ”` are
  double quotes. `‘ ’` are single quotes and word-edge apostrophes: `‘`
  attaches to the word after it (`'tis`), `’` to the word before (`th'`).
  One gap can hold either side, so the label has to say which.
- Digits are word characters. Accents fold to ASCII. Italic markup is
  deleted.

The vocabulary is 58 symbols for both sides of the pair.

## Corpus

**The shakespeare xl corpus with its marks stripped**: the Complete Works
plus twelve Project Gutenberg volumes of Marlowe, Jonson, Kyd, Webster and
Dekker, the text that trained `shakespeare-nanogpt-3`. The source list is
read from `projects/shakespeare/data/_xl_corpus.py`. It is the one human
corpus in the tree where punctuation does real work. All of it is public
domain, and it includes the editors' introductions, footnotes and
glossaries, which stay in.

`data/build_corpus.py` cuts it three ways.

**Into works.** The Complete Works splits into its 44 plays and poems. Each
other volume is one work. 56 works in all.

**Into units**, the lines the model sees one at a time. A verse line is a
unit. Prose in these files is hard-wrapped at about 70 columns, so a wrapped
paragraph is reflowed and cut into sentences, and each sentence is a unit.
Speaker labels, headings and one-line speeches are units of kind `other`.
The kinds come from a heuristic on line starts; it is wrong on cast lists
and on speeches that mix verse and prose.

| kind | units |
|---|---|
| verse | 117,781 |
| prose | 20,056 |
| other | 69,138 |
| dropped, too long for a 256 block | 1,604 (0.77%) |

Lines with no marks are kept: "this line needs nothing" is a prediction too.

**Into splits, by whole work.** A model cannot recover a held-out line from
its neighbours, because its neighbours are held out with it. Training lines
are shuffled for the same reason.

| split | works | units |
|---|---|---|
| train | 44 | 167,689 |
| val | 3 | 11,291 |
| test | 9 | 27,995 |

The nine test works were chosen by hand, before any model existed, to cover
the kinds of text and to test editions the model has and has not seen:

| test work | volume | edition in training? |
|---|---|---|
| King Lear, Much Ado About Nothing, Richard II, The Tempest, Venus and Adonis | Gutenberg #100 | yes, 37 other works |
| Marlowe, Tamburlaine Part 2 | #1589, ed. Dyce | yes, two other Dyce volumes |
| Marlowe, Edward the Second | #20288 | no |
| Kyd, The Spanish Tragedy | #6043, ed. Manly, old spelling | no |
| Webster, The White Devil | #12915 | no |

[`data/split_manifest.json`](data/split_manifest.json) records every work,
its split, its Gutenberg volume, the edition as the e-text states it, and a
SHA-256 of the file used. Short lines repeat across plays ("exit", a
speaker's name), so 7.7% of test lines have words that also appear as a
training line. The harness reports exact match with and without them.

## Model

Two arms, one recipe: same pairs, same block of 256, same 6,000-iteration
schedule.

| arm | shape | parameters |
|---|---|---|
| regular | 6 layers / 6 heads / 192 embedding | 2.66M |
| small | 4 layers / 4 heads / 128 embedding | 0.79M |

## Harness

`harness.py` generates each test line's slot string at temperature 0 and
diffs it against gold. It reports well-formedness first (output-length errors
and anchor errors), then per-mark precision and recall on the well-formed
lines, line-end marks for verse and prose apart, scores per source volume,
line exact-match, no-mark accuracy, and the marks lost to the one-mark-per-gap
rule. `--curve` scores every snapshot of a run on a fixed 4,000-line sample.
`--modern` scores twenty hand-typed lines of modern English
(`research/modern_sample.txt`), as a note and not a score.

The predictions and kill criteria were committed before the first run:
[`research/predictions.md`](research/predictions.md).

## Pipeline

```bash
uv run python projects/pointing/data/build_corpus.py     # works, units, splits, manifest
uv run python projects/pointing/data/prepare.py          # train.bin / val.bin / meta.pkl
uv run python projects/pointing/train_curve.py projects/pointing/config/regular.py
uv run python projects/pointing/train_curve.py projects/pointing/config/small.py
uv run python projects/pointing/harness.py --out_dir projects/pointing/runs/regular-r1
uv run python projects/pointing/harness.py --out_dir projects/pointing/runs/regular-r1 --curve
uv run python projects/pointing/harness.py --out_dir projects/pointing/runs/regular-r1 --modern
```

`train_curve.py` drives the shared engine's `train.py` in segments and keeps
a snapshot at fifteen points, because the report's figure is per-mark F1
across training.

## Versions

No release yet.

## Leaderboard

No runs yet.
