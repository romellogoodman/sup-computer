# ADR 0013: Attribution of the AI researcher

- **Status:** Accepted
- **Date:** 2026-06-28
- **Deciders:** Romello Goodman (with Claude)

## Context

This studio is run as an LLM-assisted research practice: a Claude model acts as
the *researcher* — diagnosing a model, proposing changes, training new versions,
and measuring them — under human direction. Until now that researcher was named
only in prose (the home-page blurb, the odd model-card sentence) and was implicitly
always the same model.

That won't hold. We will deliberately use different researcher models over time —
stronger and weaker ones — to see how researcher capability shows up in the work.
Once the roster has more than one name, "which model did what" has to be a recorded,
machine-readable fact, not something a reader infers. Attribution also wants a single
spelling: "Claude Opus 4.8" written free-hand in eight places drifts.

The researcher is distinct from the **subject** — the small GPT being built
(`shakespeare-nanogpt-1`, …), which we already track. Attribution credits the
researcher, not the subject.

## Decision

We will record the AI researcher as a first-class, id-keyed property across reports,
models, and the site.

1. **One canonical roster.** `registry.json` gains a top-level `researchers` map
   from a stable id to its identity:

   ```json
   "researchers": {
     "claude-opus-4-8": { "name": "Claude Opus 4.8", "vendor": "Anthropic", "harness": "Claude Code" }
   }
   ```

   Everything references the id; the display name is resolved once. New researchers
   get a new entry here before they're referenced.

2. **Reports** carry `researcher: <id>` in frontmatter. It is **scalar** today —
   every report so far is single-model. When a report genuinely spans multiple
   researchers, it graduates to a list that says which model did which rounds; this
   is the documented future form, not built yet:

   ```yaml
   researcher:
     - rounds: "1-3"
       model: claude-opus-4-8
     - rounds: "4"
       model: claude-sonnet-4-6
   ```

   The site resolver treats a scalar as the whole-report researcher; a list is a
   per-phase breakdown. Moving from scalar to list is additive, not breaking.

3. **Models** carry `researcher: <id>` in their `registry.json` entry — the
   researcher that produced that version. Model **cards** keep their HuggingFace-style
   frontmatter clean (so they stay portable) and state attribution in the body as a
   `**Researcher:**` line.

4. **The site** resolves ids to names via `researcherName()` and shows the credit in
   the report list, the report meta, and the model table. The home blurb names the
   current researcher but defers specifics to the per-artifact attribution.

5. **Backfill.** All existing research is attributed to `claude-opus-4-8`. This edits
   four already-published (frozen) reports' frontmatter — a one-time, sanctioned
   metadata backfill, not a content change, on the same footing as a date correction.
   The freeze still governs report *prose*.

## Consequences

- "Which model did what" is queryable from `registry.json` and report frontmatter,
  and legible on the site — the precondition for comparing stronger vs. weaker
  researchers as the roster grows.
- One spelling of each researcher; no free-hand drift.
- Two small standing obligations: every new report sets `researcher`, and every new
  model entry sets `researcher` against an id that exists in the roster. Captured in
  the root and per-project `CLAUDE.md` and the reports README checklist.
- The scalar→list path for multi-model reports is specified but unbuilt; the first
  genuinely multi-researcher report will implement the list-resolving code.
- Editing frozen reports' frontmatter is a precedent we accept only for cross-cutting
  metadata (dates, attribution), never for findings.

## Alternatives considered

- **Prose only.** Keep naming the researcher in text. Rejected: not queryable, drifts,
  and unworkable the moment two models appear in one series.
- **A custom `researcher` key in model-card frontmatter.** Rejected for the cards: it
  pollutes the HuggingFace-portable block with a non-standard key. The registry already
  drives the site, so attribution lives there plus a body line.
- **Per-round structure from day one.** Rejected as premature — every current report is
  single-model. We specified the shape instead of building it, so adopting it later is
  additive.
- **Free-floating strings instead of an id map.** Rejected: ids + a roster are what make
  "smarter vs. dumber researcher" a comparison rather than a string match.
