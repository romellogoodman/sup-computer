# Shakespeare research log

Round-by-round evidence for the LLM-assisted research series. This file holds the
**unreleased experiment rounds**; the released series and its verdicts live in
[`../leaderboard.md`](../leaderboard.md) and [`../MODELS.md`](../MODELS.md). Nothing
here edits a released row — new rounds are appended.

Held-out yardstick for every row: **bits-per-character (BPC)** on the fixed
`projects/shakespeare/test.txt` (250,000 chars of Shakespeare), computed by
`core/eval/eval.py` (char/GPT-2/custom BPE — during r5, custom BPE went through
the since-deleted project-local `eval_xl.py`; core absorbed that seam in
ADR-0029, 2026-07-14). Seed 1337 throughout, single-seed (see the
leaderboard's variance caveat).

---

## 2026-07-02 — Round 5 "XL": enlarged early-modern corpus + custom BPE vocab (UNRELEASED)

**Researcher:** Claude Opus 4.8 · **Status:** experiment, not released.

Two levers stacked on the current champion (`r3-bpe` / `shakespeare-nanogpt-2`,
BPC 1.919, 29.9M params, GPT-2 50,257-vocab, Shakespeare-only):
(a) **enlarge the corpus** with public-domain early-modern drama, and
(b) **replace the GPT-2 vocab** with small corpus-trained byte-level BPE vocabs
(~1k / 4k / 16k), with a GPT-2-vocab run on the same enlarged corpus as control.

### Headline

- **New best BPC: `r5-xl-bpe1k` = 1.884** (1024-vocab custom BPE + enlarged corpus),
  beating the champion's **1.919** — at **11.02M params, 63% smaller** than the
  29.94M champion. End-to-end vs the series baseline: 2.395 → 1.884.
- **All the larger vocabs (4k/16k/GPT-2) are inconclusive** because a numerical
  instability (below) forced them onto a 10× lower learning rate, leaving them
  badly **undertrained** at the fixed 2000-iter budget. Their BPC (2.60–2.81) is
  not a verdict on the tokenizer — it's a verdict on undertraining.
- **Instability finding (the round's second result):** the modern arch trains
  under **float16 autocast on MPS with the CUDA-only GradScaler disabled**; large
  vocab → large logits → float16 overflow → divergence. Instability **scales with
  vocab size**: 1k stable @1e-3; 4k diverges @1e-3, stable @1e-4; 16k & GPT-2
  diverge @1e-3 *and* @3e-4, only marginally trainable @1e-4.

### Corpus

Cleaned Complete Works (Gutenberg #100, identical cleaning + slicing to
`data/shakespeare_full`) **plus** 12 contemporary plays downloaded from Gutenberg:
Marlowe ×5 (Doctor Faustus, Tamburlaine 1 & 2, Edward II, The Jew of Malta),
Jonson ×3 (Volpone, The Alchemist, Every Man in His Humour), Kyd ×1 (The Spanish
Tragedy), Webster ×2 (Duchess of Malfi, White Devil), and a Dekker collection.
Build/splits: `data/_xl_corpus.py`; download cache `data/shakespeare_xl_raw/` (gitignored).

- **Held-out test is unchanged:** the 250k slice is `body[p:p+250000]`,
  `p=int(len(body)*0.45)` — verified **bit-identical** to the committed `test.txt`,
  and excluded from all training data.
- **Val is unchanged:** the same Shakespeare 150k as `shakespeare_full`
  (`s_pool[-150000:]`), for maximal comparability.
- **Train = Shakespeare-train (4,959,342 chars) + contemporaries (2,895,174) =
  7,854,519 chars** (~1.6× the champion's Shakespeare-only train pool). Tokenizers
  trained on train only (never val/test). Raw ≈ 8.9 MB (within the 8–12 MB target).

Deliberately did **not** add Gutenberg #77587 (a 4.8 MB "chief Elizabethan
dramatists" anthology) — it duplicates the individually-downloaded plays and would
push domain drift further from Shakespeare (which is what the test measures).

### Tokenizers & token counts (train / val)

Byte-level BPE (HF `tokenizers`), 256-byte initial alphabet → lossless (no UNK),
so `test.txt` always encodes fully and BPC's char denominator is exact.

| Vocab | chars/tok (train) | train tokens | val tokens |
|---|---|---|---|
| bpe **1024** | 2.32 | 3,383,756 | 61,383 |
| bpe **4096** | 3.01 | 2,612,929 | 47,621 |
| bpe **16384** | 3.54 | 2,218,079 | 40,008 |
| GPT-2 **50257** (control) | 3.10 | 2,533,307 | 45,790 |

Note: the domain-trained **16k vocab compresses Shakespeare better (3.54 ch/tok)
than GPT-2's 50k (3.10)** — a smaller, corpus-specific vocab out-compresses the
general one.

### Runs (all: n_layer=6, n_head=6, n_embd=384, block=256, dropout=0.2, batch=64,
beta2=0.99, 2000 iters, device=mps, compile=False, always_save_checkpoint=False,
eval_interval=250, seed=1337). Base config `config/train_shakespeare_mac.py`;
LR / warmup deltas noted.

| Run | vocab | params | LR (min_lr, warmup) | val curve (step:val) | val-min step | outcome |
|---|---|---|---|---|---|---|
| **r5-xl-bpe1k** | 1024 | **11.02M** | 1e-3 (1e-4, 100) | 6.99→3.97→3.70→3.57→3.48→3.45→3.40→3.37→**3.34** | **2000 (end)** | ✅ clean, undertrained |
| r5-xl-bpe4k | 4096 | 12.19M | 1e-3 (1e-4, 100) | 6.62→6.80→7.09→7.33→7.62→7.80→7.93→8.20 | 250 | ❌ **diverged** |
| r5-xl-bpe4k-lr3e4 | 4096 | 12.19M | 3e-4 (3e-5, 100) | 6.39→6.48→6.60 (killed) | 250 | ⚠️ mildly unstable |
| **r5-xl-bpe4k-lr1e4** | 4096 | 12.19M | 1e-4 (1e-5, 200) | 6.60→6.33→6.27→6.24→6.23→6.22→6.20→**6.20** | **2000 (end)** | ✅ clean, undertrained |
| **r5-xl-bpe16k** | 16384 | 16.91M | 1e-4 (1e-5, 200)† | 6.90→**6.72**→6.88→7.04→7.17→7.28→7.31→7.34 | 500 | ⚠️ early bottom, residual instability |
| r5-xl-gpt2 | 50257 | 29.94M | 1e-3 (1e-4, 100) | 8.19→10.76→13.44 (killed) | 250 | ❌ **diverged** |
| **r5-xl-gpt2-lr1e4** | 50257 | 29.94M | 1e-4 (1e-5, 200) | 6.41→**6.08**→6.22→6.36→6.45→6.52→6.55→6.58 | 500 | ⚠️ early bottom (control) |

† `r5-xl-bpe16k` was also tried at **3e-4** first — it diverged (val 7.08→7.88→8.63
→9.35), so it was relaunched at 1e-4/warmup 200 (the row above). The 3e-4 log was
overwritten by the relaunch; the divergence numbers are recorded here.

`r5-xl-bpe4k` (1e-3, diverged) and `r5-xl-bpe4k-lr3e4` (3e-4) logs are kept as
evidence; they are **excluded from the BPC table** (diverged / not-run-to-end).

### Held-out BPC (test.txt, 250,000 chars)

| Run / model | vocab | params | Test BPC | token_loss | notes |
|---|---|---|---|---|---|
| series baseline (`r1-data-small`) | char 65 | 10.6M | 2.395 | 1.660 | for scale |
| `r2-arch-modern` | char 65 | 10.6M | 2.004 | 1.389 | |
| **champion `r3-bpe`** (shakespeare-nanogpt-2) | GPT-2 50257 | 29.94M | **1.919** | 4.100 | prior best |
| `r4-champion` | GPT-2 50257 | 65.5M | 1.947 | 4.160 | prior failed round |
| **`r5-xl-bpe1k`** ⭐ | **1024** | **11.02M** | **1.884** | 2.953 | ✅ **new best, 63% fewer params** |
| `r5-xl-bpe16k` | 16384 | 16.91M | 2.597 | 5.932 | undertrained (val-min @500) |
| `r5-xl-gpt2-lr1e4` (corpus control) | 50257 | 29.94M | 2.661 | 5.687 | undertrained (val-min @500) |
| `r5-xl-bpe4k-lr1e4` | 4096 | 12.19M | 2.814 | 5.551 | undertrained (val-min @2000) |

### Findings

1. **A tiny corpus-trained vocab wins.** `r5-xl-bpe1k` (1024 tokens, 11M params)
   sets a new best BPC **1.884 < 1.919**, at **~1/3 the champion's parameters**
   (19.3M of the champion's 29.9M *was* the GPT-2 embedding table; a 1024-vocab
   embedding is ~0.4M). More capability per parameter.
2. **The enlarged corpus eliminated the overfit that defined R3/R4.** The champion
   and R4 both bottomed val around step ~1000 then rose (the "checkpoints kept
   mid-anneal" pathology). `r5-xl-bpe1k` val **fell monotonically to step 2000** —
   it never overfit and is in fact **undertrained**; more iters should lower BPC
   further. Same for `r5-xl-bpe4k-lr1e4`. The data lever did exactly what the plan
   predicted (move the overfit point later), and then some (removed it).
3. **Large-vocab training is numerically unstable on this MPS/float16 stack.**
   Root cause: `train.py` uses `dtype='float16'` on MPS (the bf16 path is CUDA-only)
   and the `GradScaler` is CUDA-only → *disabled* on MPS. Large vocab ⇒ large
   `lm_head` logits ⇒ float16 overflow ⇒ divergence. It scales cleanly with vocab
   size: **1k ok @1e-3; 4k needs ≤1e-4; 16k & GPT-2 unstable even @3e-4, only
   marginally trainable @1e-4** (val bottoms at step ~500 then creeps up).
4. **The corpus control is confounded.** `r5-xl-gpt2-lr1e4` (enlarged corpus,
   GPT-2 vocab) can't cleanly isolate "corpus alone vs champion" because the
   champion trained at 1e-3 and this control was forced to 1e-4 (undertrained).
   So the *combined-levers* win (`bpe1k` 1.884 vs champion 1.919, both @1e-3,
   both trained to their val-min) is the only clean end-to-end comparison here.

### Sample quality (temp 0.8, 500 tok; `runs/<run>-sample.txt`)

- **bpe1k** — coherent early-modern drama with speaker labels and the italic
  `_Name._` convention picked up from the Marlowe/Webster editions
  (*"My grave is England's death: let me go to choose"*). Matches its low BPC.
- **bpe4k-lr1e4 / bpe16k / gpt2-lr1e4** — word-salad with only intermittent
  structure (16k & gpt2 emit recognizable speaker names: KING, HORATIO, ANTONIO). Consistent
  with undertraining, not tokenizer failure.

### Recommended next round

- **Fix the precision, not the LR.** Set `dtype=float32` (or add an MPS-safe loss
  scaler) so all vocabs train at 1e-3; this would give the 4k/16k/GPT-2 conditions
  a fair, un-confounded shot and likely change their ranking entirely.
- **Give bpe1k more iters** (it was still improving at 2000) and **multi-seed** the
  bpe1k vs champion delta (−0.035 is within the leaderboard's stated noise band for
  small deltas — treat as *promising*, not decisive, until seed-replicated).

### Files created (this round)

- `data/_xl_corpus.py`, `data/_xl_bpe.py` — corpus builder + BPE helpers
- `data/shakespeare_xl_{bpe1k,bpe4k,bpe16k,gpt2}/prepare.py` (+ generated bins/meta/tokenizer.json, gitignored except tokenizer.json)
- `data/shakespeare_xl_raw/.gitignore` — never commit raw Gutenberg downloads
- `eval_xl.py`, `sample_xl.py` — project-local eval/sample for custom BPE (meta.pkl
  `{"vocab_size","tokenizer"}` seam per ADR-0012; core understood only char/GPT-2
  at the time — both deleted 2026-07-14 when core absorbed the seam, ADR-0029)
- `runs/r5-xl-*` (train.log + `-sample.txt`; checkpoints gitignored)
