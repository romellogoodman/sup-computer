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

The piece is about the gap between a *bot* and a *learned model*. The bot is
`itertools.permutations`: flat, exact, dead. A net approximates a distribution,
and the approximation is always a little blurry — sampled warm it keeps returning
to the six words but keeps landing slightly differently (drifted punctuation,
near-misses like "Kenoshar"). **Orbit, don't enumerate; the blur is the
artifact.** Verbatim convergence is the failure mode, not the goal.

This is a sibling of [`shakespeare`](../shakespeare/) and
[`gatsby`](../gatsby/), but unlike them it rides the monorepo's shared
[`core`](../../core/) engine directly — no vendored base engine. `core`
already honors `meta.pkl` as a char-level tokenizer contract end-to-end, so
nothing in `core` had to change (see
[ADR-0012](../../docs/adr/0012-pluggable-tokenization.md)). The agent rules
are in [`CLAUDE.md`](CLAUDE.md); the lineage is in
[`docs/sources.md`](docs/sources.md).

## How it works

The corpus is **synthetic and in-repo**: `generate.py` is a deterministic
reimplementation of Kazemi's bot, so we own the generator rather than scraping it.
That keeps the corpus frozen and inspectable, and — the real reason — lets us
*weight* it. Pynchon's nine canonical construals are folded in as ~18%
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
    --data_root=projects/kenosha-kid/data --temperature=0.9
