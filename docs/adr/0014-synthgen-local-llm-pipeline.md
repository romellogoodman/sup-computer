# ADR 0014: Synthetic-data generation via LM Studio lives in `tools/synthgen`

- **Status:** Accepted
- **Date:** 2026-06-28
- **Deciders:** Romello Goodman (with Claude)

## Context

Gatsby proved out LLM-generated corpora for tiny GPTs, but its `generate.py` is
project-local and Claude-API-specific (see [ADR-0011](0011-vendor-gatsby.md), and
[`docs/TODO.md`](../TODO.md) item 3, which reserves a future `core/curation/`).
Two new forces have appeared since:

1. **A diversity problem.** Distilling a *single* teacher into a tiny student is
   circular — the student inherits one model's habits. We want
   **mixture-of-models** corpora: many different models contributing "voices,"
   the way a varied human corpus would.
2. **A local backend.** Several capable local models now run under **LM Studio**,
   which exposes an OpenAI-compatible server. Generating locally is free per
   token and unlocks the model mix without per-call API cost.

This needs a *shared* generation engine — the generation analog of
`tools/dataviz` — rather than a second project-local copy. But the monorepo's
standing rule is to not abstract into `core/` from a single example.

LM Studio also imposed a hard, non-obvious constraint: its local models are
reasoning/"thinking" models that, left alone, spend the whole token budget on a
hidden trace and return **empty** content. The only suppression lever that worked
in testing is `"reasoning_effort": "none"` in the request body (`enable_thinking:
false` and `/no_think` did not).

## Decision

We will add **`tools/synthgen/`** — a stdlib-only engine (`synthgen.py`) plus a
CLI (`build.py`) — as the single pipeline every **LLM-generated** synthetic
corpus goes through, mirroring `tools/dataviz`. Specifically:

- **It lives in `tools/`, not `core/curation/`.** `core/curation/` stays a
  reserved slot. Gatsby (Claude API) and synthgen (LM Studio) are *two* consumers
  but of different shapes; the shared abstraction is still not forced. We promote
  to `core/` only when a real second consumer makes the right interface obvious
  (the small-hours project, per the TODO). Until then synthgen is researcher
  tooling that we *operate*, exactly the `tools/` charter ([ADR-0006](0006-tools-top-level.md)).
- **It is LLM-only, via LM Studio.** synthgen drives local LLMs over LM Studio's
  OpenAI-compatible API with stdlib `urllib`. **Procedural / non-LLM corpora
  write their own pipeline** (as `kenosha-kid` does) — a deterministic generator
  is not a model client and does not belong here.
- **Reasoning suppression is the default.** `reasoning_effort="none"` is baked in
  as the default and is overridable. Empty content is surfaced (not silently
  dropped) so a suppression miss is visible.
- **Provenance is manifest-first.** Every run writes a `manifest.json` recording
  the model mix, per-sample source model / prompt / temperature / token counts /
  sha1, the dedup ledger, and each document's offset into `raw.txt`. Because
  generation is non-deterministic, the manifest — not a re-run — is the
  reproducibility record. Dedup (exact + token-set Jaccard) never drops silently.
- **Output is a `prepare.py` drop-in.** synthgen writes `raw.txt` (documents
  joined by `\n\n`), the exact shape a project's `prepare.py` already tokenizes.
- **Zero dependencies.** stdlib only, matching dataviz.

## Consequences

- One canonical place for LLM corpus generation, and a clear answer to "where did
  this corpus come from?" — its committed manifest.
- The model mix is first-class and recorded, so a corpus's diversity is auditable.
- A *third* style of corpus tooling now exists (Claude-API gatsby, procedural
  kenosha-kid, local-LLM synthgen). They are intentionally not unified yet; the
  cost is duplicated effort if/when they converge into `core/curation/`. We accept
  it to avoid designing that interface blind.
- synthgen is coupled to LM Studio specifics (the `reasoning_effort` lever, the
  `embed` discovery filter, cold-load timeouts). These are documented in the
  module and README so they read as known facts, not surprises.
- No dollar-cost log (local generation is free per token); the manifest carries
  token counts + latency instead of a `costs.jsonl` analog.

## Alternatives considered

- **Put it in `core/curation/` now** — rejected as premature, the same call
  [ADR-0011](0011-vendor-gatsby.md) made: a single (or one-and-a-half) consumer is
  not enough signal to fix the shared API.
- **Extend gatsby's `generate.py`** — rejected. It is Claude-API-specific and
  project-local by design; bending it to also speak LM Studio and serve other
  projects would violate "projects stay thin and self-describing."
- **Use the `openai` SDK / `requests`** — rejected. The OpenAI-compatible surface
  we need (two endpoints) is trivial over stdlib `urllib`, and a dependency would
  break the tools' zero-dependency ethos.
- **Skip dedup, or drop silently** — rejected. Real near-duplicates appear across
  and within models; silent removal would corrupt the provenance record. Dedup is
  explicit and logged.
- **Fold procedural corpora in too** — rejected. A deterministic generator isn't a
  model client; conflating them would muddy what synthgen is.
