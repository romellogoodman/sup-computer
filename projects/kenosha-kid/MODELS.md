# Models

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
`r1` has the lowest loss in the series and is the worst artifact. See
[`leaderboard.md`](leaderboard.md).

## `kenosha-kid-nanogpt-1` (run `r3-mid`)

A ~0.79M-parameter char-level GPT whose entire corpus is punctuated permutations
of *you never did the kenosha kid*, stopped on purpose in the middle of the
memorization phase transition — spellings good enough that the anchors surface,
loose enough that it still dreams.

### Spec

| | |
|---|---|
| **Architecture** | modern char-level nanoGPT — RoPE, RMSNorm, bias-free (vendored snapshot of `core`) |
| **Tokenizer** | character-level, **27-char** vocab (derived from the corpus; `meta.pkl` is the contract) |
| **Size** | 4 layers · 4 heads · 128 embd · ~0.79M params |
| **block_size** | 128 |
| **Checkpoint** | the 350-iter mid-transition checkpoint, val loss ~0.48 (MPS) |
| **Best sampled at** | temperature **0.9** |
| **Git tag** | `kenosha-kid-nanogpt-1` |

### Corpus

Synthetic and deterministic: 24,000 lines of punctuated permutations of the six
words, with Pynchon's nine construals injected as high-frequency anchors over
the brute-force tail. Vendored into the frozen folder as `raw.txt` (regenerable
byte-for-byte by `generate.py` — no external deps, no scrape).

### Rebuild

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

## `kenosha-kid-nanogpt-2` (run `drift-r1`)

The same ~0.79M-parameter char-level GPT and the same six words, but trained on a
**self-drifting corpus** and taken to **convergence** — and it still dreams. This
is the answer to the open question v1's report left behind (*"a corpus that itself
drifts"*).

### What changed from v1

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

### Spec

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

### Corpus

Synthetic and deterministic: 24,000 lines of punctuated permutations of the six
words, with Pynchon's nine construals injected as **pristine** high-frequency
anchors (~18%) over a **drifted** brute-force tail (`DRIFT_RATE=0.06` → ~74% of
tail lines carry ≥1 edit). Vendored into the frozen folder as `raw.txt`
(regenerable byte-for-byte by `generate.py` — no external deps, no scrape).

### Rebuild

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
