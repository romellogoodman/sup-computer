# shakespeare-nanogpt-1

The **base** model: the original character-level nanoGPT baseline, trained on
Tiny Shakespeare. This folder is a **frozen, self-contained snapshot** of exactly
the code that produces v1 — copied out of the repo root so the
[shared engine](../../../../core/) can keep evolving without changing how this
released version is built.

- Tokenizer: character-level (65-char vocab)
- Data: Tiny Shakespeare (~1.1 MB)
- Architecture: original nanoGPT (LayerNorm, learned position embeddings)
- Parameters: ~10.6 M
- Model card: [`research-docs/model-cards/shakespeare-nanogpt-1.md`](../../../../research-docs/model-cards/shakespeare-nanogpt-1.md)
- Git tag: `shakespeare-nanogpt-1`

## Reproduce

Everything runs in place from this folder; generated files (`*.bin`, `*.pkl`,
`ckpt.pt`, `input.txt`) stay here and are gitignored.

```bash
cd models/shakespeare-nanogpt-1
python prepare.py     # downloads Tiny Shakespeare, builds train/val.bin + meta.pkl here
python train.py       # trains -> ./ckpt.pt (zero-arg run reproduces v1; see config.py)
python eval.py        # scores ./ckpt.pt on the shared held-out test (BPC)
python sample.py --start="ROMEO:" --num_samples=1 --max_new_tokens=1000
```

Override any hyperparameter on the command line, e.g. `python train.py --max_iters=5000`.

## Files

| File | Role |
|------|------|
| `model.py` | the GPT architecture (original nanoGPT) |
| `config.py` | this model's hyperparameters (auto-loaded by `train.py`) |
| `train.py` | training loop; writes `ckpt.pt` here |
| `sample.py` | generate text from `ckpt.pt` |
| `eval.py` | score `ckpt.pt` on the shared `test.txt` in BPC |
| `prepare.py` | build the dataset into this folder |
| `configurator.py` | nanoGPT's `--key=value` override helper |
