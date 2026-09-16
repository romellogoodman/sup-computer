# ADR 0037: Crediting the corpus generators

- **Status:** Accepted (extends [ADR-0013](0013-attribution-of-the-ai-researcher.md) with a second roster)
- **Date:** 2026-09-15
- **Deciders:** Romello Goodman (with Claude)

## Context

Seven of the studio's twelve released models were trained on text that a
model wrote. Claude Sonnet 4.6 wrote gatsby-nanogpt-1's thousand stories
over the API; four local models wrote gatsby-nanogpt-2's two thousand via
LM Studio; three more wrote pona-nanogpt-1's dialogues; Fairy-Stockfish
played itself to produce every game daydream's Micro and Grand tiers ever
saw. The record of who wrote what existed — `costs.jsonl`,
`raw.manifest.json`, `dialogue_manifest.json`, the self-play script — but
it was scattered across five project folders in four file formats, named
free-hand in model cards ("Olmo 3 (7B) — AllenAI"), and readable by nobody
but a person who already knew where to look. The site's model page, which
credits the researcher in its details table, said nothing about the corpus
at all.

That gap is about to matter more. The studio is about to pay frontier
models to write corpora on purpose, and wants the author's name on the page
the way the researcher's is. ADR-0013 solved the same problem for
researchers: one roster, stable ids, resolved once. The corpus needs the
same treatment, and it needs it *before* the next paid corpus lands, not
after.

The researcher and the corpus generator are different jobs. The researcher
diagnosed, proposed, trained and measured; the generator wrote training
text and never saw the run. One model can hold both jobs (a Claude that
writes a corpus and then trains on it), so the ids must be able to meet,
but the roles must not merge.

## Decision

We will record who wrote every model's training corpus as a first-class,
id-keyed fact in `registry.json`, beside the researcher, and render it on
the model page.

1. **A `corpus` block on every model entry**, directly after `researcher`:

   ```json
   "corpus": {
     "kind": "llm-synthetic",
     "generators": ["claude-sonnet-4-6"],
     "source": "1,000 TinyStories-register stories, written over the Claude API (batch)",
     "provenance": "projects/gatsby/data/costs.jsonl"
   }
   ```

   `kind` is one of `human`, `procedural`, `llm-synthetic`,
   `engine-synthetic`, or `mixed` (a corpus that combines kinds — pona's
   fetched human text interleaved with LLM dialogues). `generators` lists
   the credited authors by id and may be empty. `source` is one
   human-readable line of origin. `provenance` is the repo path to the
   committed record — a manifest, a cost log, a generator script — or
   `null` when no such record exists. Where a frozen snapshot carries its
   own copy of the record, the path points there; otherwise at the
   project's `data/`.

2. **A `generators` roster**, a top-level map separate from `researchers`.
   Entries mirror the researcher shape:

   ```json
   "fairy-stockfish": { "name": "Fairy-Stockfish", "vendor": "Fabian Fichter and contributors", "kind": "engine", "served_by": null, "url": "…" },
   "granite-4-1-8b":  { "name": "Granite 4.1 8B", "vendor": "IBM", "kind": "llm", "served_by": "LM Studio (local)", "model_id": "granite-4.1-8b" }
   ```

   `kind` is `llm` or `engine`; `served_by` names the surface the studio
   drove it through (`Claude API`, `LM Studio (local)`, or `null` for a
   binary). Ids are stable slugs: Claude models use the API model id, local
   models use the LM Studio id normalised to a slug with the exact id kept
   in `model_id`, the engine is `fairy-stockfish`. The two rosters stay
   separate because they answer different questions; when one id appears
   in both, they may merge into a single roster with per-role fields. That
   is a later ADR.

3. **Who is credited.** Models are: LLMs called over an API or served
   locally, and chess engines used as self-play generators. Fairy-Stockfish
   is credited on purpose — it is an algorithm with a hand-tuned evaluation,
   and some would call that a very simple model; the studio calls it one
   in the loose sense and puts its name on the page. **Who is not.**
   Deterministic scripts (kenosha-kid's `generate.py` enumerates
   permutations from a seed; no judgement was exercised) and human sources
   (Project Gutenberg, Lichess players, the google/fonts designers,
   Tatoeba and Wikipedia contributors). Those corpora get a `kind`, a
   `source`, and a `provenance`, with `generators: []`. The line is
   "did something make choices about the text": a search tree does, a
   permutation loop does not, and human authors are cited in the source
   line and the model card's credits rather than entered in a roster of
   machines.

4. **The site** resolves ids through `generatorName()` and renders one
   `Corpus` row in the spec table, after `Researcher`: the kind in words,
   the credited names, the source. Model cards do not restate it — the
   details table is the one home, exactly as for the researcher.

5. **Integrity.** `check_integrity.py` requires the block on every model,
   a valid kind, generator ids that exist in the roster, and a provenance
   path that is a file in the tree (or `null`). A corpus whose author
   cannot be established from a committed record is written `source:
   "unknown"` and said so in the release report, never guessed.

6. **Backfill.** All twelve releases were filled from committed evidence:
   the gatsby cost log and mixture manifest, pona's dialogue manifest,
   glyph's pinned fonts manifest, daydream's frozen `fetch_filtered.py` and
   shared `selfplay.py`, and the frozen `prepare.py`/`generate.py` of the
   rest. None needed `unknown`.

## Consequences

- "Who wrote this model's corpus" is a query on `registry.json` and a row on
  every model page. The seven LLMs and one engine that have written training
  text for the studio each have one spelling.
- Two standing obligations per release: fill the `corpus` block, and add
  any new generator to the roster first. The handbook's release checklist
  and the root `CLAUDE.md` carry the rule; the checker enforces it.
- Blend shares and per-model counts stay in the manifests, not the
  registry. The registry says who; the provenance file says how much.
- `mixed` hides the ratio. pona's page credits three local models beside
  a corpus that is 95% human text; the source line carries the shape, and
  the manifest carries the numbers.
- A model that both writes a corpus and does the research will appear in
  two rosters under the same id until the merge ADR lands. Accepted; the
  duplication is one entry.
- Fairy-Stockfish's `vendor` names the project's maintainer and
  contributors rather than a company. The roster's `vendor` field now
  means "whoever is responsible for the generator", which is what it
  already meant.

## Alternatives considered

- **One merged roster with a `roles` field.** Simpler to resolve, but the
  site and every published report's frontmatter depend on `researchers` as
  it stands, and no id yet appears in both. Deferred until one does.
- **Credit everything, scripts included.** A roster entry for
  `generate.py` would put a permutation loop beside Claude Sonnet 4.6 and
  make the word "generator" mean nothing. Scripts are provenance, not
  authors.
- **Credit no engine.** Fairy-Stockfish played 6,236 games against itself
  for Micro and Grand; leaving it off would make both corpora look
  authorless. The user's call: an engine is a model in the loose sense,
  and gets the credit.
- **A body line in each model card.** Rejected for the same reason
  ADR-0013 removed the `**Researcher:**` line in 2026-07: two homes for one
  fact, and the details table already renders from the registry.
- **Free-text `corpus_by` strings.** Rejected: "Gemma 4 (26B)", "Gemma 4
  26B A4B (QAT)" and `google/gemma-4-26b-a4b-qat` are three spellings of
  one generator; ids and a roster are what make the credit comparable
  across releases.
