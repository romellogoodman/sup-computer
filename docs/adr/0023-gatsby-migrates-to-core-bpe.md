# ADR 0023: gatsby migrates onto the modern core engine with byte-level BPE

- **Status:** Accepted (supersedes [ADR-0011](0011-vendor-gatsby.md))
- **Date:** 2026-07-02
- **Deciders:** Romello Goodman (with Claude)

## Context

[ADR-0011](0011-vendor-gatsby.md) vendored gatsby as a **self-contained** project
that kept its own copy of the base char-level engine and did **not** consume
`core/`, explicitly *deferring* the migration onto core's modern engine as "a
training follow-up — a research change, not a vendoring one." That deferral is
`docs/TODO.md` item 2.

The forcing function is gatsby's one persistent failure. Across v1→v2 the green
light reliably barges in and (by v2) the `green=N` dial moves, but the model does
not tell the story you asked for: obsession-on-a-dial §6 documents "a robot who
wanted a friend" → *a rabbit*, "a clock that lost its tick" → *a cloud*. §6 names
the structural fix directly: the root cause is **char-level conditioning on a
short prefix** — the tag and the topic word reach the model as long strings of
low-weight characters dozens of positions back — and the fix is to move
conditioning **off characters onto BPE tokens**, so "robot" and `green=5` are one
or two high-mass tokens instead of character strings.

Two prior decisions make this cheap to attempt:

- [ADR-0012](0012-pluggable-tokenization.md) established that tokenization is
  **pluggable on core with `meta.pkl` as the contract** — no core fork needed.
- shakespeare's r5 XL round built the concrete pattern: a small custom
  **byte-level BPE** trained with the HF `tokenizers` lib, a `meta.pkl` carrying
  `{vocab_size, tokenizer}`, and project-local `eval_xl.py`/`sample_xl.py` that
  resolve the tokenizer from that seam (core's own sample/eval understand only
  char `stoi` or GPT-2 BPE).

That round also produced a hard lesson: **large-vocab BPE diverged on MPS**
because core's `GradScaler` is CUDA-only, so float16 autocast runs unscaled and
large logits overflow — instability that scales with vocab size.

This round holds the experiment to a **single variable**: the v2 corpus
(`data/raw.txt`, the 2000-story mixture, ~1.53M chars) is unchanged, so any
behaviour change is attributable to the tokenizer + engine switch alone.

## Decision

We will **migrate the active gatsby project off its vendored base char-level
engine onto core's modern engine (RoPE, RMSNorm, bias-free) with a small custom
byte-level BPE tokenizer**, superseding ADR-0011's "keeps its own base engine."

- **The active project rides `core`.** `prepare.py` trains a **1024-vocab
  byte-level BPE** on the corpus and writes `data/gatsby_bpe/`
  (`train.bin`/`val.bin` + `tokenizer.json` + `meta.pkl` = `{vocab_size,
  tokenizer}`). Training is `core/nanogpt_core/train.py` driven by `config.py`
  (dims held identical to gatsby-nanogpt-2 for comparability). Sampling and eval
  are project-local BPE-aware scripts (`sample.py`, `eval_dial.py`,
  `generate_samples.py`) sharing a small `_runtime.py` that loads core's `GPT` and
  resolves the tokenizer from the `meta.pkl` seam — mirroring shakespeare's
  `eval_xl.py`/`sample_xl.py` ([ADR-0012](0012-pluggable-tokenization.md)).
- **The vendored engine is removed from the active tree** (`model.py`,
  `train.py`, `configurator.py` deleted from `projects/gatsby/`). gatsby's bare
  `from model import` scripts are rewired to `from nanogpt_core.model import`.
- **We train in float32 with a small vocab on MPS**, sidestepping the CUDA-only
  `GradScaler` overflow that diverged shakespeare's large-vocab run. gatsby is a
  ~11M model; float32 on MPS is plenty fast.
