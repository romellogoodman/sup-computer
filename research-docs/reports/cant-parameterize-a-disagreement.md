---
title: "You can't parameterize a disagreement"
type: note
researcher: claude-opus-5
date: 2026-07-25T14:35:36-04:00
summary: >
  Three thousand fonts generated from Knuth's own Computer Modern source cover
  no more of real type design than five hundred did — the ceiling is set by the
  program, not by the sample count. A third to a half of independently-set
  parameter combinations won't compile at all, and one boolean, the
  single-storey g, is worth more coverage than every continuous dial combined.
takeaways:
  - >-
    Metafont's premise, made concrete: 3,000 settings of Knuth's `cmss10.mf`
    compiled to 2,972 fonts in two minutes, encoded through glyph's codec so
    they are byte-comparable with 733 real families.
  - >-
    Six times the sampling bought nothing. Reach into real design space moved
    from 68.4% to 68.7% on `a` — the corpus's information is **capped by the
    parameterization**, not by how many draws you take from it.
  - >-
    Meanwhile each added font got cheaper to describe (marginal cost 0.104 →
    0.080 of raw size, against 0.132 for real families). More samples, more
    redundancy, no more coverage.
  - >-
    Coordinated knobs compile at 99.6%; independent knobs at 66.4% off the
    sans anchor and 41.4% off the serif one. Variety and yield trade against
    each other.
  - >-
    A single-storey `g` cannot be turned into a double-storey one. Knuth
    handled it with a boolean he wrote because he already knew both existed —
    which is the whole finding in miniature.
status: published
---

# You can't parameterize a disagreement

Metafont's premise is that a typeface is a program with knobs on it: write the
letter once as equations, expose the values — pen width, x-height, slant — and
a whole family falls out of turning them. Three thousand settings of Knuth's
own Computer Modern source say the corpus this produces is capped by the
program rather than by the sample count: six times the sampling bought under
two points of additional coverage.

That is a claim about training data, not about type. The studio keeps asking
what makes a corpus worth training on, and the usual answer — more of it — is
measurable here in a way it usually isn't, because for once every decision
that produced the data is written down in a file you can read.

## The sweep is Knuth's program, not an imitation of it

A Computer Modern parameter file is 63 named values — 46 of them dimensions —
followed by `generate roman`. `cmss10.mf` differs from `cmr10.mf` mostly in
numbers and one line, `serifs:=false`, which is the meta-font claim stated as
source code: Computer Modern Sans is Computer Modern Roman with the serifs
switched off.

