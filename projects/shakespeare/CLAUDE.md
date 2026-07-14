# CLAUDE.md — rules for agents working in shakespeare

Facts live in [`README.md`](README.md) — the project, pipeline, quick start,
version index (§ Versions), and scoreboard (§ Leaderboard). This file is only
the rules (ADR-0030).

- **Every chart goes through [`tools/dataviz/`](../../tools/dataviz/README.md)**
  — never hand-author chart SVGs or reach for matplotlib/Chart.js/D3. The
  dataviz README is the home for chart conventions (ADR-0020, ADR-0018).
- **Never commit trained weights** (gitignored) — commit everything needed to
  reproduce them instead.
- **Published reports are frozen** (ADR-0016) — never edit or rename
  `research-docs/reports/<slug>.md`; supersede with a new report. The living
  records are the README's Versions/Leaderboard sections and the model cards.
- **Shared engine code goes in `../../core/`**; this project holds only its
  datasets, configs, run outputs, `test.txt`, and frozen releases.
- **Score every version on the same fixed held-out `test.txt`, in BPC**, so
  the series stays comparable end to end.
- **Each release gets a frozen, self-contained folder** under `models/` pinned
  to a git tag — never refactor one to share `core/`. Checklist:
  [`docs/handbook.md`](../../docs/handbook.md#releasing-a-version).
- **Credit the researcher** — root [`CLAUDE.md`](../../CLAUDE.md), ADR-0013.
