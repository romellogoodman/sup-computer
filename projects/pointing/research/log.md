# pointing — research log

## 2026-11-23 — round 1: scaffold, corpus, two arms

Built from the September design brief in one session. The brief fixed the
task, the format, the two arms, the harness and the predictions. What the
build had to decide, and why:

- **Prose had to be reflowed.** The brief's unit is "verse lines and prose
  sentences, split on newlines as the corpus already is." The corpus
  hard-wraps prose at about 70 columns, so a prose newline is a line break,
  not a sentence end. `build_corpus.py` joins a wrapped paragraph and cuts it
  after `.`, `?` or `!`. Without that, P1's "line-end period recall on prose
  lines" would have been scored on ends that are mostly mid-sentence.
- **Verse, prose, other.** A paragraph of two or more lines is prose when at
  least 40% of its continuation lines start lowercase, verse otherwise. A
  lone line is `other`, with the all-caps speaker labels. 117,781 verse
  lines, 20,056 prose sentences, 69,138 other. The heuristic misfiles cast
  lists as verse and gets mixed speeches wrong.
- **Quotes carry a side.** The brief wants opening and closing quotes scored
  apart. One gap between two words can hold either, so a bare `"` in a slot
  is ambiguous. The label alphabet uses `“ ”` and `‘ ’`, set by position.
  `'tis` becomes `‘` before `tis`. The vocabulary came to 58 symbols, not the
  brief's "about 45": digits and the two directional pairs.
- **The split is by work, and the corpus had no works.** The xl corpus is one
  text. The Complete Works was cut at the 44 headings its contents page
  names; each other Gutenberg volume is one work. Nine works are test, three
  are val. The shakespeare project's own `test.txt` is a 250k-character slice
  through the middle of the Complete Works and is not used here: it cuts
  works in half.
- **Editions as the e-texts state them.** Four Marlowe volumes name Dyce, Kyd
  names Manly, Dekker names Rhys and the Mermaid Series. The rest name no
  editor, and the manifest says "not stated" instead of guessing.
- **Lines are shuffled.** In play order a training line's neighbours carry
  real context that a single test line never has. Shuffled, the context is
  noise in both.
- **0.77% of units are too long for a 256 block** and were dropped. Under
  the brief's 1% bar, so the block stayed 256.
- **4.85% of marked gaps hold two or more marks.** The slot keeps the first.
  On the test works that caps closing-quote recall at 17%, dash at 23% and
  closing-bracket at 47%, measured against the full text; mark scores are
  reported against the collapsed gold, with these ceilings beside them.
- **Snapshots.** The engine keeps one checkpoint. `train_curve.py` runs it in
  segments and copies a snapshot at fifteen points, dense early.

A baseline for scale: "no marks, then a final period" gets 24.7% of test
lines exactly right (56.2% of `other`, 13.7% of verse, 20.7% of prose).

Predictions and kill criteria were committed before the first run
(`predictions.md`).
