---
license: mit
language:
  - en
library_name: nanogpt
pipeline_tag: text-generation
tags:
  - pointing
  - nanogpt
  - char-level
  - gpt
  - punctuation-restoration
  - shakespeare
---

# Model Card — `pointing-nanogpt-1` (v1, the 2.66M arm)

The full experiment, with both arms and every prediction scored, is
[experiment 16](../reports/can-a-small-model-punctuate-a-line.md).

## What it is

A character-level GPT that puts punctuation back. It reads a lowercased line
with every mark removed and emits one mark per gap, and it never copies a
word. 2.66M parameters (6L/6H/192E, block 256) over a 58-symbol vocabulary.
Trained from scratch on the shakespeare xl corpus with its marks stripped:
the Complete Works plus twelve Project Gutenberg volumes of Marlowe, Jonson,
Kyd, Webster and Dekker.

A line of n words has n + 1 gaps. After the separator the model writes the
leading gap's slot, then each word's first letter and the slot that follows
the word. A slot is `_` or one mark.

```
to be or not to be that is the question|_t_b,o_n_t_b,t_i_t_q:
enter hamlet|[e_h.
```

The first letters are anchors: the model finds a word by matching a letter
instead of counting. The output is 2n + 1 symbols.

## Numbers that matter

Scored at temperature 0 on 27,995 lines from nine works the model never saw,
against the marks the editions printed.

| Metric | pointing-nanogpt-1 | context |
|---|---|---|
| lines exactly right | **32.5%** [32.0, 33.1] | "no marks, then a period" gets 24.7% |
| exact, lines whose words never appear in training | 28.2% | 25,837 of the 27,995 |
| exact by kind | verse 20.0%, prose 30.2%, other 67.7% | other is speaker labels, headings, one-line speeches |
| slots right | 85.0% | the no-mark baseline gets 80.6% |
| all marks, precision / recall | 57.1% / 47.7% | F1 52.0% |
| output-length errors | 0.84% | 234 lines |
| anchor errors | 0.71% | 199 lines |
| no-mark accuracy | 13.7% | 1,527 lines need nothing; the model marks most of them |
| val loss | 1.121 | per character, over both sides of the pair |

Mark scores cover the 27,754 well-formed lines (99.1%).

| mark | precision | recall | F1 | gold |
|---|---|---|---|---|
| period `.` | 64.9% | 69.1% | 66.9% | 17,569 |
| comma `,` | 46.0% | 43.2% | 44.5% | 18,948 |
| question mark `?` | 56.5% | 41.8% | 48.1% | 2,163 |
| exclamation mark `!` | 64.9% | 4.6% | 8.6% | 2,132 |
| semicolon `;` | 29.4% | 0.2% | 0.4% | 2,792 |
| colon `:` | 84.1% | 17.0% | 28.4% | 1,830 |
| opening bracket `[` | 74.4% | 65.9% | 69.9% | 1,324 |
| closing bracket `]` | 58.1% | 61.5% | 59.8% | 824 |
| leading apostrophe `‘` | 76.0% | 35.8% | 48.7% | 709 |
| trailing apostrophe `’` | 85.6% | 53.0% | 65.5% | 492 |
| opening quote `“` | 94.6% | 34.0% | 50.1% | 467 |
| closing quote `”` | — | 0.0% | 0.0% | 77 |
| dash `—` | — | 0.0% | 0.0% | 195 |
| parentheses `( )` | — | 0.0% | 0.0% | 124 |

The final gap, by kind of line:

| kind | lines | final slot right | period recall | question recall |
|---|---|---|---|---|
| prose sentence | 1,791 | 78.6% | 94.5% | 62.0% |
| verse line | 19,033 | 37.7% | 57.7% | 39.2% |
| other | 6,930 | 86.3% | 95.7% | 65.9% |

By source volume, on verse lines only (volumes differ too much in their mix
of verse and speaker labels to compare across all lines):

| source | edition in training? | verse lines | exact | the rule |
|---|---|---|---|---|
| Complete Works, Gutenberg #100 (five works) | yes | 8,747 | 20.5% | 14.6% |
| Marlowe, Tamburlaine Part 2, ed. Dyce | yes | 2,501 | 23.4% | 10.6% |
| Webster, The White Devil | no | 2,640 | 22.0% | 13.3% |
| Marlowe, Edward the Second | no | 2,772 | 15.1% | 11.0% |
| Kyd, The Spanish Tragedy, ed. Manly, old spelling | no | 2,477 | 18.0% | 17.1% |

## Scoring

There is no oracle. `harness.py` strips each held-out line with `strip.py`,
takes the model's slot string greedily, checks the length and every anchor,
and diffs the slots against the corpus. Held out by whole work, so no test
line has a neighbour in training. Short lines do repeat across plays, which
is why exact match is also reported on the lines whose words never appear
as a training line.

The gold is an editor's punctuation, not the playwright's, and editors
disagree. A model that pointed these lines well by a modern reader's
standard would still miss this gold often.

## Use temperature 0

Every number here is greedy. The format survives sampling, but a labelling
task has one answer per slot, and the scores were not measured at any other
temperature.

## Training

6 layers, 6 heads, 192 embedding, block 256, dropout 0.1, batch 64. 6,000
steps at learning rate 1e-3 with cosine decay to 1e-4 (beta2 0.99, warmup
100) on an Apple Silicon Mac (MPS), about 0.38 s per step. 8.27M training
characters, shuffled by line, about 12 epochs. The release is the last of
fifteen snapshots. Val loss was still falling slowly at the end (1.129 at
step 5,000, 1.121 at 6,000) while train loss sat at 0.98.

## Limitations

- **It barely beats a rule on whole lines.** 32.5% exact against 24.7% for
  "no marks, then a period". The gain is real on every kind of line and
  small on all of them.
- **Three marks are missing.** Semicolon recall is 0.2% and exclamation
  recall 4.6%; it writes a comma or a period where an editor chose `;` and a
  period where an editor chose `!`. Dashes, parentheses and closing quotes
  are never produced.
- **It marks lines that need nothing.** Of 1,527 lines with no marks it
  leaves 13.7% alone. It has learned that a line usually ends in something.
- **Verse line ends are close to a guess.** The final slot of a verse line
  is right 37.7% of the time, where the gold is a comma 30%, a period 26%
  and nothing 23% of the time.
- **Old spelling defeats it.** On Kyd's verse in Manly's old-spelling text it
  is 0.9 points above the rule. An unseen edition in modern spelling costs
  nothing measurable.
- **The colon score is an artifact.** Nearly all of it is the colon after
  "footnote N" in one editor's apparatus; on the other four test sources
  colon F1 is 0.0%.
- **One mark per gap.** 4.8% of marked gaps in the corpus hold two or more
  marks and the slot keeps the first, so `."` and `.]` lose their second
  mark before the model sees a label.
- **Lowercase only.** Casing is not restored.
- **A 1600s habit.** On twenty hand-typed lines of modern English it gets 3
  exactly right, drops most commas, and ends five statements and questions
  with a comma.
- One seed, one run per arm.

## Reproduce

The frozen folder (`projects/pointing/models/pointing-nanogpt-1/`) rebuilds
everything in place: `build_corpus.py → prepare.py → train_curve.py`, then
`harness.py` for the eval and `sample.py` to point a line of your own. The
split manifest in the folder records every work, its split, its edition, and
a SHA-256 of the Gutenberg file the release was built from. Weights ship via
the artifact URLs in `registry.json`, never in the tree.
