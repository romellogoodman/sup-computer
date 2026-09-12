---
name: house-style
description: The sup computer writing house style — every string a visitor or reader meets. Use whenever writing, editing, or reviewing studio text in this repo: research report drafts, model cards, README and ADR prose, frontmatter summaries, and all website copy (ledes, taglines, instrument labels, empty states, status and error lines, the 404). Four voices — report, studio, control, instrument — with a routing table from the job a string does to the voice that owns it; the report voice carries sixteen edicts distilled from Anthropic research posts, Thoughtful Lab, Ramp Labs, a Cursor engineering post and a Ramp brand essay. Published reports are frozen (ADR-0016) — never edit those; supersede them.
---

# House style

Operations, not vibes. Each edict is a move you make while writing or editing.
Evidence and source citations: `references/style-analysis.md`.

## Scope — what you may edit (hard rule)

**Published reports are frozen** (ADR-0016, `status: published` in
`research-docs/reports/`). Never apply these edicts to a published report's
prose — a new report supersedes an old one. Everything else is editable:
report *drafts*, model cards, website copy, READMEs, ADRs, frontmatter of
unpublished work. The skill covers every string a visitor reads on the
site, not only prose: a slider label, a status line, and a 404 are house
text too. When asked to "fix the writing" in a published report,
say it's frozen and offer a superseding report instead.

## Which voice? — route by the job the string does

A string arrives with a job. Find the job here; the voice it maps to carries
the rules. Four voices: **report** (the sixteen edicts below), **studio**,
**control**, **instrument**. Two jobs have no voice at all — *record* is
formatting, *off-stage* is wrapping.

| Job | Sub-job (examples from the site) | Voice |
|---|---|---|
| Orientation | masthead, tagline, footer "led by" | studio |
| | nav links, skip link, "back to the front page", "a release of …" | control |
| | page ledes (home, research, train) | studio |
| | section headings (Models, Lab notes, Specs, Releases) | control (sentence case) |
| | search / OpenGraph descriptions | studio |
| Naming | series names and verbs (write, dial, dream, play, draw, talk) | control |
| | series taglines | studio |
| | release taglines | control |
| | report titles, summaries, takeaways | report |
| | pills (essay, experiment, note, pinned, legal, played) | control |
| Instrument | run verbs (write, dream, draw, play, watch, stop, new game) | control |
| | parameter labels (temperature, top-k, max tokens, green light) | control |
| | dial words (recites … babbles; faint … total; sober … raving) | instrument |
| | readouts and legends (next token, plies, near-misses, ␠ ↵) | control |
| | captions that explain the mechanism | studio |
| | invitations — the empty state before the first run | instrument |
| | status lines (downloading…, dreaming… try 3 of 8) | control |
| | errors a player can see | control |
| | aria-labels, tooltips, alt text | control (full sentences) |
| Record | meta lines, spec-table headers, counts, the missing-value dash | *formatting* |
| Instruction | the train prompt, download labels | control |
| | the train page's explanatory sections | report |
| Off-stage | the 404 line | instrument |
| | engine errors, worker messages, download metadata | *wrap in control before it reaches the page* |

## Report voice — the edicts

**1. Open with the thing, not the lineage.** First sentence names the object or
the inversion; provenance (which experiment number, who ran it) moves to the
byline row or credits.
- Before (`illegal-moves-are-the-point.md`): "The fifth research round in the
  studio, and the first in a new faculty: daydream isn't a text-generation
  project like shakespeare, gatsby, or kenosha-kid…"
- After: "Most chess-model work treats illegal output as failure. Daydream
  renders it as a dim near-miss instead — the rejected dream is the exhibit."

**2. Sentence two lands the second punch.** After the opening image, deliver
what happened — a number or a verdict — not an aside or a category note.
- Before (`obsession-on-a-dial.md`): "A second LLM-assisted research
  experiment, run end-to-end by Claude Opus 4.8 — this time not to make a small
  model *better*, but to make it *obsessed*, controllably."
- After: "Golden Gate Claude, but Gatsby: a ~10M char-level model that cannot
  stop reaching for the green light. The obsession worked on the first run;
  the intensity dial took three."

