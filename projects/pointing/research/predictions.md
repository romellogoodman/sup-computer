# pointing — predictions and kill criteria

Registered 2026-11-23, before the first training run. The commit that adds
this file contains no run, no checkpoint and no score; the harness that will
do the scoring is already committed beside it.

The four predictions and the three kill criteria are the design brief's,
word for word. Under each one is the scoring rule fixed at build time, where
the brief left a threshold or a procedure open. Those rules are this
build's, not the brief's, and they are fixed here so the numbers cannot
choose them.

Unless a rule says otherwise, a score is taken at temperature 0 on every
line of the nine held-out works, from each arm's last snapshot (iteration
6,000), and mark scores cover the well-formed lines only.

## Predictions

### P1 — prose periods are free, commas are the task

> Line-end period recall above 95% on *prose* lines at the 2.66M arm; comma
> F1 between 40% and 70%. No threshold for verse line-ends: whether a verse
> line ends in a period, a comma or nothing is the judgment the report wants
> to see, and it is registered as unknown. If comma F1 clears 70% the corpus
> is more regular than it looks; if it's under 40% the model is guessing from
> line length.

Scoring. Two parts, each held or failed on its own.

- **P1a.** Recall of `.` in the final gap, over the test units of kind
  `prose`, 2.66M arm. Held above 95%.
- **P1b.** Comma F1 over all slots, 2.66M arm. Held from 40% to 70%
  inclusive.

A prose unit is a sentence cut from a reflowed paragraph, so its final gap
almost always holds a terminal mark. What P1a measures is whether the model
picks the period over the question mark and the exclamation mark.

### P2 — question marks depend on distance

> Every mark slot comes after the whole input line, so the model has always
> *read* the question word by the time it decides; what's hard is attending
> back from the last gap to a `what`, `who` or `shall` many words earlier.
> Prediction: question-mark recall lags period recall by more than 20 points
> at the 0.79M arm and closes to under 10 points at 2.66M, and within an arm,
> recall falls as the distance from the question word to the line end grows.
> This is the span thesis again (pona confirmed it for grammaticality; this
> tests it for a labeling task).

Scoring. Three parts.

- **P2a.** Period recall minus question-mark recall, all slots, 0.79M arm.
  Held above 20 points.
- **P2b.** The same difference at the 2.66M arm. Held under 10 points.
- **P2c.** For every gold `?`, the distance is the number of words from the
  clause's question word to the mark. The clause starts after the previous
  `.`, `?` or `!` in the line. A wh-word counts anywhere in the clause; an
  auxiliary counts only as the clause's first word. The word lists are in
  `harness.py`. Distances are binned 1–2, 3–5, 6–9 and 10+. Held, per arm,
  when recall in the 10+ bin is below recall in the 1–2 bin and their 95%
  Wilson intervals do not overlap. Marks with no question word in the clause
  are reported in their own row and decide nothing.

### P3 — the small arm learns marks in frequency order and stalls

> Ranking marks by corpus frequency predicts the order in which per-mark F1
> rises during training, and at 0.79M colon and semicolon F1 never leave
> zero.

Scoring. Two parts, on the 0.79M arm's fifteen snapshots, each scored on the
same 4,000-line sample of the test works (seed 1337). The 2.66M curve is
reported beside it and decides nothing.

- **P3a.** Frequency is a mark's count in the training slots. A mark's rise
  is the first snapshot where its F1 reaches half of its final value. A mark
  whose final F1 is under 5% never rose and ranks last. Only marks with at
  least 30 gold slots in the sample are ranked. Held when the Spearman
  correlation between frequency rank and rise order is 0.7 or higher.
- **P3b.** Colon F1 and semicolon F1 are each under 1% at every snapshot.

### P4 — well-formedness is not the problem

> Output-length errors and anchor errors each under 1% on both arms. A boring
> prediction; if it fails, the format is the finding.

Scoring. Four rates (two errors, two arms), over all test lines. Held when
all four are under 1%.

## Kill criteria

> 1. **Output-length or anchor errors above 5% after the first full run** —
>    the anchored marks-only format doesn't hold at this scale. Retry once
>    with the separator doubled; if it still fails, fall back to the copy
>    format and expect a worse but honest result.
> 2. **Comma F1 under 25% on both arms** — the corpus is too irregular for a
>    small model and the result is "a small model punctuates like a coin."
>    Publish as a note; don't release.
> 3. **The 0.79M arm ties the 2.66M arm everywhere** — the task is easier than
>    it looks and the interesting question moves to "how small can it go."
>    That is a different report; re-scope rather than ship the first one as
>    is.

Scoring.

- **Kill 1** triggers when either rate is above 5% on either arm.
- **Kill 2** triggers when comma F1 is under 25% on both arms.
- **Kill 3** triggers when the 0.79M arm is within 2 points of the 2.66M arm
  on line exact-match and on the F1 of each of period, comma, question mark,
  exclamation mark, colon and semicolon.

## Decisions this build made that the brief did not

Fixed before training, listed so a reader can weigh them.

- **Prose is reflowed.** The brief's unit is "verse lines and prose
  sentences, split on newlines as the corpus already is." The corpus hard-wraps
  prose at about 70 columns, so a newline in prose is not a sentence end. A
  wrapped paragraph is joined and cut after `.`, `?` or `!`. Without this, P1a
  would be scored on line ends that are mostly mid-sentence.
- **Three kinds of unit.** `verse` is a line in a paragraph of two or more
  lines whose lines start with capitals. `prose` is a sentence from a
  paragraph where at least 40% of the continuation lines start lowercase.
  `other` is everything else: speaker labels, headings, one-line speeches.
  The classifier is a heuristic and is wrong on cast lists and mixed speeches.
- **Quotes carry their side.** A gap between two words can hold a closing
  quote or an opening one. The label alphabet uses `“ ”` for double quotes
  and `‘ ’` for word-edge apostrophes and single quotes, set by position, so
  the two are scored apart as the brief asks.
- **Digits are letters.** The corpus has footnote numbers and dates.
- **Lines are shuffled.** Training pairs are in random order, so a line's
  neighbours tell the model nothing, in training as at test.
- **The corpus includes its apparatus.** The xl corpus carries the editors'
  introductions, footnotes and glossaries. They stay.
- **The held-out works were chosen by hand**, for coverage: five from the
  Complete Works, one more from an editor who also trains, and three volumes
  whose edition appears nowhere in training. The list and the reasons are in
  `data/build_corpus.py`.
- **Short lines repeat.** Held out by work, a long line cannot leak, but
  "exit" and a speaker's name recur across plays. The harness reports exact
  match on the lines whose words never appear as a training line.
- **Schedule.** Both arms: 6,000 iterations, batch 64, block 256, learning
  rate 1e-3 with cosine decay, dropout 0.1. Fifteen snapshots.
