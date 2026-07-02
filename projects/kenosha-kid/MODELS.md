# Models

A registry of released `kenosha-kid-nanogpt-N` versions — spec, git tag, and the
commands to rebuild each. Weights are never committed; everything needed to
reproduce them is.

| Version | Folder | What it is | Headline metric |
|---------|--------|-----------|-----------------|
| v1 | [`models/kenosha-kid-nanogpt-1/`](models/kenosha-kid-nanogpt-1/) | the mid-transition "dreaming" checkpoint (run `r3-mid`) | dream/verbatim balance at temp 0.9 |

The quality metric for this project is **not** val loss — it is the
**dream/verbatim balance**: sampled warm, the model should return to the six
words and land slightly differently each time (reordered, repunctuated, the
occasional near-miss). Verbatim-perfect convergence is the *failure mode*; run
`r1` has the lowest loss in the series and is the worst artifact. See
[`research/leaderboard.md`](research/leaderboard.md).

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
