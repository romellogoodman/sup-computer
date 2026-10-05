---
title: "Does a one-desk studio need a model factory?"
type: note
researcher: claude-opus-5-5
date: 2026-10-04T23:40:00-04:00
summary: >
  The studio doesn't need Savanna, Aleph Alpha's training-as-code factory, but
  it lacks the receipt Savanna writes for every run. Nothing here says which
  commit made which checkpoint.
takeaways:
  - >-
    **Savanna is code, not config.** Aleph Alpha's pipeline is imperative
    Python-shaped functions launched from GitHub CI; a sweep is a `for` loop,
    and a workflow engine caches every stage whose inputs repeat.
  - >-
    The post's three hidden costs (human error, forgotten learnings,
    fragmented ownership) are a large lab's costs. Two of the three need
    teams to exist.
  - >-
    The studio's gap is narrower: a glyph run dir holds a checkpoint, a
    harness JSON and samples, and none of them names the commit or the corpus
    build that produced it.
---

# Does a one-desk studio need a model factory?

Aleph Alpha trains its models by pushing to GitHub. Its "model factory",
codenamed Savanna, holds the whole training pipeline in imperative code, and
CI on `main` trains the company's best model with one click. Michael Barlow
described it on 22 May 2026 in
[Model Training as Code](https://aleph-alpha.com/en/blog/model-training-as-code/),
and the studio read it asking one question: should sup computer build one?

## The problem Savanna names

The post opens on cost. "When you're burning thousands of GPU hours, 'oops'
is an expensive word." It then walks one model through a manual lab and finds
three hidden costs.

- **Human error.** A storage quota fills two weeks into a pre-training run.
  Nobody knows whether the 30TB dataset with `do_not_delete` in its name is
  safe to delete, the GPUs sit idle, and the relaunch is rebuilt "from memory
  and Slack threads, hoping they didn't forget to set a flag."
- **Forgotten learnings.** The SFT team repeats sweeps it already ran against
  an earlier checkpoint. The reasons behind each hyperparameter are scattered
  "across Slack, the filesystem, an experiment manager and various wiki pages."
- **Fragmented ownership.** The RL model underperforms, and two weeks of
  debugging blames the SFT checkpoint. Neither team could run the other's
  stage, so each had tuned its own slice instead of the model.

The diagnosis is one sentence: "the pipeline lives in the minds of the team
rather than in a shared, durable artefact."

## What Savanna is

Savanna is code, not a config file with a launcher. A post-training pipeline
is an async function that awaits SFT, spawns an eval, awaits RL on the SFT
checkpoint, and returns both evaluations. Configs still exist, but they are
the arguments; the code owns the order. The post claims three things from
this: composability (stages are typed functions you can loop over or shrink),
consensus (`main` is the team's current best recipe), and provenance (commits
and comments record why).

The rest is engineering culture and infrastructure:

- **Trunk-based development.** Small changes land on `main` early, because
  long-lived branches "pay the same integration debt as before."
- **CI as the entrypoint.** A pull request runs a small end-to-end training
  job in under 5 minutes. A larger run every night asserts that the
  resulting model improves on the eval suite.
- **Sweeps as loops.** The post's example calls `post_train` four times over
  two SFT and two RL learning rates. The SFT stage runs twice, not four
  times, because the engine reads repeated stages from its cache.
- **Immutable artefacts.** Data, models and tokenizers are versioned in a
  registry, so "to determine which models were trained on a specific
  dataset, you use the artefact lineage graph, not Slack search."
- **The stack.** Flyte on Kubernetes runs the jobs; artefacts sit in an
  on-prem object store, versioned in Weights & Biases.

Savanna is not a library you can install. The post shares pseudocode and no
repository, so everything above is a description, not something the studio
can run.

## What it claims to have bought

No numbers. The claims are qualitative: experiments launch and evaluate
themselves, so effort moves to analysis. The last large pre-training run was
relaunched several times without risk, and "whoever was on hand could safely
pick it up." Teams now own a capability end to end rather than a stage; a
multilinguality team builds the SFT data, RL environments and evals for
German. The closing ambition is auto-research: with the pipeline in code, "an
LLM agent can read, modify and run it autonomously."

## Reading it from one desk

The studio is one director and a Claude model, training 0.8M–48M-parameter
models on one Mac, in runs of minutes to hours. Two of Savanna's three costs
assume teams. There is no handoff between an SFT team and an RL team when
both are the same session. The six projects also share little beyond
`core/`: a chess engine, a font rasterizer, a toki pona dialogue corpus and
one Pynchon sentence don't fit a common stage interface without wrapping each
in a new one.

Some of Savanna's provenance is already here. A release is a frozen folder
pinned to a git tag, `registry.json` credits the researcher and the corpus
generators, and each project's `research/log.md` records the reasoning. What
is missing sits one level down, at the run. Glyph has 32 run directories; a
typical one holds `ckpt.pt`, a harness JSON and samples. The checkpoint
carries its hyperparameters (nanoGPT saves the config dict inside it), but
not the commit that trained it or the corpus build it read. The factory is
optional. The receipt isn't.

You could say the studio is exactly where Aleph Alpha wants to go, an agent
running the research, so it should be first to build the factory. It already
has the half that matters for an agent. The pipeline is readable today
through each project's README, CLAUDE.md and log. What an agent cannot read
is which commit made which checkpoint, and a factory isn't needed to fix
that.

## What the studio left unbuilt

The planning session that produced this note sketched a scaled-down Savanna
in five pieces: a stage contract with hash-keyed caching in `core/`, a
`recipe.py` per project, a `run.json` receipt per run, a `sup run` command,
and a CI smoke job. It cut the last two first. The director doesn't train
through the CLI, and CI already runs `pytest core/tests/` on every push, so a
smoke test needs no new workflow. A wider restructure of the repo was offered
and declined, since the current layout is backed by ADRs and nothing
specific hurts.

Then everything was deferred. The cheapest piece left is the receipt:
`core/nanogpt_core/train.py` writing the commit, a dirty-tree flag, the
resolved config, a corpus hash and final losses into each run dir, in
roughly 50 lines. If a recipe file ever arrives, the likely first project is
`pointing`, the next model on the list, built recipe-first rather than
retrofitted.

## Limits of this reading

- One source, and a vendor blog. Every claim about Savanna is Aleph Alpha's
  own, with no measurement attached.
- The 50-line estimate for `run.json` is a guess, not a built thing.
- The verdict is about this studio's size. At more people or longer runs,
  the second and third hidden costs arrive, and the answer changes.

Savanna is the right answer to a coordination problem the studio doesn't
have yet. The factory is optional. The receipt isn't, and it is the piece to
build when training starts again.

## Credits

- Written by Claude Opus 5.5 from a planning session with Romello Goodman,
  who called the deferral.
- Source: Michael Barlow, [Model Training as Code](https://aleph-alpha.com/en/blog/model-training-as-code/),
  Aleph Alpha Research, 22 May 2026.
