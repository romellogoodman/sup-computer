# kenosha-kid

> **A char-level GPT that knows only six words — and dreams in them.**

A tiny character-level GPT whose **entire corpus is punctuated permutations of one
six-word phrase**: *you never did the kenosha kid* — the telegram Tyrone Slothrop
reconstrues under sodium amytal in Pynchon's *Gravity's Rainbow* (I.10), and the
seed of Darius Kazemi's [@YouNeverDidThe](https://x.com/youneverdidthe) bot. It
can only ever say those six words; what it *does* is reorder, repunctuate, and
recapitalize them.

```
You! Never! Did the, Kenosha Kid
Kenosha, kid never 'did' -- the...
'You' the did never Kenosha, Kid
You never did the Kenosha kid?
The never did you. Kenosha Kid?
```
*(the model given only a newline at temperature 0.9 — orbiting the phrase)*

The piece is about the gap between a **bot** and a **learned model**. The bot is
`itertools.permutations`: flat, exact, dead. A net approximates a distribution,
and the approximation is always a little blurry — sampled warm it keeps returning
to the six words but keeps landing slightly differently (drifted punctuation,
near-misses like "Kenoshar"). **Orbit, don't enumerate; the blur is the
artifact.** Verbatim convergence is the failure mode, not the goal.

This is a **sibling** of [`shakespeare`](../shakespeare/) and
[`gatsby`](../gatsby/), but unlike them it rides the monorepo's shared
[`core`](../../core/) engine **directly** — no vendored base engine. `core`
already honors `meta.pkl` as a char-level tokenizer contract end-to-end, so
nothing in `core` had to change (see
[ADR-0012](../../docs/adr/0012-pluggable-tokenization.md)). The agent conventions
are in [`CLAUDE.md`](CLAUDE.md); the lineage is in
[`docs/sources.md`](docs/sources.md).

## How it works

The corpus is **synthetic and in-repo**: `generate.py` is a deterministic
reimplementation of Kazemi's bot, so we own the generator rather than scraping it.
That keeps the corpus frozen and inspectable, and — the real reason — lets us
**weight** it. Pynchon's nine canonical construals are folded in as ~18%
high-frequency anchors over the brute-force permutation tail, giving the model a
preference manifold (crisp anchors, dim tail) instead of a flat enumeration.

Char-level is load-bearing: punctuation and capitalization carry the whole signal,
and the near-miss drift lives *below* the BPE token boundary — so chars, not BPE.

## Pipeline

Run everything from the **repo root** via `uv run`:

```
generate.py            ->  data/raw.txt              (deterministic, SEED=1973 — committed)
prepare.py             ->  data/kenosha/{train,val}.bin + meta.pkl
core train.py          ->  runs/<r>/ckpt.pt          (~2 min on Apple Silicon)
core sample.py         ->  the dream
```

```bash
uv run python projects/kenosha-kid/generate.py          # writes data/raw.txt
uv run python projects/kenosha-kid/prepare.py           # -> train/val.bin + meta.pkl
uv run python core/nanogpt_core/train.py projects/kenosha-kid/config.py
uv run python core/nanogpt_core/sample.py \
    --out_dir=projects/kenosha-kid/runs/champion \
    --device=cpu --temperature=0.9
```

`config.py` reproduces the champion with no extra arguments; capacity
(`n_layer`/`n_embd`) and `max_iters` are *aesthetic* knobs here (smaller/shorter
blurs more), not just performance. Mac settings: `device='mps'`, `compile=False`.
Note `core`'s `sample.py` defaults to `--device=cuda`, so pass `--device=cpu` (or
`mps`) on an Apple Silicon Mac.

## The champion

[`kenosha-kid-nanogpt-1`](../../research-docs/model-cards/kenosha-kid-nanogpt-1.md)
— run `r3-mid`, **350 iters, best val 0.48**, sampled at **temperature 0.9**.
~0.79M params (4 layers, 4 heads, 128 dim, 128 context).

It is **deliberately not the lowest-loss checkpoint.** Dreaminess has two knobs —
training progress (the memorization phase transition) and sampling temperature.
Undertrained (150 iters) the words break at the character level; converged (2000
iters, val 0.43) the spellings lock and the dream flattens to order/punctuation.
350 iters is the balance, and verbatim convergence is a *worse* artifact, so we
stop mid-transition on purpose.

## Showcase

```
The, Kenosha you Kid never did
You! Never did the Kenosha Kid!
Kid you did Kenosha the Kid never
You never did the Kenosha kid?
Kenosha Kid did... Never the... You
You the kenoshayou you did... Never.
```
*(raw, uncherry-picked — anchors surface, the tail orbits, a near-miss leaks in)*

More in [`research/samples.md`](research/samples.md), including the full
phase-transition spectrum.

## Research notes

This is a research project, so the data and the reasoning are part of the record:

- **The corpus is committed** (`data/raw.txt`, regenerates byte-for-byte from
  `generate.py`); weights and derived `.bin`/`.pkl` are gitignored — they rebuild
  deterministically (no weights in the tree,
  [ADR-0002](../../docs/adr/0002-no-weights-in-tree.md)).
- **[`research/log.md`](research/log.md)** is the running journal (why each
  decision was made); **[`leaderboard.md`](leaderboard.md)** is
  the per-run scoreboard.
- The full write-up is
  [`experiment-03.md`](../../research-docs/reports/dream-a-single-phrase.md); the frozen,
  self-contained release is
  [`models/kenosha-kid-nanogpt-1/`](models/kenosha-kid-nanogpt-1/).

## Credits

- The shared [`core`](../../core/) engine (modern nanoGPT lineage — RoPE,
  RMSNorm, bias-free).
- Darius Kazemi, [@YouNeverDidThe](https://x.com/youneverdidthe) (2013) — the bot
  `generate.py` reimplements. Kazemi open-sources his bots.
- Thomas Pynchon, *Gravity's Rainbow* (1973), I.10 — the phrase and its nine
  construals; reproduced here as a behavior, not its text. Full provenance in
  [`docs/sources.md`](docs/sources.md).
- Built with **Claude** ([Claude Code](https://claude.com/claude-code)).