**3. Frontmatter summary: two sentences, finding first, under 45 words.** No
90-word chained clause; the summary is what a feed reader sees. This is the
edict that drifts: the 2026-07 sweep fixed it, and by 2026-09 the newest
summaries (Token Chess, glyph, the font chapter) had grown back to 60–100
words of stacked dashes and colons. Count the words on every new one.
- Before (`illegal-moves-are-the-point.md`): one ~90-word sentence beginning
  "A three-tier chess-move GPT family (5x5, 8x8, and a custom 12x10 board)
  built around a single inversion…"
- After: "Three chess GPTs on three board sizes, built so illegal moves render
  as dim near-misses instead of being masked. All three land within four
  points on first-try legal-move rate (35–39%), and two design-plan 'facts'
  died on contact with the live engine."

**4. Bold budget.** Takeaways bullets: at most one bold phrase each. Body
prose: at most one bold per section, reserved for the pivot fact. Numbers are
never bolded — a number is its own emphasis. *Structural* bold is exempt and
uncounted: table row labels, bullet lead-in labels ("**Out of scope.**",
"**Run:**", Limitations claim-labels), and first-use coinage of a recurring
term ("**anchor-recall**"). In tables, bold marks the release or champion row
and nothing else — no stray bolded cells in other rows.
- Before (`obsession-on-a-dial.md`): "the bottleneck was **not the corpus**
  (clean and steeply graded throughout) but the **loudness of the conditioning
  signal** — a lone control digit was too quiet…"
- After: "the bottleneck was not the corpus — clean and steeply graded
  throughout — but the **loudness of the conditioning signal**: a lone control
  digit was too quiet for a char-model to read."

