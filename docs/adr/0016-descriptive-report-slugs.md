# ADR 0016: Research reports use descriptive slugs, not `experiment-NN`

- **Status:** Accepted
- **Date:** 2026-06-29
- **Deciders:** Romello Goodman (with Claude)

## Context

Reports lived at sequential filenames — `experiment-01.md` … `experiment-04.md`,
plus `note-01-logits-oracle.md`. The filename *is* the public URL: the website
derives each report's slug from its filename (`lib/content.js`), so these surfaced
on the studio site as `/research/experiment-03/`.

Two problems:

- **The slugs aren't readable.** `/research/experiment-03/` says nothing; the lone
  note, `note-01-logits-oracle`, already showed a descriptive slug reads better.
- **The number and the type word were redundant.** Every report already carries
  `type:` (experiment / note) and `series:` in frontmatter, and the site orders the
  index by `date`, not by filename. So the `experiment-`/`note-` prefix and the
  running number duplicated information that lived elsewhere — they bought ordering
  the site didn't use and a type distinction frontmatter already held.

The old `CLAUDE.md` freeze rule was keyed to the number ("supersede with a new
number"), so the numbering wasn't just cosmetic — it was the supersede mechanism.

## Decision

We will name each report with a **descriptive, kebab-case slug** that reflects its
subject, dropping both the `experiment-`/`note-` prefix and the running number:

| Was | Now |
|---|---|
| `experiment-01.md` | `improve-a-small-model.md` |
| `experiment-02.md` | `obsession-on-a-dial.md` |
| `experiment-03.md` | `dream-a-single-phrase.md` |
| `experiment-04.md` | `mixture-of-models.md` |
| `note-01-logits-oracle.md` | `logits-oracle.md` |

The experiment/note distinction and the topic grouping move entirely to frontmatter
(`type:`, `series:`), where they already lived. A slug is a **stable public URL**:
once a report is published, its slug is frozen — supersede with a *new* report
rather than renaming or editing (the freeze rule, restated in `CLAUDE.md`).

(`mixture-of-models` replaces the working title's "four borrowed models" — the
report is about a *mixture* of four local open-weight models writing the corpus,
which is both the headline finding and clearer than "borrowed.")

## Consequences

- **Readable URLs.** `/research/obsession-on-a-dial/` describes itself; the index,
  sitemap, and any shared link carry meaning.
- **Frontmatter is now the single source of type/series.** Anything that needs to
  tell an experiment from a note reads `type:`, not the filename — the prefix is
  gone, so there's no second, drifting copy.
- **Supersession is no longer numeric.** "Supersede with a new number" becomes
  "supersede with a new report" — a slightly looser rule. The running order, when
  needed, comes from `date`/`series`, not the filename.
- **One-time URL churn.** The reports were already live at `experiment-NN`, so this
  changed published URLs once. The static export has no redirect layer, so old
  links don't forward — acceptable now, while inbound links are negligible, and the
  reason the slug is frozen going forward.
- **Cross-references had to be rewritten.** Sibling-report links, the reports
  `README.md` index, three model cards, and `docs/TODO.md` referenced the old
  filenames; all were updated in the same change. ADR-0015's prose keeps the old
  names as a historical record.

## Alternatives considered

- **Keep `experiment-NN`.** No churn, no freeze-rule change — but the unreadable
  URLs were the whole reason for the pass, and the number/prefix stayed redundant
  with frontmatter.
- **Keep a leading number, drop only the word** (`03-dream-a-single-phrase`).
  Preserves ordering and a numeric supersede anchor, but the site already orders by
  `date`, so the number earns its place in the URL only as visual noise.
- **Pure title-slug** (`can-a-model-dream-a-single-phrase`). Maximally descriptive
  but long and tied to the exact question phrasing; the short hand-picked slug reads
  better and is more stable if a title is reworded.
