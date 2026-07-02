# sup computer — monorepo plan

**sup computer: a small language model studio**

> **Archived (July 2026).** This is the original planning document, kept as
> historical rationale — it is not maintained and parts no longer match the
> tree. The living docs are [ADR-0001](adr/0001-adopt-a-monorepo.md) (the
> decision) and [`architecture.md`](architecture.md) (the as-built map); the
> open items that survived it live in [`TODO.md`](TODO.md). See
> [ADR-0020](adr/0020-one-home-per-fact.md) for why it's marked rather than
> updated.

---

## Why a monorepo

The copy-paste pain (train.py, export.py, eval logic duplicated across repos) is a package problem solvable without merging trees. The thing that actually tips the decision is the cross-project studio surface: a website, a Claude-managed research blog, a model registry, and data viz skills. Those surfaces have to read across every project simultaneously. Keep them in separate repos and you're permanently syncing artifacts across boundaries at build time.

The Claude-managed blog is the deciding factor. If the blog lives apart from the experiments, Claude can't read run outputs, configs, and model cards while drafting a post. The blog is the lab notebook; it has to sit next to the experiments or it's writing from memory. The monorepo makes receipts always one directory away.

---

## Layout

```
supcomputer/
  core/                    # the thing that was being copy-pasted, now once
    nanogpt_core/          # train loop, model, Muon/AdamW grouping, schedules
    eval/                  # val_bpb, holdout discipline
    export/                # export.py — ONNX, quant, manifest emit
    curation/              # curation console backend
  projects/
    shakespeare/           # config + corpus pointer + model card + thin train call
    daydream/              # chess move generation, builds on shakespeare
    small-hours/           # synthetic data → time-based poem UI, builds on gatsby
    gatsby/                # synthetic data generation + refinement + training
  player/                  # @supcomputer/player — load/run nanogpt models in browser (JS/ONNX)
  site/                    # studio website + research blog (Astro content collections)
  skills/                  # data viz skills, agent prompts, runbooks
  registry.json            # model manifest the site + player both consume
```

Each project stays thin: a config, a corpus pointer, a model card, and `from nanogpt_core import ...`. The core is editable-installed so refactoring core + every consumer happens in a single atomic PR.

---

## Projects

| Project | Description | Builds on |
|---|---|---|
| shakespeare | Base model trained on Shakespeare. Proves Claude as researcher. | — |
| daydream | Base model trained on chess moves. Generates next move until valid. | shakespeare |
| gatsby | Generate and refine synthetic data, then train on it. | shakespeare |
| small-hours | Synthetic data pipeline with a time-based poem UI. | shakespeare, gatsby, daydream |
| player | Load and run nanogpt models in the browser (JS/ONNX). | — |

---

## Hard rules

**No weights, no large corpora in the tree.** This is the rule that decides whether the monorepo stays alive or rots. Checkpoints and generated corpora live in GitHub release artifacts (or R2), referenced by `registry.json` and per-project manifests. `projects/*/` holds config, card, and a pointer — never the `.pt`. The moment weights land in-tree, clone time balloons and the "legible, browsable studio" value inverts.

**Each `projects/*/` README must stay self-describing.** The monorepo erodes per-project legibility if a reader can't clone sparse and understand one project in isolation. Guard this.

---

## Bringing shakespeare-nanogpt in

Use `git subtree add` under `projects/shakespeare/`, preserving history. Don't rewrite or flatten — that repo's leaderboard and model-card history is the "proves Claude as researcher" provenance.

```bash
git subtree add --prefix=projects/shakespeare \
  https://github.com/<org>/shakespeare-nanogpt main --squash
```

---

## Tooling

- Python: `uv` workspace, `core/` editable-installed into each project
- JS: `pnpm` workspace for `player/` and `site/`
- Blog: Astro content collections under `site/src/content/posts/` — Claude writes posts with raw numbers and config paths cited so readers can diff the narrative against primary artifacts in the same tree

---

## Naming

| Surface | Form |
|---|---|
| Wordmark | sup computer |
| npm scope | `@supcomputer/*` |
| CLI verb | `sup` (e.g. `sup train`, `sup export`, `sup blog`) |
| Tagline | a small language model studio |

"Open-source" is demonstrated by the repo, not declared in the tagline. "Small" is load-bearing — it's the entire medium thesis. Never cut it.
