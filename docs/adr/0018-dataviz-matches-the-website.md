# ADR 0018: dataviz matches the website's document style

- **Status:** Accepted
- **Date:** 2026-06-29
- **Deciders:** Romello Goodman (with Claude)

## Context

The chart pipeline (`tools/dataviz`) rendered figures in a design system derived
from Vercel Geist: the Geist Sans webfont (embedded as base64), weight-600 headings
with negative tracking, a 6px corner radius, and Geist accent ramps (blue default,
green = success, red = regression), in light + dark.

The website was then redesigned around a refined "Prof. Dr." document style
([ADR-0017](0017-website-redesign-refined-prof-style.md)): system serif + monospace
(no webfont), a stark frame (no radius, hairline rules), a single green accent on
ink + grays, and a `--color-*` token system with a one-place dark-mode swap. The
charts embed into those reports via `<picture>`, so the Geist look now clashed with
the page around it — a different typeface, rounded bars, and a brighter accent palette
sitting inside an austere serif document.

## Decision

Re-skin the dataviz design system to **match the website**, dropping the Vercel
Geist basis. The renderer's engineering is unchanged (pure-stdlib, self-contained
HTML + inline SVG, nice-axis ticks, vertical layout stack); only the visual tokens
change, in `designsystem/tokens.py`:

- **System fonts, no webfont.** A serif (Charter → Georgia) for titles/subtitles;
  monospace for axis titles, ticks, data labels, captions, and the tooltip — the
  site's serif-for-reading / mono-for-data split. The embedded Geist-Variable.woff2
  and its base64 are deleted; headless-Chrome PNG export uses system fonts.
- **Stark frame.** `RADIUS = 0` (flat bars); hairline gridlines; charts paint the
  page's own surface color so they read as native to the document.
- **One green accent on ink.** The default data hue is now **ink** (the link-blue is
  a UI color, not a data color), the accent is the **studio green**, secondary series
  are gray, and a **muted red** is retained for regression/error semantics (one
  report's figure and alt text rely on "v2 (red) vs v3 (green)"). The hue *keys*
  (`blue`, `green`, `red`, `neutral`, …) are kept so `build.py` is unchanged; only
  their values are retoned.
- **Shared tokens.** `LIGHT`/`DARK` use the website's exact `--color-*` values, so a
  chart's light/dark variants line up with the page in either color scheme.
  *(Clarification, June 2026: "exact" covers the structural tokens — surface,
  text, grid, accent green — which map 1:1 to named `--color-*` variables. The
  categorical data hues (amber/teal/purple/pink, ink-blue, muted red) are
  chart-specific; the site has no chart palette to mirror. `tokens.py` comments
  name each mirrored source variable so the two stay in sync.)*

All committed report figures were **regenerated** (`python build.py`) so existing
reports show the new style.

## Consequences

- Charts and prose now share one visual language; a figure no longer looks pasted in
  from another system.
- Smaller, simpler pipeline: ~130KB of font assets gone, no `@font-face` base64 step.
- **Regenerating figures touches "frozen" reports** (the rendered PNGs under
  `research-docs/reports/assets/`). This was a deliberate, human-directed cross-cutting
  restyle — the report *prose* is unchanged, only the figure rendering — analogous to
  the ADR-0015 standardization pass. The alt text stays valid because green/red
  semantics are preserved.
- The chart palette is now narrow (ink + green + grays + one red). A future chart that
  genuinely needs many categorical series will have fewer distinct hues; reach for
  shape/pattern or small multiples before adding colors back.
- Supersedes the dataviz-design portion of ADR-0009 (which described the charts as
  "a different visual language, Vercel Geist"); the rest of ADR-0009 (site IA) stands,
  and ADR-0017 already refined the site style this now matches.

## Alternatives considered

- **Keep Geist for charts.** Rejected: the whole point was that figures clashed with
  the redesigned page; a second design system is exactly what created the problem.
- **Mono + green only, drop red entirely.** Rejected: a report figure and its alt text
  distinguish two series as red vs green; dropping red would break that contrast and
  contradict the prose. A single muted red, used only for regression, fits the
  document tone without reopening a full categorical palette.
- **Leave old figures, restyle only new charts.** Rejected: mixed old/new figures in
  the same body would look worse than either alone; a clean regenerate is cheap.