So the sweep parses those values, perturbs a subset, writes one `.mf` per
setting, and compiles each through `mf2pt1`. What comes out is encoded with
[glyph's own codec](../../docs/adr/0027-glyph-one-char-per-token-outline-codec.md)
— same 127-character alphabet, same 16-unit grid, same overlap removal, same
strict re-parse the model's output has to survive. Both corpora are then the
same kind of object, produced by the same code on the same afternoon. Nothing
in the comparison is a pipeline artifact.

The comparison corpus is glyph's: 759 open-licensed sans-serif families, of
which 733 contain a lowercase `a`, sampled one glyph per family so a designer
counts once rather than once per weight.

Two sweep modes, because the interesting question is which kind of knob-turning
you mean:

| mode | what moves | analogue |
|---|---|---|
| `axes` | four coordinated multipliers — weight, width, x-height, slant | a variable font's axes |
| `indep` | 44 knobs independently — 37 dimensions, 4 scalars, 3 booleans | every knob, if the knobs were independent |

## Six times the sampling, none of the coverage

Take the directions of variation a corpus contains, keep the strongest 64, and
ask what fraction of 733 real families' variation falls inside that span. Call
it reach; real families are always out-of-sample for a sweep, since its
directions are fitted only on generated fonts. Fit on 498 of them, then on
2,972, and see whether the extra 2,474 bought anything.

| letter | reach, 498 settings | reach, 2,972 settings |
|---|---|---|
| a | 68.4% | 68.7% |
| e | 74.8% | 76.7% |
| n | 81.4% | 83.0% |
| o | 78.6% | 80.4% |

Nothing moved. Everything the sweep can produce was decided when the program
was written, so drawing more samples enumerates that space more finely without
enlarging it — the fonts land between fonts you already had.

The compression numbers say the same thing from the other side. Measured as
marginal compressed bytes per added glyph, normalized by raw size, the sweep
gets *cheaper* as it grows — 0.104 at 498 settings, 0.080 at 2,972 — while 733
real families sit at 0.132. **A generated corpus can grow indefinitely while
its information saturates**, and the saturation shows up as redundancy long
before it shows up as anything a loss curve would flag.

## The knobs are not independent, and a third to a half of settings break

Turn the knobs together and almost everything works. Turn them apart and
Metafont starts refusing:

| sweep | settings requested | usable fonts | yield |
|---|---|---|---|
| `cmss10`, coordinated axes | 3,000 | 2,972 | 99.1% |
| `cmss10`, independent | 500 | 332 | 66.4% |
| `cmr10`, independent | 500 | 207 | 41.4% |

The failures are real Metafont errors — strokes that collide, paths that can't
be resolved — not a harness problem; of the 293 settings the serif anchor lost,
275 failed to compile at all. Knuth's parameters aren't independent
dials; they're a set of values that hold together in the regions he tested, and
pushing them apart makes letters that don't close. The serif anchor breaks
worse than the sans one, which is what you'd expect from a design with more
constraints to violate.

So the variety you want is the variety the system won't give you. Coordinated
knobs yield a smooth, near-complete family that covers less; independent knobs
cover more and cost you between a third and three-fifths of the corpus.

## Some differences aren't on a dial at all

Here is the whole argument in one letter. Every arm was fitted on an equal 207
samples and scored on 367 held-out families, so the columns are comparable:

| letter | real families | `axes` | `indep` | `cmr10 indep` |
|---|---|---|---|---|
| a | 83.3% | 64.5% | 70.5% | 61.1% |
| e | 83.4% | 71.0% | 76.9% | 66.9% |
| **g** | 80.5% | 39.8% | 70.6% | 64.1% |
| n | 90.0% | 78.3% | 80.2% | 66.0% |
| o | 86.8% | 76.5% | 80.9% | 76.1% |
| s | 83.1% | 70.2% | 73.5% | 57.9% |

Every letter shows the same gap — directions fitted on real families reach into
held-out real families better than directions fitted on Computer Modern do. But
`g` collapses. The coordinated sweep reaches 39.8% where it manages 64–78%
everywhere else, and the reason is that Computer Modern Sans draws a
single-storey `g`. A double-storey `g` is a different idea, not a different
setting, and no amount of continuous knob-turning crosses between them.

The independent sweep recovers to 70.6% because it flips `variant_g` — a
boolean. Knuth wrote that switch because he already knew both kinds of `g`
existed. That is the finding in miniature: the parameter space contains exactly
the disagreements its author had already had.

## What the measurement can't tell you

Two measures failed and are worth stating as failures.

**Counting principal components cannot count knobs.** The `axes` arm has
exactly four by construction and still needs 62 components to reach 95% of its
variance in pixel space, because the measure tracks how far shapes move rather
than how many things moved them. Any conclusion resting on component counts —
including the tempting one that a parametric corpus is "low-dimensional" — is
unsupported by this experiment.

**gzip cannot see across samples at this size.** A 32KB window against a 33KB
corpus measures redundancy within a glyph, not between glyphs, which is why the
first pass showed generated corpora compressing *worse* than real ones. The
saturation numbers above use lzma with a 64MB dictionary instead.

Three limits on what's here. Reach is a linear measure and a parameter family
is a nonlinear manifold, so every absolute number understates — the comparison
holds because the same linear measure is applied to directions fitted on real
families, but the gap's size is not to be read literally. The perturbation
ranges are mine, anchored on Knuth's values but chosen by me, and a different
choice moves the yield table. And this is a floor rather than a ceiling:
Metafont can branch on its parameters, `variant_g` proves branches do real
work, and a generator with more branches would get further.

That last limit is the one that matters, and it doesn't rescue the idea so much
as relocate it. Every branch is a decision made in advance. To reach 733
designers' worth of variety you would have to anticipate 733 designers' worth
of ideas, which is the labor of having them, not a shortcut around it.

## What this says about a corpus

A corpus is worth the number of independent decisions inside it, and sample
count measures that badly. You can generate unbounded data carrying almost no
new information — that's what 2,972 fonts covering no more ground than 498
means — and the failure is invisible from the outside, because the files are
real, well-formed, and varied-looking.

The studio has already run both ends of this axis without naming it.
[kenosha-kid](dream-a-single-phrase.md) trains on permutations of six words,
one source, enumerable exactly — and it's the right call there, because the gap
between enumeration and learning is the object of study. [glyph](one-model-or-twenty-six.md)
trains on 759 families whose designers never consulted each other. And
[gatsby's second round](mixture-of-models.md) found the same thing this note
found, from the other direction: one local model writing the corpus wasn't
enough, four in a designed blend was. That was buying independence, and calling
it a mixture.

Which reframes the question to ask of any generated corpus, synthetic data
included: not how much of it there is, but how many separate decisions it can
possibly contain. A model trained on Computer Modern's parameter space could
learn that space exactly and still never have seen anyone disagree about what a
letter is.

## Reproduce it

Requires a TeX distribution with `mf`, `mpost`, `mf2pt1`, `t1asm`, and the `cm`
sources; setup is in [the tool's README](https://github.com/romellogoodman/sup-computer/tree/main/tools/metafont-sweep).

```bash
# generate: 3,000 coordinated settings, then the independent sweeps
uv run python tools/metafont-sweep/sweep.py --base cmss10 --mode axes --n 3000 \
    --seed 4242 --out tools/metafont-sweep/mf_big
uv run python tools/metafont-sweep/sweep.py --base cmss10 --mode indep --n 500
uv run python tools/metafont-sweep/sweep.py --base cmr10  --mode indep --n 500

# measure
uv run python tools/metafont-sweep/control.py  a e g n o s   # the reach table
uv run python tools/metafont-sweep/scale.py    a e n o       # 498 vs 2,972
uv run python tools/metafont-sweep/saturate.py a e g n o s   # marginal cost
```

Committed measurements: [`tools/metafont-sweep/results/`](https://github.com/romellogoodman/sup-computer/tree/main/tools/metafont-sweep/results).
The generated corpora are not in the tree and regenerate in about two minutes
(ADR-0002).

## Credits

Metafont and Computer Modern are Donald Knuth's, 1979–1985; this note only
turns their knobs. The comparison corpus is glyph's, from
[experiment 09](one-model-or-twenty-six.md).

The idea came out of a conversation rather than the backlog: a chat about
whether to retrain glyph on Metafont output, where the answer turned out to be
that the interesting question wasn't about glyph at all. Machine-proposed,
human-sequenced — the experiment ran because Romello asked for the measurement
instead of the argument.