**5. One aside per sentence, and the aside is where the personality goes.**
A sentence gets a parenthetical or an em-dash aside, not both. If a second
aside wants in, it becomes its own sentence. The main clause stays a
measurement; the joke lives in the parenthesis (the Cursor exemplar: "and no
relational database to operate — hashtag blessed").
- Before (`kenosha-kid-nanogpt-2.md`): "we own the generator rather than
  scraping it, so the corpus is frozen and inspectable, and — the real reason
  — so we can **weight** and now **drift** it"
- After: "we own the generator rather than scraping it, so the corpus is
  frozen and inspectable. The real reason: owning it lets us weight and now
  drift it."
- Spending the aside (`a-language-small-enough-to-get-right.md`, illustrative):
  "chat-r1 lands at 96.9% [95.6, 97.8], above the corpus it learned from (the
  student marked the teacher's homework and found mistakes)."

**6. Follow long with short, and give the short sentence a job.** After any
~35+ word sentence, drop one under ten words. The exemplars reset rhythm
constantly ("Both checks cleared." "Far from it."). The studio already has
these — "This wasn't designed for; it just happened." — use them after every
dense stretch, not occasionally. But a short sentence is not only a reset. In
the best exemplars it is the thesis (edict 14), the refrain (13), the
rebuttal (15), or the turn: a one-sentence paragraph that changes the
argument's direction ("Passed down is the important phrase." "Then a real
person tries to use it."). Use the one-sentence paragraph for a turn and for
nothing else — as a rhythm device it is a tic.
- Before (`kenosha-kid-nanogpt-2.md`): the opening 45-word sentence about
  Slothrop and sodium amytal runs straight into another long clause chain.
- After: keep the long sentence, then: "Six words. That is the model's entire
  universe."

**7. No numbered sections, no "Abstract."** The `takeaways:` frontmatter
field is the abstract (ADR-0031). Report headings state the claim ("Run v2 —
fix the corpus, and the model still doesn't follow"); card and reference
headings are noun labels ("Training data," "Scoring") — the genre decides.
- Before (`obsession-on-a-dial.md`): "## 0. Abstract", "## 3. Run v1 — …"
- After: fold the abstract into the opening; "## Run v1 — the obsession works,
  the dial doesn't".

**8. Exact measurements, hedged interpretations.** Report the raw numbers
unhedged ("258/731 (35.3%)"). Hedge only derived quantities ("a ~2.3× ramp",
"roughly a third") and readings ("One reading… Another reading…"). Never hedge
a count you actually made; never state an interpretation as if measured.
Intensifiers are not measurements: "very fast", "basically a requirement",
"quite well", "literally any number" are numbers you didn't report. Replace
each with the number or cut it. The Cursor exemplar has 32 "very"s and 21
numbers in 5,350 words; the studio's budget is zero "very"s in a report.
- Before (hypothetical drift the rule blocks): "legal-move rate was roughly
  35%, which shows legality doesn't scale with board size."
- After: "legal-move rate was 258/731 (35.3%). One reading: legality-learning
  doesn't scale sharply with board size at these scales. Another: coincidence
  of these run lengths. Worth another round to find out which."

**9. Failures get a section and a mechanism.** Every report and card carries a
failure/limitations section as prominent as the win, and each failure names
its mechanism and number, uncushioned: "'A robot who wanted a friend' becomes
*Eli the rabbit*." Never the Ramp-companion move of reassuring the concern
away ("models are smart enough to contain themselves").
- Before (a cushioned draft sentence): "Topic-honoring could still use some
  improvement in certain cases."
- After: "Topic-honoring is still unreliable — the loud tag fixed the dial but
  did nothing for the topic prefix, which has the same root cause."

**10. Claim a highlight once.** "The method worth stealing" is house voice —
but it appears once per piece, at the evidence, not also in the intro.
- Before (`obsession-on-a-dial.md`): "That cheap ablation is the
  methodological highlight, and it's the part worth stealing" (§0) *and* "The
  method worth stealing." (§5).
- After: keep §5; in the opening say only what happened ("proven by a $0,
  byte-identical A/B").

**11. Charts open with the claim, then a reading instruction.** Introduce
every figure with the sentence it proves, then tell the reader where to look;
alt text describes the data's shape, not the topic. The studio's own line is
the standard — "The corpus dial (blue) climbs a cliff; both models barely
respond to it." Never "Figure 1 shows the results."
- Before (generic drift): "Below is a chart of green-light mentions by level."
- After: "You can see the gap directly. The corpus dial (blue) climbs a cliff;
  both models barely respond to it."

**12. End on the meaning, then credits.** The last content beat is one or two
sentences: what the finding means or the next concrete run ("Worth another
round to find out which"). Credits and reproduce blocks follow it; a bullet
list never carries the closing thought.
- Before (`illegal-moves-are-the-point.md`): the piece's final line is a
  credits bullet, "Set up and trained with Claude."
- After: before Credits, add: "The tight band across three boards is the
  finding to chase. If it survives a hyperparameter sweep, it's a statement
  about small models; if it doesn't, it was a coincidence worth one round."

**13. Coin a refrain.** One slogan-shaped sentence per piece — short, balanced,
quotable — stated once where it is earned and returned verbatim once where it
pays off, usually the closing beat. Not paraphrased: the second reading works
because the words are the same and the evidence has changed. A refrain may
bookend (the title asks it, the last line answers it). Evocative nouns
(the dial, the dream) do this at the word level; the refrain does it at the
sentence level. One per piece; two is a tic.
- Before (`budget-cant-buy-the-midgame.md`): the line "the budget buys the
  opening and rents the midgame" is the round-one heading and never returns.
- After: coin it in round-one prose — "What varied was how far the board got
  first. The budget buys the opening and rents the midgame." — then close
  round five on it: "All twenty-four chose the notepad. All twenty-four wrote
  nothing. The budget buys the opening and rents the midgame, and memory was
  the one thing on the menu that could have bought the midgame outright.
  Nobody paid for it."

**14. Close the paragraph on the line worth quoting.** A dense paragraph ends
on its thesis, not on its last detail. Reorder so the supporting checks come
first and the claim lands last; the antithetical couplet is the strongest
shape ("Taste remains human. Repetition becomes software." "The exotic
menial never disappeared. The floor changed."). The studio already has the
move — "One global knob does not fit twenty-six letters. The case never
needed a knob." — make it the default close for every evidence paragraph.
- Before (`a-language-small-enough-to-get-right.md`): the hazard paragraph
  ends on "exact-sentence matches (5–6%) concentrate in stock lines of the
  'mi pona.' class" — the thesis ("it can't misspell, so what's left is
  grammar proper") sits mid-paragraph.
- After: move the memorization check up, then end: "The word arm's remaining
  errors are particle machinery, 23 of 41. It can't misspell, so everything
  left is grammar."

**15. Stage the objection.** When a decision or result will be resisted and
there is only one reading, voice the reader's objection in its own words,
then answer it flat and short. This is the blunt cousin of "One reading…
Another reading…": use readings when the evidence is ambiguous and the
staged objection when it isn't. Once per piece, at the decision.
- Before (`one-model-or-twenty-six.md`): "The bake-off has a winner, and the
  release is not it. […] The studio ships the generalist anyway."
- After: "The bake-off has a winner, and the release is not it. You are about
  to say the studio is shipping the model that fails to draw a letter 29% of
  the time over the one that fails 8%. Yes. On purpose."

**16. Catalog once.** A list of nouns ("whitepapers, landing pages, sales
decks, product graphics, swag, customer logos") makes its point the first
time — volume, variety. Every later occurrence is filler; refer back with the
coined collective ("the launch bundle", "the eval suite") instead of
re-listing. Budget: one full catalog per concept per piece, and no sentence
carries two.
- Before (Ramp brand essay): 34 sentences with four or more commas, most of
  them the same list of marketing deliverables re-enumerated.
- After: list the deliverables once in the opening; thereafter "the launch
  bundle".


## Studio voice

The studio speaking about itself, in the third person, to a visitor who
may read one paragraph. Ledes, series taglines, instrument captions, search
descriptions. Plain, measured, no pitch.

**S1. Name the studio, the model, or the reader — never "we".** First person
belongs to the home intro and the essays; everywhere else the subject is
"the studio", "the model", "the instrument", or "you".
- Before (research lede): "Essays are written by Romello Goodman, one per
  question the studio has chased."
- After: "Essays are Romello Goodman's questions. Lab notes are the
  experiments that chase them."

**S2. A lede does two jobs in under 30 words: what the page holds, and who
made it.** Nothing the headings, the order, or the meta lines already say —
no "two shelves", no "newest first", no counts.
- Before: "Two shelves. Essays are written by Romello Goodman, one per
  question the studio has chased. Lab notes are the experiments behind them,
  run and written up by Claude models under direction, newest first." (39
  words, three of its five facts visible on the page)
- After: "Essays are Romello Goodman's questions. Lab notes are the
  experiments that chase them, written by the model that ran each one." (22)

**S3. Two tagline shapes, and they don't mix.** A *series* tagline is one
sentence in sentence case, verb first, with at most one em-dash pivot:
"Bends any story toward the green light — obsession you can dial from 1 to
5." A *release* tagline is a lowercase fragment that names what changed
since the last release: "same quality at a third the size — a corpus-trained
1k-vocab BPE". Sentence for the family, fragment for the version.
- Before (daydream micro): "Gardner minichess, 5x5 -- the smallest board
  with room for a full army"
- After: "Gardner minichess, 5×5 — the smallest board with room for a full
  army"

**S4. A caption explains the mechanism once, with edict 5's aside budget.**
One paragraph, numbers unhedged, one aside per sentence, no reassurance.
- Before (board caption): "Micro and Grand are watch-only — no rules engine
  runs in the browser for a 5×5 or a 12×10 board (the studio's arbiter,
  Fairy-Stockfish, is a native binary), so those boards render the dream
  without refereeing it."
- After: "Micro and grand are watch-only: no rules engine runs in the
  browser for a 5×5 or a 12×10 board, so those boards render the dream
  without refereeing it. The studio's arbiter, Fairy-Stockfish, is a native
  binary."

**S5. A search description is not the lede.** One sentence that names the
studio and says what the page is, for a reader who hasn't arrived yet.
- Before: the research lede pasted into `metadata.description`.
- After: "Research from sup computer, a small language model studio: essays
  by its director and lab notes written by the models that ran the
  experiments."

## Control voice

Everything a hand touches or a process reports: nav, run verbs, labels,
pills, status, errors, readouts. Lowercase, short, literal.

**C1. Lowercase what a hand touches; sentence-case what names a place.**
Nav, buttons, labels, pills, status lines, and error lines are lowercase.
Section headings and page titles are sentence case — they're places, not
controls.
- Before: "No lab notes filed under this series yet." (an empty state, so a
  control)
- After: "no lab notes for this series yet."

**C2. Verbs for actions, nouns for places.** A run button is one lowercase
verb, and the series verb when one exists (write, dream, draw, play). Two
words only when one word misleads ("tell it", "new game").

**C3. Labels are whole words.** "temperature", never "temp"; "max tokens";
"top-k". The same parameter carries the same label on every instrument.
- Before (text instrument): "temp" beside every other instrument's
  "temperature".
- After: "temperature".

**C4. A status line is present tense with one trailing ellipsis while
something runs, and none once it has stopped.** "downloading the model to
your browser…", "dreaming… try 3 of 8", then "your move". Use "the model",
not "model".
- Before: "loading model…" in one component, "loading the model…" in the
  next.
- After: "loading the model…" everywhere.

**C5. An error names the thing and the cause, then stops.** "the model
failed to load: {error}". No reassurance and no second sentence.
- Before: "weights not yet published for this release. The instrument lights
  up the moment they land; everything else is already wired."
- After: "weights not yet published for this release — the instrument lights
  up when they land."

**C6. Engine text never reaches the page bare.** A worker message, a parser
error, a stack trace goes after the colon of a C5 sentence, never in place
of one. "didn't parse: M inside an open contour" is right; "M inside an
open contour" alone is a leak.

**C7. Don't weld a status onto an invitation.** An empty state is either
the instrument's line (instrument voice) or a plain control-voice
statement, never both in one string. The backend line already says where
the model runs.
- Before: "the story appears here — the model runs entirely in your
  browser." (four instruments, four nouns, one welded sentence)
- After: "the story appears here."

## Instrument voice

The instrument's own line, spoken once, before the first note. Invitations,
dial words, the 404. This is where the site is allowed to be a poem, and
because it is rare it works.

**I1. An invitation is one line of the instrument's own poem.** Lowercase,
under ten words, ends with a period, no number in it. It says what is about
to happen in the instrument's vocabulary, not the studio's.
- Kept as exemplars: "six words, waiting to be dreamt." "across the water, a
  light." "the playbill fills as the model writes." "the notebook only keeps
  what was written down."

**I2. A dial gets five words that read as a scale.** One word each, least
to most, from the instrument's world: recites · murmurs · dreams · drifts ·
babbles. faint · soft · strong · heavy · total. sober · drowsy · dreaming ·
feverish · raving. A new dial writes its five before it ships.

**I3. One invitation per surface.** The second empty state on the same
instrument is control voice. A token-view placeholder is a control line;
the demo view holds the poem.

**I4. Never next to a number, never inside an error.** The moment a string
carries a count, a percentage, or a cause, it has left this voice.

## Formatting — the record job

No voice, only rules. Meta lines, spec tables, counts, the empty cell.

- **F1.** Fields in a meta line are separated by a middle dot with spaces:
  `experiment · Sep 2026 · shakespeare · researcher: Claude Fable 5.1`.
- **F2.** The em-dash is the only dash inside a sentence. Never `--`, never
  a hyphen doing a dash's job. Multiplication is `×`, not `x`.
- **F3.** A missing value is an em-dash alone.
- **F4.** A count is a numeral and a noun, pluralized by the count: "1
  near-miss", "3 near-misses", "14 plies". Never a bare numeral.

## What NOT to change

The studio's voice is plain, curious, findings-forward, with evocative names.
Do not sand these off:

- **Question titles** ("Can you put an obsession on a dial?") and claim-shaped
  report headings.
- **The `takeaways:` frontmatter field** — a YAML list of markdown bullets,
  required on experiment reports, the author's call on long notes, never on
  model cards (ADR-0031). Tighten its bullets; never remove it from an
  experiment.
- **Honesty sections** ("Be honest: what still doesn't work") — as strong as
  anything in the exemplars.
- **Cost as data** ("$0, byte-identical reformat", committed cost tables).
- **Named alternative readings** for surprising results ("One reading… Another
  reading…") — make this the standard move, not an occasional one.
- **Evocative recurring nouns** — the dream, the dial, anchors, near-misses,
  the green light. Coin once, then reuse the same word.
- **Reproduce-it sections** with runnable commands.
- **Personality beats** ("the part worth stealing", "Golden Gate Claude, but
  Gatsby") — capped by edict 10, never deleted.
- **The register drop** — one deliberate break in a composed voice ("hashtag
  blessed"; "a worse brief wearing a nice shirt"). It works because the
  surface around it is plain, so it is rare: one or two per piece, never in
  a summary or a heading, never next to a number.

## Quick pass order (editing a draft)

0. Route the string: which job, which voice (the table above). A report
   gets steps 1–6; site copy gets its voice's edicts and the formatting
   rules, then step 6.
1. Opening two sentences (edicts 1–2), then frontmatter summary (3) — count
   its words.
2. Strip bold to budget (4); un-stack asides and spend the one you keep (5);
   give every short sentence a job (6).
3. Headings and structure (7); numbers, hedges, and intensifiers (8);
   failures (9).
4. Deduplicate highlights (10); chart intros (11); closing beat (12).
5. Coin or cut the refrain (13); re-land paragraph closers (14); stage the
   one objection (15); collapse repeated catalogs (16).
6. Confirm the piece is not a published report before saving (scope rule).
