# ADR 0022: Daydream is a three-tier board-size family, and the first sampler/prober project

- **Status:** Accepted
- **Date:** 2026-07-02
- **Deciders:** Romello Goodman (with Claude)

## Context

Every existing project in this monorepo (shakespeare, gatsby, kenosha-kid)
is *one* corpus, *one* tokenizer, *one* config, *one* trained model, riding
or vendoring the shared training engine. `docs/monorepo-plan.md` and
`docs/TODO.md` already sketched a `daydream` project in one line — "chess
move generation, builds on shakespeare" / "generates next move until
valid" — but the shape that emerged from design is considerably more
elaborate than that sketch, and diverges from the established one-project/
one-model pattern in two ways at once.

First: daydream is explicitly a **family of three models** (Micro 5×5,
Regular 8×8, Grand 12-file×10-rank), each with its own corpus, its own
character-level vocabulary (square names depend on board dimensions, so
vocabularies cannot be shared), and its own trained checkpoint — named
after the model-tier pattern (Haiku/Sonnet/Opus) but keyed to board size.
This is not "one project, one model" and not really "one project, N
unrelated models" either — the three are a deliberate set, meant to be
switched between in the player with the board itself visibly shrinking or
growing.

Second: daydream's core mechanic isn't generation quality, it's what
happens to *illegal* output. Every prior project either has no notion of
"illegal" (free text generation) or treats correctness as the goal.
Daydream inverts that: illegal moves are rendered as dim near-misses
instead of being masked away, and the sampler's job (resample-until-legal,
soft-capping as a "dreaminess" knob) is the artistic surface, not a
correctness mechanism to hide. That makes this the first project in the
monorepo whose primary faculty is *sampling/rendering* rather than
*generation* — what the design process called a Regime 2 "sampler/prober"
project, distinct in kind from the text-generation projects that came
before it.

## Decision

We will build `daydream` as:

1. **A single project directory** (`projects/daydream/`) riding the shared
   `core/` engine directly, the same way shakespeare and kenosha-kid do —
   **not** vendoring a separate engine like gatsby (ADR-0011). Nothing
   about chess required forking `core/nanogpt_core`: tokenization is
   char-level over each tier's UCI move alphabet, which fits the existing
   `meta.pkl` contract (ADR-0012) with zero core changes.
2. **Three independent sub-pipelines inside that one project**, one per
   tier, each with its own `data/<tier>/` corpus directory, its own
   `config/<tier>.py`, and its own frozen release folder at release time
   (`models/daydream-chess-nanogpt-<tier>-N/`, with Regular's tier name
   omitted from the id — `daydream-chess-nanogpt-1` — since it's the
   implicit default board size). A release of any one tier is a **new**
   frozen folder for that tier only; frozen folders are never refactored to
   share code with each other or with `core/`, per the standing releasing
   rule.
3. **One shared harness** (`harness.py`) and **one shared engine client**
   (`engine_client.py`), parameterized by tier, used identically for
   self-play corpus generation (Micro/Grand) and for post-training
   verification (all three tiers) — this is the sampler/prober machinery
   itself, and it's deliberately tier-agnostic so verifying Micro doesn't
   require different code than verifying Grand.
4. **Verification, not benchmarking, as the release gate.** Per the design
   plan, the automated gate a tier must clear before release is exactly
   two things — games complete without crashing, and legal-move rate
   clears a threshold — not win rate against an opponent and not a
   subjective read on dream quality. That keeps the gate honest about what
   this project is actually for (a working sampler/renderer, not a strong
   chess engine).

## Consequences

**Easier:**
- Anyone opening `projects/daydream/` sees the tier structure immediately
  (`data/{micro,regular,grand}/`, `config/{micro,regular,grand}.py`) rather
  than having to infer it from scattered files.
- The shared harness means a bug fix or a metric change lands once and
  applies to all three tiers' verification runs, not three copies.
- Future sampler/prober projects (the design docs mention Really Bad Chess
  as a parked probe on a frozen model) have a real precedent to follow
  instead of inventing the shape from scratch.

**Harder / debt accepted:**
- **Three tiers means three of almost everything at release time**: three
  corpora, three configs, three frozen model folders, three model cards,
  three `registry.json` entries. This is more release-process overhead per
  research round than any prior project in this monorepo has had.
- **No shared vocabulary or checkpoint across tiers, by design** — this
  forecloses ever training "one daydream model that generalizes across
  board sizes" without a real architectural change (e.g. a board-size
  conditioning token and a superset vocabulary), which is explicitly out of
  scope for this decision and would need its own ADR if pursued later.
- **The "sampler/prober" framing is new enough that there's no established
  convention yet for what a model card should say about it** (existing
  model cards describe generation quality; daydream's model cards need to
  describe legal-move rate and dream-rendering behavior instead, alongside
  or instead of BPC). We're setting that convention with this project's
  model cards rather than inheriting one.

## Alternatives considered

- **One tier only (Regular), defer Micro/Grand.** Rejected: the board-size
  triptych and its "switching models visibly shrinks/grows the board" UI
  idea is the anti-marketing thesis the project was designed around — a
  single-tier release wouldn't be daydream as designed, just a chess-move
  GPT.
- **Separate top-level projects per tier** (`projects/daydream-micro/`,
  `projects/daydream-regular/`, `projects/daydream-grand/`). Rejected: the
  three tiers share a harness, an engine client, and a design thesis tightly
  enough that splitting them into unrelated projects would mean either
  duplicating that shared machinery three times or introducing
  cross-project imports this monorepo doesn't otherwise have — worse than
  the three-sub-pipelines-in-one-project shape we chose.
- **Bend an existing project's shape to fit chess** (e.g. extend
  shakespeare). Rejected outright by the sampler/prober distinction above —
  daydream's core mechanic (render illegal output, don't discard it) has no
  analog in a pure text-generation project, and forcing the fit would
  obscure exactly the thing that makes this project different.