```

`config.py` reproduces the champion with no extra arguments; capacity
(`n_layer`/`n_embd`) and `max_iters` are *aesthetic* knobs here (smaller/shorter
blurs more), not just performance.

## The champion

[`kenosha-kid-nanogpt-1`](../../research-docs/model-cards/kenosha-kid-nanogpt-1.md)
— run `r3-mid`, 350 iters, best val 0.48, sampled at temperature 0.9.
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

## Versions

A registry of released `kenosha-kid-nanogpt-N` versions — spec, git tag, and the
commands to rebuild each. Weights are never committed; everything needed to
reproduce them is.

| Version | Folder | What it is | Headline metric |
|---------|--------|-----------|-----------------|
| v1 | [`models/kenosha-kid-nanogpt-1/`](models/kenosha-kid-nanogpt-1/) | the mid-transition "dreaming" checkpoint (run `r3-mid`) | dream/verbatim balance at temp 0.9 |
| v2 | [`models/kenosha-kid-nanogpt-2/`](models/kenosha-kid-nanogpt-2/) | the **drift-corpus** checkpoint (run `drift-r1`) — converged, still dreaming | 9/9 anchors verbatim **and** ~33% near-miss lines at temp 0.9 |

The quality metric for this project is **not** val loss — it is the
**dream/verbatim balance**: sampled warm, the model should return to the six
words and land slightly differently each time (reordered, repunctuated, the
occasional near-miss). Verbatim-perfect convergence is the *failure mode*; run
`r1` has the lowest loss in the series and is the worst artifact. See the
[Leaderboard](#leaderboard).

### `kenosha-kid-nanogpt-1` (run `r3-mid`)

A ~0.79M-parameter char-level GPT whose entire corpus is punctuated permutations
of *you never did the kenosha kid*, stopped on purpose in the middle of the
memorization phase transition — spellings good enough that the anchors surface,
loose enough that it still dreams.

#### Spec

| | |
|---|---|
| **Architecture** | modern char-level nanoGPT — RoPE, RMSNorm, bias-free (vendored snapshot of `core`) |
| **Tokenizer** | character-level, **27-char** vocab (derived from the corpus; `meta.pkl` is the contract) |
| **Size** | 4 layers · 4 heads · 128 embd · ~0.79M params |
| **block_size** | 128 |
| **Checkpoint** | the 350-iter mid-transition checkpoint, val loss ~0.48 (MPS) |
| **Best sampled at** | temperature **0.9** |
| **Git tag** | `kenosha-kid-nanogpt-1` |

#### Corpus

Synthetic and deterministic: 24,000 lines of punctuated permutations of the six
words, with Pynchon's nine construals injected as high-frequency anchors over
the brute-force tail. Vendored into the frozen folder as `raw.txt` (regenerable
byte-for-byte by `generate.py` — no external deps, no scrape).

#### Rebuild

A frozen, self-contained snapshot lives in
[`models/kenosha-kid-nanogpt-1/`](models/kenosha-kid-nanogpt-1/) and runs **in
place** with no project-root or shared-`core` dependency:

```bash
cd models/kenosha-kid-nanogpt-1
python prepare.py     # raw.txt -> kenosha/{train,val}.bin + meta.pkl (here)
python train.py       # -> ./ckpt.pt  (stop at ~350 iters — the dream lives mid-transition)
python sample.py --temperature=0.9
```

Model card: [`research-docs/model-cards/kenosha-kid-nanogpt-1.md`](../../research-docs/model-cards/kenosha-kid-nanogpt-1.md).
Report: [Can a model dream a single phrase?](../../research-docs/reports/dream-a-single-phrase.md).

### `kenosha-kid-nanogpt-2` (run `drift-r1`)

The same ~0.79M-parameter char-level GPT and the same six words, but trained on a
**self-drifting corpus** and taken to **convergence** — and it still dreams. This
is the answer to the open question v1's report left behind (*"a corpus that itself
drifts"*).

#### What changed from v1

v1's near-misses were a side effect of **undertraining**: the pristine corpus never
misspelled, so a converged model spelled the six words perfectly and the drift
retreated to order/punctuation. Getting near-misses meant stopping mid-transition,
which **coupled** them to blurred anchors. v2 moves the drift into the **data**:
`generate.py` gains a `DRIFT_RATE` knob (default **0.06**), a per-letter
misspelling channel (swap / double / drop / substitute) applied to the permutation
**tail only** — the nine Pynchon anchors stay **pristine and verbatim**. Now a
fully converged, low-loss model reproduces the anchors crisply *and* dreams the
near-misses, because the near-misses live in the corpus rather than in a stopping
point. `DRIFT_RATE` is the dial (heavier drift → more near-miss, some garble, an
anchor at risk). At `DRIFT_RATE=0.0` the corpus regenerates byte-for-byte identical
to v1's, so the two rounds share a provenance.

#### Spec

| | |
|---|---|
| **Architecture** | modern char-level nanoGPT — RoPE, RMSNorm, bias-free (vendored snapshot of `core`) |
| **Tokenizer** | character-level, **39-char** vocab (vs v1's 27 — the drift channel's substitutions add the full lowercase alphabet; `meta.pkl` is the contract) |
| **Size** | 4 layers · 4 heads · 128 embd · ~0.79M params |
| **block_size** | 128 |
| **Checkpoint** | the **converged 1100-iter** checkpoint, best val loss **~0.65** (MPS) — a higher floor than v1 (0.43) on purpose: the drift is genuine entropy, so "converged" = plateaued on its own corpus |
| **Best sampled at** | temperature **0.9** |
| **Dream-score** (`eval_dream.py`, T=0.9) | anchor-recall **9/9** verbatim · near-miss line-rate **~0.33** · garble ~0.002 |
| **Git tag** | `kenosha-kid-nanogpt-2` |

#### Corpus

Synthetic and deterministic: 24,000 lines of punctuated permutations of the six
words, with Pynchon's nine construals injected as **pristine** high-frequency
anchors (~18%) over a **drifted** brute-force tail (`DRIFT_RATE=0.06` → ~74% of
tail lines carry ≥1 edit). Vendored into the frozen folder as `raw.txt`
(regenerable byte-for-byte by `generate.py` — no external deps, no scrape).

#### Rebuild

A frozen, self-contained snapshot lives in
[`models/kenosha-kid-nanogpt-2/`](models/kenosha-kid-nanogpt-2/) and runs **in
place** with no project-root or shared-`core` dependency:

```bash
cd models/kenosha-kid-nanogpt-2
python generate.py            # (optional) rewrites raw.txt identically (DRIFT_RATE=0.06)
python prepare.py             # raw.txt -> kenosha/{train,val}.bin + meta.pkl (here)
python train.py config.py     # -> ./ckpt.pt (converged, 1100 iters, val ~0.65)
python sample.py --out_dir=. --data_root=. --device=cpu --start=$'\n' --temperature=0.9
python eval_dream.py --device=cpu --num_samples=40   # the dream-score
```

Model card: [`research-docs/model-cards/kenosha-kid-nanogpt-2.md`](../../research-docs/model-cards/kenosha-kid-nanogpt-2.md).
Round notes: [`research/log.md`](research/log.md) (2026-07-02 drift round) and
[`runs/drift-samples.md`](runs/drift-samples.md).

## Leaderboard

Per-run scoreboard. The journal (why) is in [`research/log.md`](research/log.md).
For this project the "score" is not just val loss — it's the **dream/verbatim
balance**: a good run keeps the six words recognizable while drifting
(punctuation, near-misses) when sampled warm. Verbatim-perfect convergence is a
*loss*, not a win.

| run | corpus | model (L/H/E, block) | iters | best val loss | warm-sample read | verdict |
|---|---|---|---|---|---|---|
| r1 | v1 (24k lines, anchors 18%) | 4 / 4 / 128, 128 | 2000 | 0.4325 | crisp words; drift only in order/punctuation. The **lucid** dream. | too clean — no near-misses |
| r2-early | v1 | 4 / 4 / 128, 128 | 150 | 0.59 | char-level near-misses ("Kenoshau", "nevu"); anchors too broken | too dreamy — phrase dissolves |
| **r3-mid** | v1 | 4 / 4 / 128, 128 | 350 | 0.48 | anchors surface + occasional near-miss; best at **temp 0.9** | **champion → kenosha-kid-nanogpt-1** |
| **drift-r1** | v2 (drift 0.06; anchors pristine) | 4 / 4 / 128, 128 | 1100 (converged) | 0.65 | 9/9 anchors verbatim **and** near-miss on ~33% of lines; best at **temp 0.9** | **released → kenosha-kid-nanogpt-2** |

L/H/E = n_layer / n_head / n_embd. "Score" here is the dream/verbatim balance, not
val loss — r1 has the lowest loss and is the *worst* artifact, and v2 (drift-r1)
has a *higher* loss than the v1 champion yet is a better artifact (the injected
drift is genuine entropy — see the drift round below and the model card).

### 2026-07-02 round — drift corpus + MC-dropout (drift-r1 released as v2)

Automated dream-score via `eval_dream.py` (~430 lines/run, T=0.9): **anchor_hit**
= fraction of lines verbatim = 1 of 9 anchors, **9** = anchors covered/9,
**near-miss** = fraction of lines with a 1–2 edit-distance drift word, **garble** =
lines with a ≥3-distance word. corpus v2 = drifted tail (`DRIFT_RATE`), anchors
pristine. Goal: crisp anchors **AND** abundant near-misses from a *converged* model.

| run | corpus | iters | val | anchor_hit | 9 | near-miss | garble | verdict |
|---|---|---|---|---|---|---|---|---|
| r1 (baseline) | v1 | 2000 | 0.43 | 0.225 | 9/9 | 0.000 | 0.000 | crisp anchors, no near-misses |
| r3-mid (baseline) | v1 | 350 | 0.48 | 0.042 | 3/9 | 0.037 | 0.012 | couples both via undertraining |
| **drift-r1** | v2, drift 0.06 | 1100 | 0.65 | 0.138 | **9/9** | **0.331** | 0.002 | **crisp anchors + abundant near-misses (win)** |
| drift-r2 | v2, drift 0.14 | 1100 | 0.85 | 0.131 | 8/9 | 0.592 | 0.035 | heavier drift; more near-miss, some garble |
| r1 + MC-dropout p=0.2 | v1 | 2000 | 0.43 | 0.118 | 9/9 | 0.002 | 0.000 | dropout too weak to drift spellings |
| r1 + MC-dropout p=0.4 | v1 | 2000 | 0.43 | 0.009 | 2/9 | 0.252 | 0.051 | near-misses only by wrecking anchors (coupled) |

**Drift decouples; MC-dropout does not.** drift-r1 is the only converged model
with crisp anchors *and* abundant near-misses. Samples:
[`runs/drift-samples.md`](runs/drift-samples.md),
[`runs/mcdropout-samples.md`](runs/mcdropout-samples.md). **drift-r1 is released
as `kenosha-kid-nanogpt-2`** (see [Versions](#versions) and
[`models/kenosha-kid-nanogpt-2/`](models/kenosha-kid-nanogpt-2/)).

## Research notes

This is a research project, so the data and the reasoning are part of the record:

- **The corpus is committed** (`data/raw.txt`, regenerates byte-for-byte from
  `generate.py`); weights and derived `.bin`/`.pkl` are gitignored — they rebuild
  deterministically (no weights in the tree,
  [ADR-0002](../../docs/adr/0002-no-weights-in-tree.md)).
- **[`research/log.md`](research/log.md)** is the running journal (why each
  decision was made); the [Leaderboard](#leaderboard) above is the per-run
  scoreboard.
- The full write-up is
  [`dream-a-single-phrase.md`](../../research-docs/reports/dream-a-single-phrase.md); the frozen,
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
