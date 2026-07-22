# ADR 0033: Index tables are generated from their sources

- **Status:** Accepted (amends [ADR-0030](0030-doc-surface-one-home-per-fact.md) decision 4)
- **Date:** 2026-07-22
- **Deciders:** Romello Goodman (with Claude)

## Context

ADR-0030 kept three hand-maintained index tables — the reports index
(`research-docs/reports/README.md`), the ADR index (`docs/adr/README.md`),
and the tools index (`tools/README.md`) — and had `check_integrity.py` police
them ("enforced, not trusted"). The policing worked: the 1-month-and-60-models
note shipped without its index row and CI went red. But red CI for a
forgotten ritual is the failure mode, not the fix, and an audit showed the
premise of hand-maintenance was gone: every column of the reports table
(title, number, produced, researcher, date, summary) already lives in report
frontmatter, and every ADR row is its file's H1 plus `**Status:**` line. The
tables were copies, and publishing meant editing two homes for one fact.

## Decision

We will generate the three index tables and make hand-editing them a CI
failure.

1. **`check_integrity.py --write` regenerates the tables** between
   `<!-- generated:NAME -->` / `<!-- /generated -->` markers; the prose around
   the markers stays authored. Check mode (what CI runs) fails a stale or
   missing block, and the finding names the fix: run `--write`.

2. **Each table's source is the artifact itself.** Reports: frontmatter
   (`title`, `number`, `type`/`series`, `summary`, `produced`, `researcher`
   resolved through `registry.json`, `date` rendered month + year, rows sorted
   by timestamp). ADRs: the `# ADR NNNN: <title>` H1 and the `**Status:**`
   line, verbatim. Tools: a directory's README **tagline** — the italic line
   directly under its H1, now a required convention — and a script's docstring
   first sentence. Taglines stay link-free: a relative link resolves
   differently from the two homes that display it.

3. **Authored surfaces stay authored.** Project READMEs (`## Versions`,
   `## Leaderboard`), model cards, and all prose remain hand-written; the
   registry cross-checks on them are unchanged. Generation applies only where
   the audit showed pure duplication.

## Consequences

- Publishing a report, adding an ADR, or adding a tool is one file plus one
  command; the "forgot the index row" drift class is unrepresentable rather
  than policed.
- The reports table loses hand-tightened blurbs — rows now carry frontmatter
  summaries verbatim, so summaries must be written index-worthy (house style
  already requires this). ADR status text appears verbatim too, so long
  status lines make long rows.
- Every tools directory must have a README with a tagline (this ADR added
  `hf-stage/`'s, the one directory without a README).
- ADR-0030 decision 4 is amended: "enforced, not trusted" becomes "generated
  where derivable; enforced where authored."

## Alternatives considered

- **Keep hand-maintained + enforced (status quo).** The curation it bought —
  tightened blurbs, curated row order — turned out nearly empty against the
  cost: a recurring red-CI ritual and duplicate homes for every row.
- **A separate generator script.** Folding `--write` into the checker keeps
  the derivation and the enforcement in one file — they can't drift apart,
  and the failure message can name its own fix.
- **Delete the indexes instead.** The tree's readers (sparse clone, GitHub)
  lose the catalog view the site can't give them; ADR-0030's reasons for the
  indexes existing still hold — only the maintenance mode was wrong.
