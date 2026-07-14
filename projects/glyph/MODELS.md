# glyph — released models

One release per version, singular on purpose: the studio ships ONE
glyph-nanogpt per round (the generalist), with the 26-specialist case from
experiment 09 standing as the frozen, unreleased yardstick it is trying to
overtake. Version history:

| Version | Date | What it is | Yardstick gap at release |
|---|---|---|---|
| [`glyph-nanogpt-1`](models/glyph-nanogpt-1/) | 2026-07-14 | omni-xl — 47.8M letter-conditioned generalist, 12L/8H/576E, one-char-per-token outline codec (ADR-0027) | wins mean BPC (1.490 vs 1.521) but draws valid glyphs 71.0% vs the case's 92.1% at temp 1.0 |

The gap to close, stated so no future version can dodge it: **valid-glyph
rate at the case's 92.1%, without giving back the BPC lead.**
