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
