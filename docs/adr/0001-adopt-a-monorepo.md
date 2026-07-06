# ADR 0001: Adopt a monorepo for sup computer

- **Status:** Accepted
- **Date:** 2026-06-27
- **Deciders:** Romello Goodman (with Claude)

## Context

The model work was spread across separate repos, with the train, export, and eval
logic copy-pasted between them. That copy-paste pain is real, but it's a *package*
problem — solvable without merging trees, by extracting a shared library.

The thing that actually tips the decision is the cross-project studio surface: a
website, a Claude-managed research blog, a model registry (`registry.json`), and
dataviz. Those surfaces have to read across every project at once — run outputs,
configs, model cards. Keep them in separate repos and you are permanently syncing
artifacts across boundaries at build time.

The blog is the deciding factor. It is the lab notebook, and a lab notebook has to
sit next to the experiments it describes. If the blog lives apart from the runs,
Claude can't read real run outputs, configs, and model cards while drafting a post —
it writes from memory instead of citing primary artifacts. The point of the studio
is that a reader can diff the narrative against the receipts, so the receipts have
to be one directory away.

The origin of this rationale is `monorepo-plan.md`, the pre-monorepo planning
doc — removed from the tree once it went stale (recover it with
`git log --diff-filter=D -- docs/monorepo-plan.md`).

## Decision

We will keep everything in one monorepo with a small, fixed top-level shape:

```
core/            the shared engine (model, train, sample, eval, export)
projects/        one folder per model series (shakespeare/ is the first)
tools/           researcher tooling (dataviz, cost accounting)
research-docs/   cross-project reports + model cards (the lab notebook)
website/         the studio site; consumes content, owns none
registry.json    the model manifest the site and player both read
```

Each project stays thin — a config, a corpus pointer, run evidence, a model card,
and `from nanogpt_core import …` — so the receipts a blog post needs are always in
the same tree as the post.

## Consequences

- Refactoring `core/` and every consumer is one atomic change in one commit — no
  cross-repo version dance.
- The blog and website can cite real run outputs, configs, and cards because they
  are all "one directory away."
- Two things now have to be actively guarded, or the monorepo rots:
  - **Weights and corpora must stay out of the tree** — committing them inverts the
    "legible, browsable studio" value ([ADR-0002](0002-no-weights-in-tree.md)).
  - **Per-project legibility must not erode** — a reader cloning one project sparse
    has to understand it in isolation, so each `projects/*/README.md` stays
    self-describing.

## Alternatives considered

- **Separate repos + a shared pip package for `core/`** — rejected. It solves the
  copy-paste problem but not the deciding one: the blog still can't read across
  repos, so the studio is back to syncing artifacts across boundaries at build time
  forever. The package is necessary but not sufficient.
