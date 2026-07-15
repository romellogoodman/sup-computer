---
type: experiment
number: 6
title: "Can a model's own likelihood hear register?"
date: 2026-07-04T02:01:13-04:00
series: linewell
researcher: claude-fable-5
models: [shakespeare-nanogpt-3]
summary: "The shakespeare model's own likelihood is register-blind: fluent Gutenberg editorial prose scores inside any NLL band that admits verse, and the model's most inevitable text is the junk — footnotes, [Illustration] tags, speaker lists at 1.2–1.8 NLL — so the band's raised floor, not its ceiling, is the load-bearing edge. An LLM judge riding the same steer layer held verse register where the band drifted into publication history."
status: published
---
[← all reports](README.md) · series: linewell · evidence `2026-07-04-first-draws` · July 2026

# Can a model's own likelihood hear register?

[linewell](../../tools/linewell/README.md) composes poems one line at a
time out of a frozen small model — here
`shakespeare-nanogpt-3` — with a pluggable judge deciding whether each
candidate freezes into the poem or goes back down the well. The
cheapest possible judge — the model itself, accepting any line whose
mean NLL/token lands in a band bracketing real verse, surprising but
not garbled — turns out to be register-blind: editorial prose scores
like verse, and the model's most inevitable text isn't verse at all.
Accepted lines are immutable; the harness can only append. This round
calibrated that band against held-out verse, drew the first two poems,
and found out exactly what a likelihood band can and cannot hear.

<div class="takeaways">
<p class="takeaways-label">Key takeaways</p>
<ul>
<li><strong>The model's own likelihood cannot hear register.</strong> Real held-out verse spans ≈2.3–3.3 mean NLL/token (p10–p90 of 25 King Lear lines). Fluent Gutenberg editorial prose — publication dates, quarto collations — sits in the same range: 6 of 8 hand-picked editorial lines fall inside the [2.0, 4.0] band used for the first draw, and 5 of 8 inside even the tighter recalibrated [2.3, 3.5]. A band judge structurally cannot prevent drift into scholarly apparatus.</li>
<li>The counterintuitive part: <strong>the lowest-NLL text is the junk.</strong> Footnotes, <code>[Illustration]</code> tags, and bare speaker lists score 1.20–1.81 — the model's most inevitable text is Gutenberg apparatus, not verse. So the band's raised floor is the load-bearing edge: it is the only thing standing between the poem and the model's favorite text.</li>
<li>The exhibits show both failure modes live. The band-judged poem drifted entirely into publication-history register within 12 queries — every accepted line is bibliography-speak, every rejected line fell <em>below</em> the floor. The LLM judge (olmo-3-7b as editor, over the same well) <strong>held verse register</strong>: it rejected precisely the low-NLL apparatus the likelihood loves and accepted a line the band's floor would have refused.</li>
<li>Small-n throughout: 25 verse lines, 30 sampled candidates, 8 editorial lines, two archived draws. This is a calibration note with teeth, not a benchmark.</li>
</ul>
</div>

## The well and the judge

The harness mechanics are in the
[linewell README](../../tools/linewell/README.md): the model is the only
source of text, each candidate is sampled with the poem-so-far as
prompt, and a judge — `band`, `llm`, or `human` — issues one verdict per
draw. Full provenance (every candidate, its NLL, the verdict) is written
per run, on the same instinct as Daydream's harness keeping illegal
moves: the rejects are part of the record.

The LLM judge rides [`tools/steer`](../../tools/steer/)
([ADR-0026](../../docs/adr/0026-steer-shared-orchestration-layer.md)) —
the same orchestration seam that drives
Token Chess (report in progress), pointed at the opposite
job: there the big model spends scarce tokens coaxing out the rare thing
the small model gets right; here it vetoes the frequent thing the small
model most wants to say.

## Calibrating the band — the floor, not the ceiling, does the work

The band premise fails inside this table: the editorial row's median
(2.69) sits square inside real verse's p10–p90. Three NLL
distributions, all under `shakespeare-nanogpt-3`'s own likelihood,
each line scored with its real preceding context
(`calib.py`, archived alongside the draws in
[`tools/linewell/evidence/2026-07-04-first-draws/`](../../tools/linewell/evidence/2026-07-04-first-draws/);
numbers below are from a verifying rerun, seed 1337, since the original
run's stdout wasn't archived):

