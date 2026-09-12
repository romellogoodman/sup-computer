# Style analysis — evidence behind the house-style skill

Three exemplar sources chosen by the studio lead, read 2026-07-04, compared
against three pieces of the studio's own published writing. This file is the
evidence; the edicts live in `../SKILL.md`.

Pieces read:

- **Anthropic research** (5): [natural-language-autoencoders](https://www.anthropic.com/research/natural-language-autoencoders),
  [teaching-claude-why](https://www.anthropic.com/research/teaching-claude-why),
  [claude-code-expertise](https://www.anthropic.com/research/claude-code-expertise),
  [n-days](https://www.anthropic.com/research/n-days),
  [project-fetch-phase-two](https://www.anthropic.com/research/project-fetch-phase-two).
- **Thoughtful Lab** (3): [the-state-of-ai-post-training-agents](https://www.thoughtfullab.com/the-state-of-ai-post-training-agents.html),
  [letting-ai-posttrain-ai](https://www.thoughtfullab.com/letting-ai-posttrain-ai.html),
  [posttrainbench](https://www.thoughtfullab.com/posttrainbench.html).
- **Ramp Labs** (1 + 1 companion): [labs.ramp.com/swebench](https://labs.ramp.com/swebench)
  (full text captured via rendered page — the site is client-rendered React and
  invisible to plain fetchers). labs.ramp.com hosts **only this one piece**; the
  only outbound editorial link is the companion post
  [why-we-built-our-background-agent](https://builders.ramp.com/post/why-we-built-our-background-agent)
  on builders.ramp.com, which was read as the "1–2 others."
- **Studio** (3): `research-docs/reports/obsession-on-a-dial.md`,
  `research-docs/reports/illegal-moves-are-the-point.md`,
  `research-docs/model-cards/kenosha-kid-nanogpt-2.md`.

**Second reading, 2026-09-12** — two more pieces, chosen by the studio lead,
read against four newer studio reports (`a-language-small-enough-to-get-right`,
`one-model-or-twenty-six`, `budget-cant-buy-the-midgame`, and the reports
index summaries). Sources 4–5 and studio-delta item 8 below come from it.

- **Cursor engineering** (1): [git-at-any-scale](https://cursor.com/blog/git-at-any-scale),
  Vicent Martí, 2026-08-18 (the page ships its body twice in the HTML;
  dedupe before counting).
- **Ramp brand** (1): "Brand as software", Paul Jun, an X article,
  2026-09-11 (pasted text; no stable URL).

---

## Source 1 — Anthropic research posts

**Openings.** Sentence one orients in plain language; sentence two delivers the
mechanism or stake. No throat-clearing, no self-reference to the publication.
"When you talk to an AI model like Claude, you talk to it in words."
(natural-language-autoencoders). "Agentic coding has taken off."
(claude-code-expertise). When there is history, it's one clause: "In August
2025, we ran an experiment…" (project-fetch-phase-two).

**Findings.** Agent–verb–number, with the number mid-sentence where the verb can
act on it: "Claude Mythos Preview … built 8 working code-execution exploits
autonomously" (n-days). Hedges are calibrated and attach to derived or uncertain
quantities, not raw counts: "roughly 12 hours," "about 20 times faster,"
"between 12% and 15% of the time."

**Structure.** Question-form headings are a signature: "What did we do?",
"Where did Claude struggle?" (project-fetch), "Why does agentic misalignment
happen?" (teaching-claude-why). Mostly **no TL;DR block** — the one exception is
claude-code-expertise, which opens with a "Key findings" section.

**Failures.** A struggle section is structural, not buried, and failures come
with mechanism: "it couldn't chain those together to go from `lowpriv` to
`SYSTEM`" (n-days); "The most important limitation is that NLA explanations can
be wrong" (natural-language-autoencoders).

**Voice.** Institutional "we," with occasional short conversational beats:
"This doesn't mean that LLMs have now solved robotics. Far from it."
(project-fetch). Sentence rhythm alternates long and very short:
"Unquestionably, it could not."

**Endings.** Forward-looking, one or two sentences: "It would be unwise to rule
out the same trajectory in hardware" (project-fetch); "we hope to share more on
this site once we're ready" (n-days).

## Source 2 — Thoughtful Lab

**Openings.** The bluntest of the three sources — the finding or the build lands
in the first two sentences: "We built a posttraining task that runs for 20
hours with the Tinker API. The core bottleneck is research intuition."
(letting-ai-posttrain-ai). "How well can AI agents post-train language models?
We built a benchmark to find out." (posttrainbench).

**Findings.** Numbers lead the sentence and nulls are stated flat: "Only 4 out
of 20 agents reach >25% pass@4; the rest hover near zero."
(letting-ai-posttrain-ai). "No agent-trained model exceeds random chance on
GPQA." (posttrainbench).

**Structure.** Headings are claims and observations, not labels: "Agents make
the same set of mistakes," "Agents have no working sense of time,"
"Sophisticated methods, amateur mistakes." No TL;DR blocks anywhere.

**Failures.** Failure *is* the content: "Almost every agent we tested failed
it." Failure sentences carry the mechanism list: "generating SFT data from a
weak base model, skipping basic sanity checks…, and evaluating on the training
distribution without noticing."

**Voice & rhythm.** "We" throughout, a rare "you" ("feel free to skip").
Deliberate long/short alternation: "Both checks cleared."

**Endings.** Zoom out to the thesis under the experiment: "…that research
intuition is trainable, and that once it is, improving a model becomes
something AI should do for anyone, on any task, at all times."
(letting-ai-posttrain-ai). Or a living-project promise (posttrainbench).

## Source 3 — Ramp Labs (swebench)

This piece is a **reference page**, not an essay — a benchmark spec with a
dashboard attached. Its operations transfer to model cards and site copy more
than to reports.

**Opening.** Definition + motivation in two sentences: "Ramp SWE-Bench is a
private, production-grounded coding benchmark created from engineering work in
Ramp's backend. Public benchmarks saturate quickly and can leak into training
data…"

**Structure.** Noun-label sections (Tasks, Curation, Harness, Scoring, Privacy,
Future work, References); lists do heavy lifting; a question list frames the
purpose ("How do they navigate massive codebases? … Where do they break?").

**Epistemics.** Ambiguity is stated as named alternative readings: "When no
model solves the task, it could mean a brittle test or broken environment over
real difficulty." Caveats are owned, not cushioned: "it is inherent to the
SWE-Bench evaluation mechanism."

**Ending.** Future-work list, references, then a colophon line: "Ramp SWE-Bench
v1 · Last updated: June 30, 2026."

The builders.ramp.com companion is looser and product-flavored ("Internal
adoption charts have been vertical: ~30% of all pull requests…") — useful as a
number-first example, but its unhedged confidence ("frontier models are smart
enough to contain themselves") is *not* house style.

---

## Where the sources disagree — and what the skill picks

1. **Takeaways block.** Anthropic mostly none (one "Key findings"); Thoughtful
   Lab none; Ramp none. The studio already leads every report and card with a
   Key takeaways block, and it works. **Pick: keep the block** — it's the house
   feature the sources mostly lack — but tighten its bullets (see delta).
2. **Heading style.** Anthropic asks questions, Thoughtful Lab states claims,
   Ramp uses noun labels. **Pick: claims/questions in reports, noun labels in
   model cards and reference pages.** The genre decides.
3. **Opening move.** Anthropic orients gently; Thoughtful Lab leads with the
   punch; Ramp defines the artifact. **Pick: Thoughtful Lab for reports**
   (finding in the first two sentences), **Ramp for cards** (definition first).
4. **Hedging.** Anthropic hedges derived quantities ("roughly," "about");
   Thoughtful Lab barely hedges; the Ramp companion overclaims. **Pick:
   Anthropic's calibration** — exact measurements, hedges only on derived
   multipliers and interpretations.
5. **Endings.** Anthropic looks forward; Thoughtful Lab zooms to thesis; Ramp
   ends in a colophon. **Pick: a 1–2 sentence meaning/next-run beat before
   credits** (Anthropic/TL blend); the colophon pattern stays fine for cards.

## The studio delta

**Already strong — protect it.** Question titles ("Can you put an obsession on
a dial?"), the takeaways-at-top block, failure sections as prominent as wins
("Be honest: what still doesn't work"), exact costs as data ("$0,
byte-identical reformat"), named alternative readings ("One reading… Another
reading… Worth another round to find out which" — illegal-moves), chart intros
that tell you how to read the chart ("The corpus dial (blue) climbs a cliff;
both models barely respond to it"), evocative recurring nouns (the dream, the
dial, anchors, near-misses), reproduce-it sections, personality beats ("the
part worth stealing"). No exemplar does the honesty sections better.

**Gaps, ranked.**

1. **Bold overload.** Studio body prose bolds several phrases per paragraph
   ("the bottleneck was **not the corpus** … but the **loudness of the
   conditioning signal**") and takeaway bullets carry 3+ bolds each. All eight
   exemplar pieces use almost no mid-sentence bold; sentences carry their own
   emphasis. Everything shouting means nothing is loud.
2. **Meta-first openings.** Both reports open with lineage, not the finding:
   "The fifth research round in the studio, and the first in a new faculty"
   (illegal-moves); "A second LLM-assisted research experiment, run end-to-end
   by Claude Opus 4.8" (obsession). Exemplars open with the thing itself.
3. **Frontmatter summaries are single mega-sentences.** illegal-moves' summary
   is ~90 words of chained clauses.
4. **Academic scaffolding.** obsession numbers its sections 0–9 and has an
   "Abstract" heading; no exemplar numbers sections, and the takeaways block
   already does the abstract's job.
5. **Aside stacking.** Sentences carry a parenthetical *and* an em-dash aside
   *and* bold at once ("and — the real reason — so we can **weight** and now
   **drift** it", kenosha card). Exemplars allow one aside, then a short
   sentence to reset.
6. **Repeated self-highlighting.** obsession calls its ablation the highlight
   twice (§0 and §5). Claim it once, where the evidence is.
7. **Endings trail off into credits.** illegal-moves' last content is a credits
   list; the "Worth another round" beat is buried mid-report instead of
   closing it.
8. **Summary drift.** The 2026-07 sweep fixed frontmatter summaries; by
   2026-09 the newest ones had grown back to 60–100 words of stacked dashes
   and colons (`budget-cant-buy-the-midgame`, `one-model-or-twenty-six`,
   `three-predictions-from-a-font-chapter`). Body prose held the style;
   the summaries — the part a feed reader sees — did not. Edict 3 now
   carries a word cap.

---

## Source 4 — Cursor engineering (git-at-any-scale)

A senior engineer's conference talk, transcribed: story-first, lecturer's
signposting, jokes in parentheses, refrains, and a marketing close.

| | count |
|---|---|
| words | 5,350 |
| sentences / median length | 258 / 18 words |
| sentences under ten words | 47 (18%) |
| bold | 0 |
| parentheses / em-dashes | 38 / 8 |
| "very" | 32 |
| numeric mentions | 21, nearly all in the last fifth |
| words before the product is named | 2,877 |
| "you" / "we" / "I" | 52 / 71 / 4 |

**Opening.** A punch, then history: "Hosting Git repositories at scale is a
nightmare." Linus, GitHub's 2008 tagline, NFS, GFS, DRBD, Spokes — the
product appears past the halfway mark. Edict 1 satisfied, edict 2 not.

**Emphasis.** No bold anywhere; fragments do the work ("Very pragmatic. It
didn't work." "A short-lived deployment with GFS. A longer-lived deployment
based on DRBD. They all hit a wall.").

**The joke in the parenthesis.** The main clause stays technical; the
personality is in the aside: "(Linus is not going to come over and check)",
"(and no relational database to operate — hashtag blessed)", "(Microsoft's
own competitor to Microsoft's own GitHub)". → edict 5 amendment.

**Refrain.** "Always be correct when degraded, and always fast when healthy"
twice verbatim; "doing weird stuff with Git", "bit the bullet", "look it up"
as callbacks. → edict 13.

**Aphorism as paragraph-closer.** "With three-phase commit, the floor is
always too high, and the ceiling too low." "A corrupted copy is as bad as a
missing one." "Pets, not cattle." Each ends its paragraph. → edict 14.

**Staged objection.** "'That is insane,' I hear you mumble from behind your
screen across time and space. 'UDP is not a reliable transport.' Of course it
isn't." → edict 15.

**Not house style.** Intensifiers instead of measurements for 4,000 words
(→ edict 8 amendment); every failure belongs to someone else, and the new
system's one limit is cushioned with "we're working on innovative ways"
(edict 9); the last section is a pitch — "We're hoping you'll place your
trust in us and our platform" (edict 12); unhedged overclaims ("literally
any number of replicas", "the scalability of S3 is unmatched").

---

## Source 5 — Ramp brand essay ("Brand as software")

A manifesto: thesis, history lesson, metaphor, testimony. Tighter than
Source 4 at the sentence and looser at the evidence.

| | count |
|---|---|
| words | 4,600 |
| sentences / median length | 336 / 12 words |
| sentences under ten words | 127 (38%) |
| one-sentence paragraphs | 19 |
| parentheses / em-dashes / exclamation marks | 1 / 5 / 0 |
| "very" | 0 |
| numbers that are evidence | 1 (375 Slack requests) |
| sentences with four or more commas | 34 |
| "you" / "we" / "I" | 8 / 19 / 21 |

**The antithetical couplet** is the signature and closes nearly every
section: "Consistency says, 'We always look like this.' Coherence says, 'We
evolve, and you still know it is us.'" "Taste remains human. Repetition
becomes software." "Memory is not imagination." → edict 14.

**Bookend refrain.** Noise versus music is the first line and the last, with
the metaphor seeded a dozen times between (score, tempo, song, "five
departments tuning their instruments in public"). → edict 13 (bookend form).

**One-sentence paragraph as a turn.** "Passed down is the important phrase."
"Then a real person tries to use it." Nineteen of them, each a change of
direction, and no exclamation marks or intensifiers anywhere — the paragraph
break is the only emphasis. → edict 6 amendment.

**History closed with aphorisms.** Bernbach 1941, Rand, Caplan 1981, each
episode landing on a line: "The restraint was part of the argument. The
layout delivered the joke." "The exotic menial never disappeared. The floor
changed."

**The register drop.** Against a composed surface, two or three deliberate
breaks: "Genuinely, what the fuck." "Space monkeys on a hurtling rock." "That
PDF has the resilience of a wet napkin." → What-NOT-to-change entry, capped.

**Claim-shaped headings** ("The demo is the easy part", "A brand system
should behave like jazz") and an ending on the meaning before credits —
edicts 7 and 12 done exactly.

**Not house style.** Seven numbers in the piece, one of them evidence; the
only concrete proof (a 48-hour launch) arrives in the closing testimony
(edicts 2, 8); the failure section lists generic tool failures, none
measured on Ramp's own system (edict 9); the noun catalog is re-enumerated
until it is filler (→ edict 16); system, judgment, taste, and coherence
carry the argument undefined.

**What the pair teaches together.** Both use the short sentence as a job —
refrain, thesis, punchline, rebuttal, turn — where the skill had treated it
only as a rhythm reset. Both are also what the house style is built to
resist: beautiful cadence over thin evidence. Edicts 8 and 9 are what let
the studio sound like this without arguing like this.
