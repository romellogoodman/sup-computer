# shakespeare-nanogpt-3

The **r6 float32 winner**: a modern-architecture GPT (RoPE + RMSNorm + bias-free)
with a **1024-token, byte-level BPE trained on the corpus itself**, trained on an
**enlarged early-modern-drama corpus** (Shakespeare's Complete Works plus
public-domain Marlowe, Jonson, Kyd, Webster, and Dekker) at **dtype=float32**.

This folder is a **frozen, self-contained snapshot** of exactly the code +
tokenizer that produces v3, copied out of the shared engine and the working data
pipeline so the released version reproduces forever, independent of `core/` drift
(see [ADR-0003](../../../../docs/adr/0003-frozen-self-contained-releases.md) and
[`docs/releasing.md`](../../../../docs/releasing.md)). It runs **in place** with
no cross-folder imports — `model.py` / `train.py` / `configurator.py` are
vendored from `core/nanogpt_core` (the engine r6 rode; the `train.py` import is
repointed to the sibling `model.py`), and the 1024-token tokenizer is pinned in
`shakespeare_xl_bpe1k/tokenizer.json`.

- Tokenizer: **1024-vocab byte-level BPE**, trained on the r6 training corpus
  (committed as `shakespeare_xl_bpe1k/tokenizer.json`; `meta.pkl` is the
  contract — the ADR-0012 seam, extended with a `"tokenizer"` field)
- Data: the enlarged early-modern-drama corpus (~5 MB Shakespeare + contemporary
  drama); the held-out test slice is the shared `test.txt` and is **excluded**
- Architecture: modern — RoPE + RMSNorm + bias-free
- Size: 6 layers · 6 heads · 384 embd · 256 context · **~11.02 M params**
  (about **1/3** of v2's 29.9 M GPT-2-vocab model)
- dtype: **float32** (eliminates the MPS float16 large-vocab logit overflow that
  confounded r5, so lr=1e-3 trains cleanly)
- Held-out test: **BPC 1.831** — beats the prior champion v2's 1.919 (29.9 M) and
  matches/beats a fresh fp32 GPT-2-vocab control (1.843, 29.9 M) at ~1/3 the size
- Model card: [`research-docs/model-cards/shakespeare-nanogpt-3.md`](../../../../research-docs/model-cards/shakespeare-nanogpt-3.md)
- Git tag: `shakespeare-nanogpt-3`

## Reproduce

Everything runs in place from this folder; generated files
(`shakespeare_xl_bpe1k/{train,val}.bin`, `shakespeare_xl_bpe1k/meta.pkl`,
`shakespeare_xl_raw/`, `ckpt.pt`) stay here and are gitignored. The 1024-token
`tokenizer.json` is committed and is **never retrained** — `prepare.py` only
re-encodes the corpus with it, pinning the exact vocabulary.

The BPE steps need the Hugging Face `tokenizers` library, provided ad hoc (it is
not in `pyproject`), so prefix those commands with `--with tokenizers`:

```bash
cd projects/shakespeare/models/shakespeare-nanogpt-3
uv run --with tokenizers python prepare.py   # downloads the corpus, encodes train/val.bin + meta.pkl here
uv run python train.py                        # trains -> ./ckpt.pt (zero-arg run reproduces v3; see config.py)
uv run --with tokenizers python eval.py       # scores ./ckpt.pt on the shared held-out test (expect BPC ~1.831)
uv run --with tokenizers python sample.py --start="ROMEO:" --num_samples=1 --max_new_tokens=500
```

Override any hyperparameter on the command line, e.g. `uv run python train.py --max_iters=4000`.

## No weights here (this folder ships CODE + tokenizer)

The trained weights are **not** in this folder. `*.pt`, `*.bin`, and `*.pkl` are
gitignored and regenerate deterministically from the committed code + the pinned
`tokenizer.json` + the auto-downloaded public-domain corpus. The released weights
live as **release artifacts** (referenced by the top-level
[`registry.json`](../../../../registry.json)), not in the git tree — per the
monorepo's no-weights-in-the-tree rule. This snapshot is pinned to git tag
`shakespeare-nanogpt-3`.

## Files

| File | Role |
|------|------|
| `model.py` | the modern GPT (RoPE + RMSNorm + bias-free) — vendored from `core/nanogpt_core` |
| `config.py` | this model's frozen hyperparameters (float32; auto-loaded by `train.py`) |
| `train.py` | training loop; writes `ckpt.pt` here — vendored from `core` (import repointed to the sibling `model.py`) |
| `sample.py` | generate text from `ckpt.pt` (byte-level BPE, resolved via `meta.pkl`) |
| `eval.py` | score `ckpt.pt` on the shared `test.txt` in BPC (byte-level BPE-aware) |
| `prepare.py` | download + assemble the enlarged corpus, encode with the committed tokenizer into `shakespeare_xl_bpe1k/` |
| `configurator.py` | nanoGPT's `--key=value` override helper — vendored from `core` |
| `shakespeare_xl_bpe1k/tokenizer.json` | the pinned 1024-token byte-level BPE (committed; the only vocab this release uses) |
