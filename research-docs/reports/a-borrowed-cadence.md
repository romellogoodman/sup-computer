---
title: "A borrowed cadence: where the house style comes from"
type: note
researcher: claude-fable-5
date: 2026-07-04T01:49:12-04:00
summary: >
  The studio writes to a rulebook — twelve editing operations encoded as a
  skill, distilled from Anthropic's research posts, Thoughtful Lab, and Ramp
  Labs, piloted on two files and then swept across the studio: nine model
  cards, ten docs, and the website's visitor copy, 130-odd edits in all. The
  pilot's diagnosis held at scale — the studio's biggest tic was emphasis
  overload, and the sweep removed bolded lines over reintroducing them at
  roughly four to one.
status: published
---

# A borrowed cadence: where the house style comes from

The studio now writes to a rulebook. It lives at
[`.claude/skills/house-style/`](https://github.com/romellogoodman/sup-computer/tree/main/.claude/skills/house-style)
as twelve editing operations — openings, emphasis, rhythm, hedging, endings —
each with a before/after pair taken from real studio prose. It was not
invented. It was borrowed, from three places that write about technical work
in ways worth stealing, then proven on two files before it was allowed to
touch the rest.

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

**The pilot.** Before any sweep, the skill was applied to exactly two files —
one model card, one README. Nineteen edits; fourteen were on a single rule,
the **bold budget**. Studio prose was bolding three phrases per takeaway
bullet where the exemplars bold almost nothing, teaching the reader's eye to
skim past emphasis entirely. The pilot also caught the skill being wrong once
— applied literally, the bold budget would have stripped table row labels and
term coinage — so the rule gained a structural-bold exemption before it ever
saw a third file. A rule that survives contact with real prose is worth more
than a rule that reads well.

**The sweep.** With the exemption in place, the skill ran across the studio
the same day: the other nine model cards (70 edits), ten READMEs and project
docs (42 edits), and the website's visitor copy. The pilot's diagnosis held at
scale — across the sweep commits, lines carrying bold were removed over
reintroduced at roughly four to one. What the sweep did not touch, by the
skill's own scope rule, is the published reports: their prose froze at
publication, and a style pass has no standing to reopen them.

Just as important is what the skill refuses to touch anywhere. The question
titles, the takeaways block at the top, the honesty sections, cost-as-data,
the evocative recurring nouns — the dream, the dial, the green light — are the
studio's own, and the skill marks them protected. The cadence is borrowed; the
voice is not.

## Credits

- Style analysis and skill: Claude Fable 5, from eight exemplar pieces across
  the three sources and three pieces of studio prose.
- Sources: Anthropic research, Thoughtful Lab, Ramp Labs — read, quoted
  briefly, and argued with in
  [`references/style-analysis.md`](https://github.com/romellogoodman/sup-computer/blob/main/.claude/skills/house-style/references/style-analysis.md).
