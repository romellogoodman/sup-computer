# oblique — research log

The why behind each decision, newest last. Numbers live in the README's
leaderboard and in the JSON beside this file.

## 2026-11-23 — the corpus

**Cost.** A pilot of one 30-line request per model per register cost $0.0023
and put a full run at well under a dollar, against a $5 cap. The full run
was 960 requests of 50 lines for $0.357. Total with the pilot: $0.359.

**One generator can't turn reasoning off.** `meta/muse-ember` answers
`reasoning.effort: none` with HTTP 400, "Reasoning is mandatory for this
endpoint". It ran at `minimal`. Its fortune responses carry about twice the
completion tokens of its strategy responses, so the hidden trace is billed,
and it still came in at $0.094. Seven responses came back empty, five of
them from this model.

**Themes.** The first design had no theme words. Four models asked the same
question 120 times each would have written the same hundred lines, so each
request carries two words from a list of 160 plain nouns. The list is shared
by both registers and the draw is seeded by position, so request *i* of
every model and both registers gets the same pair. The classifier still
separates held-out corpus lines at 98.3%, so the registers differ in more
than topic. The words it leans on are worth a look in the next round.

**Length is where Haiku went.** 4,956 of Haiku's 12,261 lines ran past
eleven words. The other three lost about 50 each.

**The deck.** 247 distinct cards from six public transcriptions, fetched to a
gitignored directory. 42,705 lines checked, 0 matches at the 0.85 bar. The
closest surviving line sits at 0.789. A zero with nothing near it would have
been suspicious. This one has a near miss under the bar, which is what a
working check looks like.

## 2026-11-24 — training

**Three agents on one GPU.** The first seed ran at 0.2–0.5 s a step with
two other projects training beside it, and a machine restart killed it at
step 4,000. `sweep.py` gained `--resume`. Resumed alone under the studio's
GPU lock it ran at 74 ms a step. The log shows step 4,000 twice: the second
is the resumed run's eval of the same weights on fresh batches.

**The loss never turned.** Validation loss fell at every eval to 0.7689 at
step 12,000, with train loss at 0.7238. Kenosha's corpus was 24,000 lines of
six words and its spellings locked within 2,000 steps. This corpus is 27,000
distinct training lines and 70 passes weren't enough to start copying.

## 2026-11-24 — the harness, and a bar nobody cleared

**P1 holds.** At temperature 1.0 the corpus-trained classifier agrees with
the token on 96.5% of samples from step 12,000, against 98.3% on held-out
corpus lines. It crossed 85% by step 2,000.

**P4 fails.** The lowest-loss checkpoint is the last one, and its exact
memorization is 0.2% in its worst dial cell. There is no earlier checkpoint
to prefer on memorization grounds. The brief's reading of that outcome: the
corpus was bigger than it needed to be.

**The registered checkpoint rule named no checkpoint.** The rule asked for
under 10% exact memorization in every dial cell and at least 90% mean
well-formedness at temperature 1.0 and below. Every checkpoint clears the
first. None clears the second: the best is step 8,000 at 89.4%, and step
12,000 is at 88.6%.

The mechanism is one rule of the five. The corpus filter cut every line at
eleven words, and 8–12% of corpus lines sit exactly on that edge. A model
that writes characters can't count words, so it learned the distribution
without the cliff: a share of its lines run to twelve or thirteen words.
Those lines are spelled, punctuated and terminated. At step 12,000 they
are 13.2%, 10.8% and 8.9% of lines at temperatures 0.6, 0.8 and 1.0, and
adding them back puts all three cells at 98.9% or above. Garbled words account
for about 1% of lines at temperature 1.0 and none to speak of below it.

What this is not is kill criterion 1. That criterion, in the owner's words,
fires when no cell under 10% memorization produces well-formed lines,
because the corpus is too small to generalize from. Here every dial cell is under
1% memorization and 83–90% of its lines pass every check. The 90% figure was the
researcher's, registered before training, and it was set without knowing the
corpus's length edge would be soft in the model.

**What was done about it.** Nothing was re-thresholded. `choose.py` reports
that no checkpoint is eligible under the registered rule, then names the
checkpoint the same rule picks with the well-formedness bar set aside: the
lowest validation loss among checkpoints under the memorization bar, step
12,000. The rating sheets are drawn from it. Whether that fallback stands,
or the miss should be treated as kill criterion 1 and the corpus doubled, is
the owner's ruling, and it is flagged for him before he rates.

**The soft-cap is not a second dial here.** daydream's grid (8, 4, 2) was
built for a model with small logits. On this one, a cap of 8 at temperature
1.0 drops well-formedness from 90.0% to 41.6% and register accuracy from
96.5% to 76.6%. At 4 and 2 the output is noise and the classifier is at
chance. The brief sweeps the soft-cap only at the winning temperature, after
the ratings. That sweep needs a gentler grid, somewhere above 8.

**Sheets.** 200 dial lines and 60 register-test lines from seed 1337, step
12,000, sampled on the CPU from a fixed seed, exactly as they came out. The
keys flag which lines break the length band or carry a garbled word. No
line on either sheet is a copy of a training line.

**Second seed.** Seed 1338 is trained to the same 12,000 steps so that only
sampling remains. Its sheet waits on the first seed's peak.

## 2026-11-24 — the ratings, and the answer

**Who rated.** The owner passed the rating seat to the Claude Fable 5.2
session managing the project. It rated the dial sheet, the register test and
later the second-seed sheet from the sheet files, without the keys. The
researcher session built the sheets and rated nothing. So the ratings are a
model's, and the human seat the brief was built around is still open.

**The checkpoint ruling.** The managing session accepted step 12,000 as the
fallback while the owner was away, on the grounds in the entry above: the 90%
bar was the researcher's, kill criterion 1 did not fire, and the misses are a
word or two over length. The owner can overrule it.

**P2 fails, kill criterion 3 fires.** `[s]` keepers of 20: 8, 2, 6, 0, 2
across 0.6 to 1.4. The highest is at the lowest setting. Mean strange sits
between 3.85 and 4.10 at every temperature, so heat adds none. Mean usable
falls from 3.30 to 1.80. The band the hypothesis needed, strangeness rising
to meet usefulness falling, has only one of its two slopes.

**P3 is half.** Fortunes are less strange at every temperature. They are
also less usable at the lowest, 1.85 against 3.30, and 0 of 100 were
keepers. A strategy with a slipped word is still an instruction. A fortune
with a slipped word is a broken sentence.

**The second seed.** The managing session set its temperatures at 0.4, 0.6
and 0.8. `[s]` keepers of 10: 1, 2, 4. Its peak, 0.8, is within 0.2 of the
first seed's, so that clause of P2 holds on its wording, but the seeds swap
ranks at 0.6 and 0.8. At 0.4 mean strange is still 3.70: the platitudes the
hypothesis expected at the cold end did not show up. 0.4 was rated on this
seed only.

**The soft-cap above 8.** At temperature 0.6, caps of 64, 32, 24, 16 and 12
change nothing: well-formedness stays between 85.3% and 86.6% and register
recovery between 97.6% and 98.8%. With the first grid's 8, 4 and 2 that makes
a flat line and then a cliff. It ran on automatic metrics and was not rated.

**Release.** `oblique-nanogpt-1` is step 12,000 of seed 1337 with the dial at
0.6, labeled as the highest of five noisy keeper rates. The series
`instrument` is `text`: the site has no component by that name and falls back
to its generic text instrument, and the integrity check requires the field to
be non-empty. The git tag and the artifact URLs are left for the release
step.
