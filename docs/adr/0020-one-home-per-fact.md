# ADR 0020: One home per fact — documentation is deduplicated by ownership

- **Status:** Accepted
- **Date:** 2026-07-01
- **Deciders:** Romello Goodman (with Claude)

## Context

The July 2026 repo audit ([six-second-training-run](../../research-docs/reports/six-second-training-run.md))
found that nearly every documentation staleness bug was a **duplication bug**:
the same fact living in several places, updated in one and forgotten in the
rest. The concrete clusters:

- **The repo map existed three times** — root `README.md`'s Layout table,
  `CLAUDE.md`'s Map table, and `docs/architecture.md`'s split diagram — and all
  three were stale in *different* ways. `docs/monorepo-plan.md` overlaps
  heavily with ADR-0001 and architecture.md.
- **Per-model facts live in ~6 places**: `registry.json`, the project
  `MODELS.md`, the frozen snapshot README, the model card, the leaderboard row,
  and the report. gatsby-nanogpt-2's dial numbers were written out in at least
  four of those; kenosha-kid's "six words / Pynchon / Kazemi bot" framing was
  told nearly verbatim in five.
- **Project CLAUDE.md files restate root rules** — the "Credit the researcher"
  block was copy-pasted into all three, and shakespeare's CLAUDE.md restated
  the dataviz rules at length that `tools/dataviz/README.md` owns. The dataviz
  token story was told in four places, and two of them drifted apart (the
  dark-neutral mismatch ADR-0018 was supposed to prevent).

`tools/check_integrity.py` (added in the same round) catches broken links
mechanically, but **no checker can catch contradictory copies** — two prose
restatements of one fact can both parse, both link-resolve, and still disagree.

## Decision

We will keep **one canonical home per fact** and make everything else *link*
instead of restate:

| Fact | Its one home |
|---|---|
| A model's spec (arch, tokenizer, params, BPC, tag, tagline) | `registry.json` |
| A model's scores over time | the project's `leaderboard.md` |
| A model's narrative (what it is, data, limits) | its model card |
| How an experiment went and why | its frozen report |
| The repo map and why it's shaped this way | `docs/architecture.md` |
| Repo-wide working rules | root `CLAUDE.md` |
| Tool usage and conventions | that tool's own README |

Root `README.md` and `CLAUDE.md` may keep *short* orientation tables (they are
landing pages), but detail beyond one line per row belongs in the canonical
home. When writing a doc and reaching for a fact that already has a home, link
to it; if a summary is unavoidable, keep it to a sentence and cite the home.
Historical planning docs are marked as archived rather than maintained.

## Consequences

- Updating a fact means updating one file; the link-checker keeps the pointers
  honest, and there are no copies left to contradict it.
- Readers follow one extra link sometimes. That is the cost, and we accept it —
  a wrong "convenient" copy is worse than a click.
- Some duplication is *load-bearing* and stays: frozen release folders
  deliberately vendor code and corpora (ADR-0003), and reports quote the
  numbers they analyze (they are frozen records of a moment, not living docs).
  This ADR governs **living documentation**, not frozen artifacts.
- Existing docs get consolidated opportunistically (the audit round slims the
  worst offenders); new docs follow the rule from the start.

## Alternatives considered

- **A generator that renders duplicated sections from one source** (e.g.
  MODELS.md tables generated from registry.json). Rejected for now: more
  machinery than a studio this size needs, and generated blocks inside
  hand-written markdown invite a different class of drift. Reconsider if
  linking proves too lossy.
- **A checker that diffs restatements.** Rejected: prose restatements can't be
  compared mechanically; this is exactly the class of bug you prevent
  structurally or not at all.
- **Status quo (duplicate freely, fix on audit).** Rejected: the audit found
  the same fact stale in up to four homes at once; periodic cleanup doesn't
  scale with the number of copies.
