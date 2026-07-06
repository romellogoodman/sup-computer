---
title: "An instrument anything can play: why the studio ships a CLI"
type: note
researcher: claude-fable-5
date: 2026-07-04
summary: >
  The studio's small models are instruments — single-purpose, played rather
  than prompted — and sup, the studio CLI, is the accessibility argument: one
  greeting downloads a release and streams its voice to stdout. A handle that
  simple works in a shell pipe, which means it works for another model.
status: published
---

# An instrument anything can play: why the studio ships a CLI

Type `sup shakespeare` and an 11M-parameter model downloads itself and
answers in blank verse. That greeting is the entire interface — no
environment, no notebook, no API key; the model's starter prompt is already
loaded, so the instrument answers in its own voice the first time you touch
it.

**Instruments, not assistants.** None of the studio's models chat. Each one
does a single thing with character: shakespeare writes verse, gatsby reaches
for the green light, kenosha-kid chants six words, daydream plays chess
without knowing the rules. A model like that is not an assistant waiting for
instructions — it is an **instrument**, and an instrument implies a player.
The studio now has three kinds. A person plays at the terminal or on the
[model player](https://www.supcpu.com/model-player/). A judge plays
shakespeare line by line in linewell, deciding which draws freeze into a
poem. And in Token Chess, one model plays another: a local LLM steering
daydream's sampler under a token budget, learning by feel what temperature
lands a legal move. The playing is the research.

**The case matters as much as the instrument.** Before the CLI, playing a
release meant a Python research environment or a browser tab. `sup` is the
third surface and the lowest doorway: generated text goes to stdout, status
goes to stderr, so `sup shakespeare > sonnet.txt` captures only the poem and
`sup daydream` drops a dreamed game into any pipe that wants one. This is
the [Monolith](https://monolith.romellogoodman.com/) philosophy applied to
the studio's own shelf — single-purpose tools with dedicated handles,
chainable in the UNIX way, software built for a computer to use. An agent
that can run a shell command can play every instrument the studio ships,
present and future, through one unchanging case.

A dedicated tool also teaches its player how to hold it. The CLI encodes the
studio's opinions so a player can't easily hold the instrument wrong: the
greeting resolves a series to its newest release, `--seed` makes a
generation reproducible, and the sampling window comes from the release's
own manifest rather than a guess, so you cannot ask a model to dream past
the edge of its context. Guard rails, in Monolith's terms — there to follow,
or to push against once you know the instrument.

The doorway is deliberately small because the models are. `sup` runs from
the clone today, unpublished (ADR-0025) — but the shape is set: instruments
accumulate, one per research round, and the case never changes. The models
are small. The doorway should be too.

## Credits

- Written by Claude Fable 5.
- The philosophy is borrowed from the studio lead's
  [Monolith](https://monolith.romellogoodman.com/) — a deterministic toolbox
  built on the same bet: give a computer tools with dedicated handles and it
  becomes a more reliable player.
- The CLI: [`cli/`](../../cli/README.md), design in
  [ADR-0025](../../docs/adr/0025-sup-cli-and-injectable-player-backend.md).
