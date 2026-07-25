# ADR 0034: CI pins its linter and names its rules

- **Status:** Accepted
- **Date:** 2026-07-25
- **Deciders:** Romello Goodman (with Claude)

## Context

CI linted with `uvx ruff check .` — no version — against a `[tool.ruff.lint]`
section that set `per-file-ignores` but never set `select`, relying on ruff's
implicit defaults (E4/E7/E9/F, as its own comment noted).

Both halves were time bombs, and both went off at once on 2026-07-25. ruff
0.16.0 shipped a wider default rule set, so the next push — a research note that
touched no Python at all — failed with 175 errors across files untouched since
July: 63 `RUF100`, 26 `I001`, 13 `SIM115`, and a long tail of `FURB`, `BLE`, and
`PLW`. Nothing in the repo had changed. The linter had.

This is the recurring failure the studio kept hitting as "CI breaks whenever we
publish." Publishing a report is the most common kind of push that changes no
code, which is exactly when a red build is most obviously not about the commit —
and most likely to be shrugged at.

A second, separate gap showed up in the same incident: that push also carried
four genuine lint errors, because the documented publishing flow
(`docs/handbook.md` § Publishing a report) said to regenerate the index tables
and nothing else. Lint ran for the first time in CI, after the push.

## Decision

We will pin both the linter and the rules it enforces.

1. **`select` is explicit** in `[tool.ruff.lint]` — `["E4", "E7", "E9", "F"]`,
   the set the repo was already relying on. A ruff release can no longer change
   what "lint clean" means here.
2. **The ruff version is pinned in `ci.yml`** (`uvx ruff@0.16.0 check .`).
   Bumping it is a deliberate commit with a local run behind it, not something
   that happens to the studio overnight.
3. **The publishing flow runs the checks CI runs.** `docs/handbook.md`
   § Publishing a report now lists `ruff check .` alongside
   `check_integrity.py --write`, so a red build is discovered before the push
   rather than after it.

## Consequences

Builds are reproducible: the same tree lints the same way in six months. Red CI
becomes informative again — it means the commit broke something, which is the
only way a signal stays worth reading.

The cost is that improvements no longer arrive for free. New ruff rules worth
having (import sorting, the `SIM` family) now need a deliberate bump, and the
pin will drift until someone does it. That's the trade we want at this size: a
studio where one person publishes research is better served by a lint gate that
never surprises than by one that stays current on its own.

Pinning also can't catch a rule that was always violated and never enforced. The
175 errors are still there under a wider rule set; this ADR declines to fix them
rather than pretending they don't exist. Adopting any of those families is a
separate, deliberate piece of work.

## Alternatives considered

**Add ruff to the `dev` dependency group and lint with `uv run ruff`.** This is
the better single-source answer — `uv.lock` pins it, and local matches CI
exactly. Rejected for now because CI lints *before* `uv sync`, so adopting it
means every lint failure waits on a full torch install first. Worth revisiting
if the pin in `ci.yml` starts drifting from what developers run locally.

**Take ruff 0.16's defaults and fix all 175.** Rejected as scope: most of the
findings are in frozen-in-spirit research tooling (`tools/token-chess/`), and a
sweeping mechanical rewrite of working analysis scripts buys little. The
explicit `select` records what the studio actually enforces; widening it later
is a decision with its own commit.

**Leave it unpinned and fix breakage as it appears.** Rejected — that's the
status quo that produced this ADR.
