# ADR 0032: /train — a runnable prompt as page content

- **Status:** Accepted
- **Date:** 2026-07-17
- **Deciders:** Romello Goodman (with Claude)

## Context

The site needed a `/train` page: a single copy-paste prompt that trains a
character-level nanoGPT on TinyStories inside any coding agent, on the
visitor's own machine. The content model (ADR-0007) says the website owns
zero source content — everything it renders is synced from `research-docs/`
(reports, model cards) or `registry.json` at prebuild. The prompt fits
neither existing genre: it isn't a report (no findings, and it must stay
editable as the recipe improves — reports freeze on publish, ADR-0016) and
it isn't a model card. It's the first *page* — standing site content whose
source of truth still belongs with the research.

## Decision

We will add a third content genre, **pages**: top-level markdown files in
`research-docs/` (starting with `research-docs/train.md`) rendered at their
own routes. Concretely:

- The existing whole-directory sync already copies top-level files;
  `lib/content.js` gains `getPage(name)` with the same link/asset rewriting
  as reports (`repoBase: "research-docs"`).
- **Pages are living documents.** Unlike reports they are edited in place —
  no freezing, no draft pruning (that machinery stays scoped to `reports/`).
- `/train` renders the doc's first fenced code block through a copy-button
  component (`PromptBlock`); the copied text is the raw fenced content,
  byte-for-byte. The prose around it renders as normal markdown.
- Pages get the ADR-0019 treatment: a raw `.md` twin (`/train.md`) and a
  `## Pages` section in `llms.txt`.
- The prompt targets karpathy's nanoGPT, not `core/`, and pins a
  lowest-common-denominator config — device detected at run time
  (`cuda` → `mps` → `cpu`), `dtype='float32'` and `compile=False`
  everywhere. Generality over speed: nothing in the prompt depends on this
  monorepo or on any particular hardware.

## Consequences

- Easier: a new page is one markdown file plus one route; the prompt is
  version-controlled prose Claude edits like any other doc, and it ships
  through the same sync/rewrite/text-twin pipeline as everything else.
- Harder: two markdown genres now have opposite freezing rules — reports
  freeze, pages don't — and future editors have to know which they're in.
- The `/train` route assumes the doc's *first* fenced block is the prompt;
  a page with a different shape needs its own route logic.
- Pages are deliberately absent from `llms-full.txt`, which stays a research
  corpus (reports + cards).

## Alternatives considered

- **Hardcode the prompt in `app/train/page.jsx`** — breaks the
  owns-zero-content rule the first time; the prompt is exactly the kind of
  content that should live next to the research it distills.
- **Publish it as a report** — wrong lifecycle: reports freeze at a slug
  (ADR-0016), and this recipe should improve in place (e.g. backfilling
  measured wall-clock and loss after a calibration run).
- **Point the prompt at `core/`** — couples visitors to the monorepo, `uv`,
  and our release layout. karpathy's nanoGPT is self-contained, is the
  studio's actual lineage, and makes the prompt runnable anywhere.