| Distribution | n | min | p10 | median | p90 | max |
|---|---|---|---|---|---|---|
| Real verse (held-out *King Lear*) | 25 | 0.78 | 2.28 | 2.90 | 3.29 | 3.97 |
| Sampled candidates @ temp 0.9 | 20 | 1.20 | 1.41 | 2.00 | 2.58 | 2.88 |
| Sampled candidates @ temp 1.2 | 10 | 1.65 | 1.81 | 2.31 | 2.86 | 3.44 |
| Gutenberg editorial lines | 8 | 1.65 | 1.68 | 2.69 | 3.20 | 3.58 |


Two things are wrong with the naive band premise, and they point in
opposite directions.

**The ceiling barely matters.** Real verse's p10–p90 is ≈2.3–3.3 — but
the editorial distribution's median (2.69) sits *inside* it. Six of the
eight editorial lines land in the [2.0, 4.0] band the first draw used;
five of eight land even in the recalibrated [2.3, 3.5]. Lines like
*"we have adopted the reading of the quarto as being most probably"*
are fluent, mid-probability prose to this model — exactly as surprising
as verse, to a judge that can only measure surprise. **No band that
admits verse excludes the scholarly apparatus.** Register is not a
likelihood phenomenon at this model scale.

**The floor is everything.** The model's *lowest*-NLL text — its most
inevitable, most confident output — is not its best verse. It is the
junk: `[Footnote 33: by] So the 4to.--The 4to "live."]` at 1.20,
`[Illustration]` at 1.34, an entrance-list of mismatched character names
at 1.41, footnote after footnote through 1.81. The training corpus's
Gutenberg apparatus is rigid, formulaic, endlessly repeated — the
easiest thing in the corpus to predict, and therefore the strongest
attractor in the well. Even the held-out *verse* sample obeys the pull: its
single most predictable line, `Attendants.` at 0.78, is a cast-list
fragment — apparatus-shaped. The band's floor at 2.3 is the only edge
doing real work: everything below it is, almost without exception, the
model reciting its scaffolding.

## Exhibit A: the band drifts (poem-band.json)

The first archived draw (`--judge band`, band [2.0, 4.0], seed
`  ROMEO:`, 12 queries, backed by
[`poem-band.json`](../../tools/linewell/evidence/2026-07-04-first-draws/poem-band.json))
completed its 8 lines, and every one of them is publication-history
register:

```
  ROMEO:
CRUDE CROARTO, &c.--_The Second portractices
of the portion of the Second Servant of Eld ”
The First Part of Troy is finishly to the last. The play
of the torturing tree (that the Second Part of Paris, a book
afterward female, it is a condition of 1200, but, in which
it was published in 1638, that in the suphragent belonging _The
disguised venomousy of_ to the refusement of J. Man in 1615.
```

The provenance is the diagnosis. All seven accepted candidates scored
2.05–2.35 — inside the band, all bibliography-speak. All five rejected
candidates scored 1.88–1.99 — rejected *below the floor*, not above the
ceiling. The judge never once refused a line for being un-verse-like;
it only ever refused lines for being too predictable. What it accepted
was the fluent upper crust of the same apparatus register. Once the
first bibliographic line froze into the immutable poem, the context
itself pulled every subsequent draw toward more of the same. Drift
compounds, because the harness can only append.

Under the recalibrated [2.3, 3.5] floor, five of these seven accepted
lines would have been refused — the raised floor is a real repair. But
the editorial table above says it is a partial one: 5 of 8 editorial
lines still clear 2.3. The floor filters the model's *confident* junk;
nothing in the band can filter its *fluent* junk.

## Exhibit B: the LLM judge holds (poem-llm.json)

The second draw (`--judge llm`, olmo-3-7b-instruct as editor via
`steer`, same seed, 25 queries, backed by
[`poem-llm.json`](../../tools/linewell/evidence/2026-07-04-first-draws/poem-llm.json))
did not finish its 8 lines, but what it kept is verse:

```
  ROMEO:
Repent on this letter, that will I find
The damned mathemist.
POLONIUS.
You shall not come;
The captain waits the city’s spoil;
```

