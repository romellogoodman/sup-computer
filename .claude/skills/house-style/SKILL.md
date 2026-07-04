---
name: house-style
description: The sup computer writing house style. Use whenever writing, editing, or reviewing studio prose in this repo — research report drafts, model cards, website copy, READMEs, ADR prose, frontmatter summaries. Encodes openings, emphasis budget, sentence rhythm, headings, hedging, failure sections, chart intros, and endings, distilled from Anthropic research posts, Thoughtful Lab, and Ramp Labs. Published reports are frozen (ADR-0016) — never edit those; supersede them.
---

# House style

Operations, not vibes. Each edict is a move you make while writing or editing.
Evidence and source citations: `references/style-analysis.md`.

## Scope — what you may edit (hard rule)

**Published reports are frozen** (ADR-0016, `status: published` in
`research-docs/reports/`). Never apply these edicts to a published report's
prose — a new report supersedes an old one. Everything else is editable:
report *drafts*, model cards, website copy, READMEs, ADRs, frontmatter of
unpublished work. When asked to "fix the writing" in a published report,
say it's frozen and offer a superseding report instead.

## The edicts

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

**3. Frontmatter summary: two sentences, finding first.** No 90-word chained
clause; the summary is what a feed reader sees.
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

**5. One aside per sentence.** A sentence gets a parenthetical or an em-dash
aside, not both. If a second aside wants in, it becomes its own sentence.
- Before (`kenosha-kid-nanogpt-2.md`): "we own the generator rather than
  scraping it, so the corpus is frozen and inspectable, and — the real reason
  — so we can **weight** and now **drift** it"
- After: "we own the generator rather than scraping it, so the corpus is
  frozen and inspectable. The real reason: owning it lets us weight and now
  drift it."

**6. Follow long with short.** After any ~35+ word sentence, drop one under
ten words. The exemplars reset rhythm constantly ("Both checks cleared." "Far
from it."). The studio already has these — "This wasn't designed for; it just
happened." — use them after every dense stretch, not occasionally.
- Before (`kenosha-kid-nanogpt-2.md`): the opening 45-word sentence about
  Slothrop and sodium amytal runs straight into another long clause chain.
- After: keep the long sentence, then: "Six words. That is the model's entire
  universe."

**7. No numbered sections, no "Abstract."** The takeaways block is the
abstract. Report headings state the claim ("Run v2 — fix the corpus, and the
model still doesn't follow"); card and reference headings are noun labels
("Training data," "Scoring") — the genre decides.
- Before (`obsession-on-a-dial.md`): "## 0. Abstract", "## 3. Run v1 — …"
- After: fold the abstract into the opening; "## Run v1 — the obsession works,
  the dial doesn't".

**8. Exact measurements, hedged interpretations.** Report the raw numbers
unhedged ("258/731 (35.3%)"). Hedge only derived quantities ("a ~2.3× ramp",
"roughly a third") and readings ("One reading… Another reading…"). Never hedge
a count you actually made; never state an interpretation as if measured.
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

## What NOT to change

The studio's voice is plain, curious, findings-forward, with evocative names.
Do not sand these off:

- **Question titles** ("Can you put an obsession on a dial?") and claim-shaped
  report headings.
- **The Key takeaways block at the top** of reports and cards (memory: takeaways
  at top, never bottom). Tighten its bullets; never remove it.
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

## Quick pass order (editing a draft)

1. Opening two sentences (edicts 1–2), then frontmatter summary (3).
2. Strip bold to budget (4); un-stack asides (5); add short sentences (6).
3. Headings and structure (7); numbers and hedges (8); failures (9).
4. Deduplicate highlights (10); chart intros (11); closing beat (12).
5. Confirm the piece is not a published report before saving (scope rule).
