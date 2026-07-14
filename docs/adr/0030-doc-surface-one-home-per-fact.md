# ADR 0030: the doc surface — one home per fact, applied to the tree

- **Status:** Accepted (applies [ADR-0020](0020-one-home-per-fact.md) to the doc tree itself)
- **Date:** 2026-07-14
- **Deciders:** Romello Goodman (with Claude)

## Context

A doc-drift review found the same fact stated in several markdown homes and
wrong in all of them together: gatsby's prompt format lived in README,
CLAUDE.md, and a stale `docs/plan.md` — all three teaching the pre-reformat
string; daydream's pipeline was wrong in README and CLAUDE.md in tandem. The
living descriptive surface was ~40 files, dominated by a six-file pack per
project (README, CLAUDE.md, MODELS.md, leaderboard.md, models/README.md, the
journal) plus four overlapping repo handbook docs. Every drift bug of the
review lived in this layer; the record layers (ADRs, frozen reports, journals,
run evidence) don't drift because they're append-only.

The audiences that matter are agents and users in a text editor — fewer
places to look beats prettier rendering.

## Decision

**1. Per project, facts live in README.md and only there.** The README
carries the version index (`## Versions`, absorbing `MODELS.md`) and the
scoreboard (`## Leaderboard`, absorbing `leaderboard.md`). `CLAUDE.md` is
rules-only: it states locked decisions and conventions, never a fact about
the project — any bullet that *describes* belongs in the README.
`models/README.md` is a three-line pointer.

**2. One repo handbook.** `docs/architecture.md` + `docs/workflows.md` +
`docs/releasing.md` merge into `docs/handbook.md` (§ Architecture,
§ Workflows, § Releasing a version). The backlog (`docs/TODO.md`) moves out
of the repo entirely — it is the researcher's working state, not repo
description.

**3. Published ink pins paths; stubs keep them alive.** Frozen reports
(ADR-0016), already-uploaded HF card copies, frozen release snapshots, and
ADRs all carry links that render as URLs into this tree. Any file such ink
links becomes a two-line redirect stub instead of being deleted; everything
unpinned is deleted outright (stale one-offs like gatsby's `docs/plan.md`
die too — git history keeps them, the `monorepo-plan.md` precedent).

**4. The remaining hand-maintained indexes are enforced, not trusted.**
`tools/check_integrity.py` fails when an ADR or a `tools/` directory has no
index row, when a project README lacks its Versions/Leaderboard sections or
omits a released model id, or when any relative markdown link 404s.

## Consequences

- The living descriptive surface drops from ~40 files to ~18 (+7 inert
  stubs); an agent's lookup path is root `CLAUDE.md` → `docs/handbook.md` or
  a project's `README.md`/`CLAUDE.md` → tool READMEs.
- A release's markdown work is two files: the project README and the model
  card (plus `registry.json`).
- READMEs get long (shakespeare's is ~300 lines) — accepted; agents and
  editors navigate by section, and one long true file beats four short
  drifting ones.
- The stubs are inert but exist; deleting one later requires checking what
  pins it (the link checker will say).
- Tool and package READMEs stay — for multi-file tools the README is the
  agent's entry point, and each tool documenting itself in place survives
  sparse clones.

## Alternatives considered

- **Folding tool READMEs into module docstrings** — rejected: the READMEs are
  the entry points agents find first, token-chess's README is itself a locked
  contract, and dataviz's is the design-system home (ADR-0018/0020).
- **Deleting pinned files and accepting broken links in frozen ink** —
  rejected outright; frozen reports and published HF cards are promises.
- **Generating MODELS.md/leaderboard.md from registry.json** — the prose
  around the numbers is the point of those records; generation would strip it.
