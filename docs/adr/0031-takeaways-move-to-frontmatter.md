# ADR 0031: Takeaways are frontmatter, and model cards don't carry them

- **Status:** Accepted
- **Date:** 2026-07-15
- **Deciders:** Romello Goodman (with Claude)

## Context

The key-takeaways block is document metadata living as body content.
[ADR-0015](0015-research-post-standardization.md) authored it as a raw-HTML
`<div class="takeaways">` inside the markdown, and explicitly rejected
frontmatter because the box would be "invisible when reading the `.md`
in-repo." A year of use argues the other way.

The body turned out to be the wrong home in practice:

- **Placement kept drifting.** ADR-0015 put report takeaways near the top and
  card takeaways in a dated bottom addendum; the house-style pass later moved
  cards' blocks to the top. The renderer papers over the drift:
  `website/components/Markdown.jsx` searches the rendered tree for a
  `.takeaways` node and splices it to position zero. A hoist hack to enforce a
  placement rule is the sign the field wants to be structured.
- **Raw HTML costs formatting.** Bullets can't use markdown inline syntax —
  bold and code are hand-written as `<strong>`/`<code>`. ADR-0015 accepted
  that cost; every author since has paid it.
- **Structured consumers arrived.** The LLM-readable `.md` twins
  ([ADR-0019](0019-llm-readable-markdown-endpoints.md)) already compose each
  report doc from frontmatter (`website/scripts/build-text.mjs`), and the
  designed-but-unbuilt OG/social cards and series pages want a scannable
  digest per piece. Their choice today is scrape HTML out of the body or go
  without.
- **The in-repo objection weakened.** `summary:` already lives in frontmatter
  as prose and nobody calls it invisible. GitHub renders YAML frontmatter as a
  table at the top of the file; a raw-file reader sees it first.

Separately, the block spread wider than its purpose. All 11 model cards carry
one, but a card is a reference document: it opens with the model-details
table rendered from `registry.json` plus the frontmatter summary, readers
jump to sections rather than read through, and the card's bullets mostly
re-distill the round's report. Among the 14 reports, the split tracks length,
not discipline: all 10 experiments (1,900–3,300 words) have takeaways, the
two ~1,500-word notes (`logits-oracle`, `twenty-second-training-run`) have
them, and the two ~550-word notes never got them. The de facto rule is
"long pieces get an abstract" — it was just never written down.

## Decision

**Takeaways move to a `takeaways:` frontmatter field** — a YAML list of
markdown strings, three to five items, inline markdown allowed under the
house-style bold budget. The body carries no takeaways HTML.

```yaml
takeaways:
  - >-
    A ~10M char-level model baked to compulsively reach for Gatsby's green
    light — **Golden Gate Claude, but Gatsby**. The obsession worked on the
    first real run; the hard part was the intensity dial (`green=1..5`).
```

**Reports carry the field; model cards don't.** Required for
`type: experiment`, the author's call for `type: note` (the length rule,
stated: a note long enough to need an abstract gets one), never on model
cards — a card's distillation lives in the round's report, and the details
table plus summary already open the page.

Rendering and generation follow the field:

- `website/app/research/[slug]/page.jsx` renders the box from
  `frontmatter.takeaways` — same `.takeaways` markup and CSS module, so the
  styled output is unchanged. The hoist in `Markdown.jsx` is deleted.
- `build-text.mjs`'s `reportDoc` emits the takeaways as a bullet list after
  the summary, so the `.md` twins and `llms-full.txt` keep them. `cardDoc`'s
  "already self-contained (H1, takeaways, prose)" comment updates.

**One-time mechanical migration, in place.** The 12 takeaways-bearing reports
get their div converted to frontmatter (`<strong>` → `**`, `<code>` →
backticks; the words don't change); the 11 cards have the block deleted.
[ADR-0016](0016-descriptive-report-slugs.md)'s freeze protects content and
slugs, not serialization — precedent is ADR-0015's own standardization pass
and the 2026-07-02 researcher-line sweep across every card. The house-style
skill's takeaways rules re-point to the field (its "never remove it" scoped
to reports), and ADR-0015 is marked amended by this ADR.

## Consequences

- Placement stops being an authoring rule anyone has to remember, and the
  renderer hoist goes away. Consumers — the twins today, OG cards and series
  pages when built — read a field, not a regex over body HTML.
- Bullets regain markdown inline syntax.
- On GitHub the takeaways render as rows in the frontmatter table rather
  than a styled box — a weaker in-repo presentation than the div. Accepted:
  frontmatter is still the first thing in the file.
- The migration touches 23 published files, format-only. Hugging Face card
  copies staged before the migration keep the old block until each model's
  next publish, which drops it; no re-publish needed.
- A new convention to uphold: experiment reports must set `takeaways:`,
  model cards must not, and notes decide by length. This ADR is the
  reference.

## Alternatives considered

- **Keep the div (ADR-0015's call).** Rejected — the hoist hack and placement
  drift are the evidence that body-as-home failed, and the structured
  consumers exist now.
- **Frontmatter for reports, keep divs on cards.** Rejected — two homes and
  two formats for one fact ([ADR-0020](0020-one-home-per-fact.md)), and card
  takeaways duplicate the report's.
- **Strip takeaways from notes entirely (a strict type rule).** Rejected —
  the two long notes' takeaways are real content on ~1,500-word pieces;
  deleting them to satisfy a taxonomy inverts the length rationale the rule
  exists to serve.
- **A takeaways field in `registry.json`.** Wrong home — the registry is the
  model manifest; takeaways are per-document, and most documents aren't
  models.
