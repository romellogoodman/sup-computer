# ADR 0040: Corpora publish as versioned datasets

- **Status:** Accepted (extends [ADR-0037](0037-crediting-the-corpus-generators.md) from models to the corpora themselves)
- **Date:** 2026-10-05
- **Deciders:** Romello Goodman (with Claude)

## Context

Every gatsby corpus so far has been a model artifact: a `raw.txt` committed
next to the project, read by `prepare.py`, credited on the model's page
(ADR-0037), and never released on its own. That worked while corpora were 1–2k
stories and 1–1.5MB.

gatsby-nanogpt-3 changes both halves. Its corpus is ~30k stories (~30MB with
its per-story records) written by DeepSeek V4.1 Flash for under $7, which is
too large for the tree under the root rule against large corpora. And the
studio wants the corpus to be a thing other people can use: generate one
large pool, release it, and train the model on a declared subset of it, so
the size of the subset becomes a research variable instead of an accident.

The three gatsby corpora also differ in kind, not just size. v1 was written by
Claude Sonnet 4.6, v2 by a four-model local blend, v3 by DeepSeek. Their
generator rosters, output terms and prompts are all different.

## Decision

We will publish corpora as **versioned datasets** on Hugging Face under the
`sup-computer` org, separately from the models trained on them.

- **One repo per dataset family, one folder per version.** The gatsby family
  is `sup-computer/tiny-green-light-stories`, with `v1/`, `v2/` and `v3/`
  declared as dataset configs (so the HF viewer and `load_dataset(..., "v3")`
  see each one) and a git tag per published version.
- **Versions are independent corpora, not cumulative.** v3 does not contain
  v1 or v2. A version number orders the corpora; it never implies
  containment. The dataset card says so up front.
- **One writer roster per version.** Each version credits exactly the
  generators that wrote it, with their ids from `registry.json`'s
  `generators` map, and notes their output terms.
- **Large corpora live on HF, not in the tree.** For v3 the repo commits the
  generator (`projects/gatsby/generate_v3.py`), the run record
  (`data/v3/manifest.json`, with every prompt and parameter) and the subset
  specs; the story text (`stories.jsonl`, 45MB) and the topic bank
  (`topics.json`, 3MB) are gitignored and published.
  Small corpora that are already committed (v1, v2) stay where they are.
- **Splits are by topic, and subsets are declared.** v3's train / val / test
  split assigns whole topics, so test subjects are unseen by any model
  trained on train. A model trains on a named, seeded subset
  (`subsets/train-10k.json`), published with the dataset.
- **The registry records datasets.** `registry.json` gains a `datasets` map
  (family id → name, HF repo, published versions with writer, counts, cost,
  provenance path). A model's `corpus` block adds `dataset`, `version` and
  `subset` alongside the ADR-0037 fields.
- **Publication waits on the terms check.** A version publishes only after
  its generators' output terms are checked. Tonight that is v3 (DeepSeek,
  MIT-licensed weights; outputs usable). v1 (Anthropic's terms on competing
  models) and v2 (Gemma's derivative clause, 20% of its stories) wait.

## Consequences

- A corpus can outlive and outgrow the model that motivated it; anyone can
  train on v3 or a subset of it and compare against gatsby-nanogpt-3.
- Reproducing gatsby-nanogpt-3 needs the HF dataset, not just a clone. The
  tree still holds everything needed to regenerate v3 (generator, prompts,
  seeds), at the cost of regeneration.
- The project's convention that `data/raw.txt` is committed now has an
  exception for corpora over a few MB; `projects/gatsby/CLAUDE.md` says so.
- Two places hold dataset facts (the HF card and `registry.json`). The
  registry is the source the site reads; the card is written from the same
  manifest.

## Alternatives considered

- **Commit v3 to the repo.** Breaks the root rule against large corpora and
  bloats every clone by ~30MB for a file nobody edits.
- **One HF repo per version.** Three repos that share a schema and a card
  are harder to compare than three configs in one; tags already give each
  version a fixed revision.
- **Make v3 a superset of v1 and v2.** Mixes three writer rosters into one
  version, so a story's credit would depend on when it was added, and
  "train on a random 2k of v3" would silently draw on older corpora.
- **Train on the whole pool, no subsets.** Loses the size sweep, which is
  the cheapest way to learn whether data was gatsby's binding constraint.
