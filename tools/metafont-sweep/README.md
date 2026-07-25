# metafont-sweep — a corpus made of parameter settings

*Turns the knobs on Knuth's Computer Modern and measures what that corpus is worth against real type families.*

Generate a corpus of letterforms by sweeping Metafont parameters, encode it
with glyph's codec, and compare it to 733 open-licensed families.

Built for [You can't parameterize a
disagreement](../../research-docs/reports/cant-parameterize-a-disagreement.md).
The numbers in that note come from `results/`, which is committed; the corpora
themselves regenerate and are gitignored (ADR-0002).

## What it does

A Computer Modern parameter file (`cmss10.mf`, `cmr10.mf`) is 63 named values,
46 of them dimensions, followed by `generate roman`. `sweep.py` parses them,
perturbs a
subset, writes one `.mf` per setting, compiles each through `mf2pt1`
(Metafont → MetaPost → Type 1), and encodes the lowercase glyphs with
**glyph's own codec** — same 127-character alphabet, same 16-unit grid, same
overlap removal, same `decode_glyph` validity gate. The output is therefore
byte-comparable with `projects/glyph/data/corpus/`.

Two sweep modes:

| mode | what moves | analogue |
|---|---|---|
| `axes` | four coordinated multipliers — weight, width, x-height, slant | a variable font's axes |
| `indep` | 44 knobs independently — 37 dimensions, 4 scalars, 3 booleans | "62 knobs", if the knobs were independent |

`swroman.mf` is a lowercase-only driver — Knuth's `roman.mf` minus majuscules,
numerals, punctuation, accents, and ligature tables. Nothing the corpus sees
changes; it just cuts each compile from 128 characters to 26.

## Requirements

A TeX distribution providing `mf`, `mpost`, `mf2pt1`, `t1asm`, and the `cm`
sources. TinyTeX is enough:

```bash
curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh
~/Library/TinyTeX/bin/*/tlmgr install metapost mf2pt1 t1utils cm
```

`sweep.py` finds the sources via `kpsewhich`; override with `CM_SOURCE`, and
point `TEXBIN` at the binaries if they aren't in the default TinyTeX location.
FontForge is optional — without it Type 1 output is unhinted, which does not
affect outlines.

## Run it

```bash
# generate (writes mf_corpus/<base>-<mode>/<letter>.txt + sweep-stats.json)
uv run python tools/metafont-sweep/sweep.py --base cmss10 --mode axes  --n 500
uv run python tools/metafont-sweep/sweep.py --base cmss10 --mode indep --n 500
uv run python tools/metafont-sweep/sweep.py --base cmr10  --mode indep --n 500
uv run python tools/metafont-sweep/sweep.py --base cmss10 --mode axes --n 3000 \
    --seed 4242 --out tools/metafont-sweep/mf_big

# measure
uv run python tools/metafont-sweep/control.py  a e g n o s   # the headline
uv run python tools/metafont-sweep/scale.py    a e n o       # does more sampling help?
uv run python tools/metafont-sweep/saturate.py a e g n o s   # marginal cost per glyph
```

Compiles run about 0.65s each across 8–10 workers; 3,000 settings take two
minutes.

## The measurements

`variety.py` holds the shared primitives: a numpy scanline rasterizer (even-odd
fill, matching the codec's documented fill rule), PCA, and the subspace-span
calculation. Rasterization is deliberately **un-normalized** — x-height and
stem weight are exactly what a parameter sweep varies, so scaling them away
would erase the thing under test.

| script | measures | in the note |
|---|---|---|
| `control.py` | reach into held-out real families, every arm fitted on equal samples | yes — the headline table |
| `scale.py` | whether 6× more sweep points buys more reach | yes |
| `saturate.py` | marginal compressed bytes per added glyph (lzma, 64MB dictionary) | yes |
| `compare.py` | first pass: component counts, gzip saturation, in-sample span | superseded |
| `checks.py` | the controls that disqualified two of those measures | as a negative result |

**Two measures were disqualified and are kept here as the record.** Counting
principal components can't count knobs: the `axes` arm has exactly four by
construction and still needs 62 components to reach 95% of its pixel-space
variance, so the measure tracks how far shapes move, not how many things moved
them. And gzip can't see across samples in a corpus this size — a 32KB window
against a 33KB corpus measures within-glyph redundancy only, which is why
`saturate.py` uses lzma with a 64MB dictionary instead.

**One caveat that survives.** Span is a linear measure and a parameter family
is a nonlinear manifold, so reach is understated. `control.py` applies the same
linear measure to directions fitted on real families, which is the comparison
the note relies on rather than any absolute number.
