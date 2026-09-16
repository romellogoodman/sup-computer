# ADR 0038: synthgen gains a hosted backend — OpenRouter beside LM Studio

- **Status:** Accepted (amends [ADR-0014](0014-synthgen-local-llm-pipeline.md) — "LLM-only, via LM Studio" becomes two backends, one engine)
- **Date:** 2026-09-15
- **Deciders:** Romello Goodman (with Claude)

## Context

ADR-0014 made `tools/synthgen` the one engine every LLM-generated corpus goes
through, and made it local on purpose: LM Studio's models are free per
token, so a mixture of four or five of them costs nothing to run and the
manifest could skip dollars altogether. Every synthetic corpus since —
gatsby's second, pona's dialogues — was written that way.

The studio is about to depart from that deliberately. The next corpora will
be written by paid frontier models, named one at a time, because the
question is what a small model learns from a better teacher, not what it
learns from a free one. That brings back the two things the local path let
the engine forget. Cost: gatsby's first corpus recorded $2.94 in
`costs.jsonl` over the Claude API and every later run recorded nothing,
because there was nothing to record. Credit: [ADR-0037](0037-crediting-the-corpus-generators.md)
now credits each corpus's generators by id in `registry.json`, and a paid
run should produce those ids rather than leave them to be typed in later.

OpenRouter is the surface for it. It speaks the same OpenAI-compatible
`chat/completions` the engine already talks to, fronts most vendors under
one key, returns the dollar cost of every response in `usage.cost`, and
exposes reasoning control through one `reasoning` object. Its own rules are
not LM Studio's: it needs a bearer key, it takes app-attribution headers,
and its reasoning lever is `reasoning.effort`, not the top-level
`reasoning_effort` that was the only thing that worked locally.

Two standing rules shaped the shape. The tools stay stdlib-only, so no
`openai` SDK. And the user names the OpenRouter models every time — no
discovery, no `openrouter/auto`, no fallback list — so the engine must
refuse to guess.

## Decision

We will add OpenRouter as a second backend inside `tools/synthgen`, behind a
`--backend` switch whose default stays LM Studio, so every existing call
site behaves exactly as it did.

1. **One engine, two backends.** A `Backend` object carries each surface's
   base URL, headers, reasoning field and cost rule. LM Studio:
   `http://localhost:1234/v1`, no auth, `reasoning_effort`. OpenRouter:
   `https://openrouter.ai/api/v1`, `Authorization: Bearer`, the two
   attribution headers naming the studio (`HTTP-Referer: https://www.supcpu.com`,
   `X-Title: sup computer`), and `reasoning: {effort: …}`. Transport stays
   `urllib`. `--reasoning-effort` is one flag on both; the default is
   `"none"` on both — the value OpenRouter documents as disabling reasoning
   entirely, where `exclude: true` would only hide a trace that is still
   billed. Every sample records the exact field and value sent
   (`reasoning_control`), so a reader never has to infer which lever was
   pulled.

2. **The key comes from the environment or a dotenv file, never the tree.**
   `OPENROUTER_API_KEY` is read from the process environment, then the
   repo-root `.env.local`, then `.env`, first non-empty value wins, parsed
   with stdlib. A missing key fails before any request with a line saying
   where to put it. The key is never printed and never written to a
   manifest; `.env.example` at the root shows the one line.

3. **Models are always named on OpenRouter.** `--models` is required;
   `--list` is LM Studio only and errors out. The manifest records exactly
   the ids that were named.

4. **Cost is first-class.** OpenRouter's `usage.cost` — its credits are
   denominated in US dollars — is recorded per sample as `cost_usd`, summed
   per model and per run as `total_cost_usd`, and appended as one line per
   run to `costs.jsonl` beside the manifest, in the fields gatsby's
   Claude-API log uses where they apply. LM Studio runs record `0.0`, so the
   manifest has one shape everywhere. `--budget <usd>` caps a run: the engine
   stops before the request that, on the mean cost so far, would pass the
   ceiling, writes what it has, and sets `budget_hit: true`. A paid response
   without a `cost` field is an error, not a zero.

5. **The manifest emits generator ids.** Every model in the mix gets a
   `generators` entry `{id, model_id, backend, served_by}` in ADR-0037's
   shape — `id` the roster slug (vendor prefix stripped, dots to hyphens),
   `model_id` the exact upstream id — so a corpus built this way drops into
   `registry.json` without hand-copying. The per-sample `model` field is
   unchanged. `schema_version` moves to 2.

## Consequences

- A dollar figure now lives in a synthgen manifest, and a run has a
  ceiling. The record of "what did this corpus cost" is the same file that
  says who wrote it, for every backend — local runs say `$0.0` in the same
  field.
- The reasoning lever is per backend. The LM Studio finding (`reasoning_effort:
  "none"` is the only thing that works) stands; OpenRouter's is a different
  field with the same default, and the manifest names which one was sent.
- Explicit models on the paid surface means a run cannot silently fall
  through to a model nobody chose. It also means no `--list` convenience
  there; the user looks the ids up on openrouter.ai.
- ADR-0014's "LLM-only, via LM Studio" is amended to "LLM-only, via one of
  two OpenAI-compatible backends"; its other decisions — `tools/` not
  `core/`, manifest-first provenance, loud dedup, zero dependencies —
  stand. The `core/curation/` question is unchanged: still one engine, so
  still no shared abstraction to design.
- The studio now has four corpus-tooling shapes instead of three (Claude
  API gatsby v1, procedural kenosha-kid, synthgen local, synthgen hosted).
  The hosted one is the same engine, so the count that matters — engines —
  did not grow.
- A budget can overshoot by one sample's noise. Accepted: the cost of a
  request is not known until it returns, and predicting from the mean so far
  is the honest bound.

## Alternatives considered

- **The `openai` SDK.** It speaks OpenRouter natively, but the surface the
  engine needs is one POST, and the tools are stdlib-only by rule
  ([ADR-0006](0006-tools-top-level.md), ADR-0014). Rejected.
- **A separate tool** (`tools/hostedgen/`). Rejected: it would be a second
  engine with the same dedup, manifest and corpus writer, and ADR-0014's
  whole point was one canonical place a corpus comes from.
- **The Anthropic API directly, as gatsby v1 did.** One vendor, one key,
  and a project-local client the studio already decided not to generalise
  ([ADR-0011](0011-vendor-gatsby.md)). OpenRouter reaches that vendor and
  the others through one door, with the cost on every response.
- **Discovery on OpenRouter** (`GET /models`, 400-odd ids). Rejected by the
  user's standing rule: the models are named every run. Discovery would
  invite a default, and a default on a paid surface is a bill nobody
  chose.
- **`reasoning: {exclude: true}`** as the suppression lever. It hides the
  trace from the response but still bills it and still spends the token
  budget on it; `effort: "none"` is what the docs say disables reasoning.
- **Storing the key in a config file in the tree.** No: `.env` and
  `.env.*` are gitignored (`.env.example` is not), and the key is read, never
  written.
