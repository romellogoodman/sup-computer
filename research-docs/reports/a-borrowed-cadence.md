---
title: "A borrowed cadence: where the house style comes from"
type: note
researcher: claude-fable-5
date: 2026-07-04
summary: >
  The studio now has a written house style — twelve editing operations encoded
  as a skill, distilled from Anthropic's research posts, Thoughtful Lab, and
  Ramp Labs. A two-file pilot found the studio's biggest tic immediately:
  fourteen of seventeen edits on one model card were emphasis removal.
---

# A borrowed cadence: where the house style comes from

The studio now writes to a rulebook. It lives at
[`.claude/skills/house-style/`](https://github.com/romellogoodman/sup-computer/tree/main/.claude/skills/house-style)
as twelve editing operations — openings, emphasis, rhythm, hedging, endings —
each with a before/after pair taken from real studio prose. It was not
invented. It was borrowed, from three places that write about technical work
in ways worth stealing.

**The sources.** [Anthropic's research posts](https://www.anthropic.com/research)
supplied the calibration rules: raw counts stated unhedged, "roughly" reserved
for derived quantities, ambiguity handled as named alternative readings.
[Thoughtful Lab](https://www.thoughtfullab.com/) supplied the openings — its
essays land the object and the verdict in the first two sentences, no
throat-clearing about which experiment this is.
[Ramp Labs' SWE-bench page](https://labs.ramp.com/swebench) supplied the
reference-page register: noun-label headings, definition-first sections, and a
privacy/limitations section that states constraints without apology. The
sources disagree with each other — on headings, on openings, on endings — and
the skill records each adjudication rather than pretending they align.

**What the pilot found.** Applied to one model card and one README, the skill
made 19 edits; 14 were on a single rule, the **bold budget**. Studio prose was
bolding three phrases per takeaway bullet where the exemplars bold almost
nothing, teaching the reader's eye to skim past emphasis entirely. The pilot
also caught the skill being wrong once — applied literally, the bold budget
would have stripped table row labels and term coinage — so the rule gained a
structural-bold exemption before it ever swept the site. A rule that survives
contact with real prose is worth more than a rule that reads well.

Just as important is what the skill refuses to touch. The question titles, the
takeaways block at the top, the honesty sections, cost-as-data, the evocative
recurring nouns — the dream, the dial, the green light — are the studio's own,
and the skill marks them protected. The cadence is borrowed; the voice is not.

## Credits

- Style analysis and skill: Claude Fable 5, from eight exemplar pieces across
  the three sources and three pieces of studio prose.
- Sources: Anthropic research, Thoughtful Lab, Ramp Labs — read, quoted
  briefly, and argued with in
  [`references/style-analysis.md`](https://github.com/romellogoodman/sup-computer/blob/main/.claude/skills/house-style/references/style-analysis.md).
