# shakespeare-nanogpt-2

The **research-lab winner** (Round 3): a modern-architecture GPT with GPT-2 BPE
tokenization, trained on the full Complete Works of Shakespeare. This folder is a
**frozen, self-contained snapshot** of exactly the code that produces v2 — the
modern model (`model.py`) was copied from
[`research-lab/model_modern.py`](../../research-lab/model_modern.py), and the
training command's overrides are baked into [`config.py`](config.py). The living
[research loop](../../research-lab/) can keep changing without affecting this
released version.

- Tokenizer: GPT-2 BPE (~50k vocab)
- Data: Complete Works (~5 MB)
- Architecture: modern — RoPE + RMSNorm + bias-free
- Parameters: ~29.9 M
- Held-out test: **BPC 1.919** (the series' best)
- Model card: [`research-docs/model-cards/shakespeare-nanogpt-2.md`](../../research-docs/model-cards/shakespeare-nanogpt-2.md)
- Git tag: `shakespeare-nanogpt-2`

## Reproduce

Everything runs in place from this folder; generated files (`*.bin`, `ckpt.pt`,
`raw.txt`) stay here and are gitignored. BPE writes no `meta.pkl`, so eval/sample
fall back to the tiktoken GPT-2 tokenizer.

```bash
cd models/shakespeare-nanogpt-2
python prepare.py     # downloads the Complete Works, builds BPE train/val.bin here
python train.py       # trains -> ./ckpt.pt (zero-arg run reproduces v2; see config.py)
python eval.py        # scores ./ckpt.pt on the shared held-out test (expect BPC ~1.919)
python sample.py --start="ROMEO:" --num_samples=1 --max_new_tokens=1000
```

Override any hyperparameter on the command line, e.g. `python train.py --max_iters=4000`.

## Files

| File | Role |
|------|------|
| `model.py` | the modern GPT (RoPE + RMSNorm + bias-free) |
| `config.py` | this model's hyperparameters (auto-loaded by `train.py`) |
| `train.py` | training loop; writes `ckpt.pt` here |
| `sample.py` | generate text from `ckpt.pt` |
| `eval.py` | score `ckpt.pt` on `research-lab/test.txt` in BPC |
| `prepare.py` | download + BPE-encode the Complete Works into this folder |
| `configurator.py` | nanoGPT's `--key=value` override helper |