- **Frozen releases are untouched.** `gatsby-nanogpt-1` and `gatsby-nanogpt-2`
  keep their vendored base engine inside `projects/gatsby/models/*` — the
  frozen-release rule ([ADR-0003](0003-frozen-self-contained-releases.md)) says a
  release is a runnable snapshot pinned to its tag; this migration is the *active*
  project only. `tokenizer.json` is committed (a small text artifact, not a
  weight, matching shakespeare's precedent); `*.bin`/`*.pkl`/`*.pt` stay
  gitignored.

## Consequences

- gatsby now shares **one living engine** with shakespeare and kenosha-kid.
  ADR-0011's accepted debt — "a third copy of the base engine" — is repaid: the
  active copy is gone, the frozen copies remain (correctly).
- **The control line is now high-mass tokens.** `[green=5] [green=5] [green=5]
  obsession=total\ntopic: …` tokenizes with `green`, the level digit,
  `obsession`, `total`, and `topic` each as a single token — ~a dozen strong
  tokens instead of ~45 low-weight characters. This is the structural change §6
  called for.
- **It fixed the dial** (the dimension the stronger control-line signal most
  directly drives): green mentions per 480 chars are **strictly monotonic
  2.08 / 3.67 / 4.08 / 5.67 / 8.08** across levels 1→5, versus v2's
  3.72 / 4.78 / 4.67 / 4.50 / 6.06 (which inverts at L3→L4 and compresses the
  middle). The dynamic range roughly doubled and the ordering is now clean.
- **It did NOT fix topic-honoring — the headline hypothesis.** On 15 held-out
  topics at green=2, ~**1/15** are clearly on-topic (spider spinning a web
  lands); the rest collapse to a generic "found a shiny X" opening plus the green
  light — "a robot" → a shiny rock, "a clock" → a red block, "a submarine" → a
  spaceship in the sky. This is essentially v2's failure. The BPE topic token
  occasionally seeds one concrete detail but does not anchor the narrative.
  Diagnosis: topic-honoring's bottleneck is **not** tokenizer strength but
  **corpus content** — the mixture stories frequently abandon their own topic once
  the green light appears, so "topic: X" is weakly correlated with story content
  no matter how strong the token — compounded by overfitting (below). Making the
  *dial* louder helped the dial; making the *topic* land needs the corpus to
  actually stay on topic.
- **BPE compresses the corpus ~3.1x** (1.53M chars → ~445k tokens), so the model
  sees each token far more often per iteration and **overfits fast**: val
  bottomed at **step 750 of 3000** (1.85) and rose to 2.58 by step 3000. With
  `always_save_checkpoint=False` the kept checkpoint is the step-750 best-val one.
  This is the key confound on the topic-honoring result: the model **overfits
  before it can learn topic conditioning**, the same small-corpus failure mode
  obsession-on-a-dial diagnosed (too few distinct topics, learned as templates
  rather than a topic→content map). A future round should **pair BPE with corpus
  enlargement** (more distinct topics via [`tools/synthgen`](../../tools/synthgen/README.md),
  and topic-faithful stories) **and train only ~750–1000 iters** (plus
  regularization) so conditioning is learned before overfitting sets in.
- **This is a research finding, not a release.** No new `models/` folder,
  `registry.json` entry, or model card is created this round; the migrated model
  is not shipped. Evidence lands in `projects/gatsby/research/log.md`,
  `leaderboard.md`, and `runs/migrate-bpe-r1-samples.md`.

## Alternatives considered

- **Stay on the vendored char engine** — rejected. That is exactly the deferred
  debt of ADR-0011 and TODO item 2, and the char prefix is the diagnosed weak
  signal that §6 says to replace.
- **Re-add the base architecture to core behind a flag** — rejected;
  [ADR-0004](0004-core-is-modern-only.md) stands, and the frozen release folders
  already preserve base for posterity.
- **A large BPE vocab (GPT-2 50k, or shakespeare's 16k)** — rejected. The corpus
  is tiny, and large-vocab float16 diverges on MPS. A small (1024) byte-level
  vocab keeps every control-line token frequent and well-trained, stays lossless
  (all 256 bytes in the initial alphabet), and trains stably in float32.
- **Regenerate or enlarge the corpus this round** — rejected. The point was to
  isolate the tokenizer + engine switch as a single variable against v2; the
  topic-honoring finding above is precisely what tells us the *next* round must be
  a corpus round, not another tokenizer round.
