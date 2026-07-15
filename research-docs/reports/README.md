# Experiment reports

Each report is a frozen write-up of one **experiment** — a self-contained run of the
research loop that produced one or more model versions. Reports live at descriptive,
stable slugs (`<descriptive-slug>.md` — the slug is the public URL; see
[ADR-0016](../../docs/adr/0016-descriptive-report-slugs.md)) and are never edited
after the fact; supersede a published report with a new one. The living records are
each project's README `§ Versions` and `§ Leaderboard` sections (e.g.
[shakespeare's](../../projects/shakespeare/README.md#versions), ADR-0030) and the
per-version [model cards](../model-cards/).

Frontmatter `date:` carries the **full publish timestamp** (day, hour, minute —
normally the commit that published the report), not just the day: the site
displays only month + year but sorts by the timestamp, and several reports share
a publish day, so a date-only value makes the ordering an alphabetical accident.
`tools/check_integrity.py` enforces this.

| # | Report | Produced | Researcher | Date |
|---|--------|----------|-----------|------|
| 01 | [Can a big model improve a small one?](improve-a-small-model.md) — LLM-assisted research experiment, Rounds 1–4 (more data, modern architecture, BPE, diminishing returns). | `shakespeare-nanogpt-1 → -2` | Claude Opus 4.8 | Jun 2026 |
| 02 | [Can you put an obsession on a dial?](obsession-on-a-dial.md) — steerability + synthetic data, runs v1–v3 (bake the obsession into the corpus; the $0 ablation that found the dial's real bottleneck). | `→ gatsby-nanogpt-1` | Claude Opus 4.8 | Jun 2026 |
| 03 | [Can a model dream a single phrase?](dream-a-single-phrase.md) — the smallest corpus in the studio: punctuated permutations of six words; a learned model can't be the bot, and the memorization phase transition turns out to be a dreaminess knob. | `→ kenosha-kid-nanogpt-1` | Claude Opus 4.8 | Jun 2026 |
| 04 | [Can four borrowed models write one obsession?](mixture-of-models.md) — mixture-of-models synthetic data: four local open models write gatsby's corpus for $0 instead of the Claude API. The finding is that the blend is a designed object — a granite-heavy round broke the dial; rebalancing off it and doubling the data recovered it. | `→ gatsby-nanogpt-2` | Claude Opus 4.8 | Jun 2026 |
| — | [The logits oracle: running small models in the browser](logits-oracle.md) — *design note* (series: player). Export only the forward pass as a static ONNX graph; keep the loop, sampling, and tokenization in JS. | — | Claude Opus 4.8 | Jun 2026 |
| — | [The twenty-second training run](twenty-second-training-run.md) — *maintenance note* (series: core). A repo-wide audit by a larger model, and the smoke test that now trains a tiny GPT end to end (train → resume → sample → eval → export parity) on every push. | — | Claude Fable 5 | Jul 2026 |
| 05 | [Can a chess model's illegal moves be the point?](illegal-moves-are-the-point.md) — the studio's first sampler/prober project: a three-tier chess-move GPT family (5×5, 8×8, custom 12×10) that renders illegal moves as near-misses instead of masking them. All three tiers land in a tight 35–39% legal-move-rate band despite very different boards; two design-doc facts about Grand's variant turned out wrong when checked against the live engine instead of a web search. | `→ daydream-chess-nanogpt-1, -micro-1, -grand-1` | Claude Sonnet 5 | Jul 2026 |
| 06 | [Can a model's own likelihood hear register?](the-likeliest-line-is-a-footnote.md) — linewell's first draws: the shakespeare model's most inevitable text is Gutenberg apparatus (footnotes at 1.2–1.8 NLL/token), fluent editorial prose scores inside any verse band, and the calibrated band's raised floor — not its ceiling — is the load-bearing edge. An LLM judge held register where likelihood could not. | — | Claude Fable 5 | Jul 2026 |
| — | [An instrument anything can play: why the studio ships a CLI](an-instrument-anything-can-play.md) — *studio note*. The models are instruments, the players are the research, and sup is the smallest doorway — Monolith's toolbox philosophy applied to the studio's shelf. | — | Claude Fable 5 | Jul 2026 |
| — | [A borrowed cadence: where the house style comes from](a-borrowed-cadence.md) — *studio note*. The writing house style, encoded as a skill and distilled from Anthropic research posts, Thoughtful Lab, and Ramp Labs. A two-file pilot found the studio's biggest tic (emphasis overload) and corrected the skill's own bold-budget rule; the studio-wide sweep that followed confirmed the diagnosis at scale. | — | Claude Fable 5 | Jul 2026 |
| 07 | [Can a token budget buy a finished chess game?](budget-cant-buy-the-midgame.md) — Token Chess, rounds one through five. Budget buys plies at a worsening rate (all 15 calibration games forfeit; legality collapses 49% → 14% out of the book, then floors at 8–12% to ply 250); remove death and random configs match olmo; price batches + picking with engine adjudication and ministral — the worst sampler on the board — beats olmo 3–1 on tempo; and memory goes unused twice: assigned, zero notes in 24 games; freely chosen with stated reasons, 24 seats for 24 — still zero notes. | — | Claude Fable 5 | Jul 2026 |
| 08 | [A pass over the studio: one research loop across four models](a-pass-over-the-studio.md) — a single afternoon improving all four models at once: a larger model planned per-model optimizations, small runs executed them. Two new releases, one migration, one eval-only characterization, and findings that only show up across projects side by side. | `→ shakespeare-nanogpt-3, kenosha-kid-nanogpt-2` | Claude Fable 5 | Jul 2026 |
| 09 | [One model or twenty-six?](one-model-or-twenty-six.md) — twenty-six 1.8M per-letter GPTs against one letter-conditioned generalist on 82k glyph outlines from 759 sans-serifs. The 47.8M generalist wins mean BPC by 2% but fails to draw a well-formed glyph 29% of the time where the specialists fail 8% — and ships anyway, on purpose, with the case's numbers frozen as the yardstick. | `→ glyph-nanogpt-1` | Claude Fable 5 | Jul 2026 |
| 10 | [Three predictions from a font chapter](three-predictions-from-a-font-chapter.md) — glyph's round-2 plan, built from a type-design chapter, tested where it could be without training anything. One prediction died (the craft axes explain 2.1% of what the generalist finds hard; outline complexity explains 17.9%), one passed (the grid binarized overshoot instead of erasing it), one survived after the corpus corrected the plan (u is a round letter). | craft_score.py + measure_axes.py | Claude Fable 5 | Jul 2026 |
