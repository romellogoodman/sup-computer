# dataviz — the studio chart pipeline

A small, dependency-free chart generator that renders the project's results as
**self-contained HTML files** (inline SVG, system fonts — no network at view
time, no webfont, no JS libraries).

**This is the single source of every chart in the repo.** All charts — in the
[README](../../projects/shakespeare/README.md), the [model cards](../../research-docs/model-cards/), the
[experiment reports](../../research-docs/reports/), and the [leaderboard](../../projects/shakespeare/leaderboard.md) —
are generated here. Don't hand-author chart SVGs or use other charting tools;
add the chart to [`build.py`](build.py) and regenerate. See the project
[`CLAUDE.md`](../../projects/shakespeare/CLAUDE.md) for the standing rule.

It's part of this monorepo: the training engine lives in [`core/`](../../core/), and this
subdirectory turns the numbers in [`leaderboard.md`](../../projects/shakespeare/leaderboard.md)
and [`README.md`](../../projects/shakespeare/README.md) into charts for the write-up / blog post.

## Design system — the studio document style

The visual language **matches the studio website's refined "Prof. Dr." style**
([ADR-0017](../../docs/adr/0017-website-redesign-refined-prof-style.md)) so charts
read as native to the reports they sit in
([ADR-0018](../../docs/adr/0018-dataviz-matches-the-website.md)). We keep the
*engineering* approach (self-contained SVG, nice-axis ticks, a vertical layout
stack); the visual tokens mirror the site:

- **system fonts** — a serif for titles, monospace for axes/ticks/data labels
  (no embedded webfont).
- headings at weight 700; **no corner radius** (flat, stark frame).
- one green accent; ink + grays carry the rest; **muted red = regression**.
- light + dark themes use the website's exact `--color-*` token values.

Tokens live in [`designsystem/tokens.py`](designsystem/tokens.py).

## Layout

```
dataviz.py              # renderer: bar() + line() + HTML wrapper
designsystem/tokens.py  # colors, type, spacing (light + dark) — mirror the site
build.py                # the report charts, defined from the repo's data
output/                 # generated self-contained .html (one per chart × mode)
```

## Build

```bash
cd tools/dataviz
python3 build.py            # all charts, light + dark -> HTML + PNG
python3 build.py --light    # light only
python3 build.py --dark     # dark only
python3 build.py --no-png   # HTML only (skip the PNG export)
```

`build.py` writes self-contained HTML to `output/` and then exports light/dark
PNGs straight into [`../../research-docs/reports/assets/`](../../research-docs/reports/assets/) (`exp01-<chart>.<mode>.png`)
for the Markdown report. The renderer itself is pure Python 3 stdlib; the PNG step
shells out to headless Chrome (override the binary with `DATAVIZ_CHROME`, or pass
`--no-png` to skip it — the HTML still builds either way).

### Charts produced

| File | What it shows |
|------|---------------|
| `bpc-by-round` | Test BPC across baseline + 4 research rounds (the 20% drop; R4 regression) |
| `data-win` | Round 1: held-out BPC, 1MB control vs 5MB full (more data alone) |
| `bpe-overfit` | Round 3: train vs val loss — BPE overfits, best-val checkpoint kept |
| `researcher-efficiency` | ΔBPC per 100K Claude tokens per round (diminishing returns) |
| `training-loss` | Baseline validation loss descending 4.28 → 1.46 |

These are also exported as light/dark PNGs into [`../../research-docs/reports/assets/`](../../research-docs/reports/assets/)
(named `exp01-<chart>.<mode>.png`) and embedded in [Experiment 01](../../research-docs/reports/improve-a-small-model.md)
via `<picture>` so they follow the reader's color scheme.

Open any `output/*.html` in a browser, or copy the inner `<svg>` for static embeds.

## Use it for your own data

```python
import dataviz as dv

dv.write(dv.bar({
    "title": "My chart",
    "subtitle": "optional",
    "categories": ["A", "B", "C"],
    "values": [1.2, 3.4, 2.1],
    "colors": ["blue", "green", "red"],   # hue names from tokens.py; optional
    "valueFmt": "{:.1f}",
    "yTitle": "Score", "xTitle": "Group",
    "caption": "optional source note",
}, mode="light"), "output/my-chart.light.html")
```

`line()` takes `x` + `series=[{"name","y","hue"}]` instead of
`categories`/`values`. Bars support negative values (they draw below a zero
baseline). PNG export is handled by `build.py` (it auto-sizes the screenshot
from each chart's viewBox); to render a one-off by hand, point headless Chrome
at the HTML:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
  --screenshot=output/my-chart.png --window-size=1008,800 file://$PWD/output/my-chart.light.html
```