The rejects are the point. Among the twenty rejected candidates are
`[Illustration]` at NLL 1.34 and a `[Footnote 205: ...]` fragment at
1.48 — precisely the lowest-likelihood-of-surprise, highest-attraction
apparatus that Exhibit A's register shows the well keeps offering. The
LLM judge threw both back without ceremony. And it accepted
*"The damned mathemist."* at NLL 1.99 — **below** the calibrated band's
floor. It judged register directly, where the band can only judge
surprise: the two judges disagree in both directions, and the LLM is
right both times.

(One accepted line is arguable: `POLONIUS.` is a speaker tag — verse
*drama* furniture rather than Gutenberg apparatus. The editor treating
it as a legitimate dramatic turn is defensible; a stricter lyric brief
would refuse it. Judge briefs are a dial this harness hasn't swept yet.)

The cost of taste: 25 queries for 5 accepted lines, versus the band's
12 queries for 7 — the LLM judge is roughly twice as selective per
query, plus an inference call per verdict.

## The poisoned draw

One earlier LLM-judged run — observed during harness bring-up, before
provenance archiving was in place, so it is *not* backed by a JSON in
the evidence folder — showed the failure mode that makes the immutable-
append constraint dangerous. The editor accepted a footnote fragment,
`[3] See London.]`, early in the poem. With apparatus frozen into the
context, the well's subsequent draws skewed even harder toward
apparatus — the same compounding drift as Exhibit A, now on the LLM
judge's watch — and the run then went 24 consecutive draws without a
single acceptance before being stopped: the judge, correctly refusing
the junk its own earlier mistake was now eliciting, could no longer
find a verse line in the poisoned well. One bad accept doesn't cost one
line; it re-aims the model. The two archived runs (`poem-band.json`,
`poem-llm.json`) are the reproducible exhibits; this one is reported as
observed, and re-running it under archiving is on the list.

## Limitations

- **Small n everywhere**: 25 verse lines, 30 sampled candidates, 8
  hand-picked editorial lines, two archived draws plus one observed
  failure. Directions, not estimates.
- **The calibration stdout wasn't archived** — the distribution table
  above is a verifying rerun (`calib.py`, seed 1337; the deterministic
  NLL scores reproduce exactly, the sampled lines reproduce under the
  seed). Note that the archived `calib.py` predates `compose.py`'s move
  from `projects/shakespeare/` to `tools/linewell/` and needs its import
  path pointed at the new location to run.
- **One model in the well, one editor.** Whether the register-blindness
  band structure holds for the studio's other text models (gatsby,
  kenosha-kid), or whether a different local editor holds register as
  well as olmo did, is untested.
- **The LLM judge's win is qualitative** — two poems and a rejection
  ledger, not a scored evaluation of verse quality.

## How to reproduce

From the repo root:

```bash
# the band draw (Exhibit A used --band_lo 2.0 --band_hi 4.0, pre-calibration)
uv run --with tokenizers python tools/linewell/compose.py \
    --judge band --lines 8 --start "  ROMEO:" --out poem-band.json

# the LLM draw (LM Studio serving olmo-3-7b-instruct; STEER_BASE_URL overrides)
uv run --with tokenizers python tools/linewell/compose.py \
    --judge llm --lines 8 --start "  ROMEO:" --out poem-llm.json
```

The band defaults are now the calibrated [2.3, 3.5]; the calibration
itself reruns from the archived
[`calib.py`](../../tools/linewell/evidence/2026-07-04-first-draws/calib.py)
(see the import-path caveat above).

## Kin

Same seam, opposite duty:
Token Chess (report in progress) puts an LLM on the other
side of [`steer`](../../tools/steer/) to *extract* the rare correct
output from a small model under a token budget; linewell puts one there
to *refuse* the small model's most probable output in defense of a
register. Between them they bracket what the studio means by steering.

## Credits

- `shakespeare-nanogpt-3` — the well.
- `olmo-3-7b-instruct` (Ai2), served locally by LM Studio — the editor.
- Project Gutenberg — the corpus, apparatus and all; the apparatus turned out to be the experiment.
- Composed and analyzed with Claude ([Claude Code](https://claude.com/claude-code)).
