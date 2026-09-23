---
title: Train a small model
summary: >-
  The studio's method as one prompt. Paste it into a coding agent and it
  trains a ~10M-parameter character-level GPT on TinyStories, end to end,
  on your machine.
---

# Train a small model

The whole method fits in a prompt. Paste it into a coding agent and it trains
a small [TinyStories](https://huggingface.co/datasets/roneneldan/TinyStories)
nanoGPT on your own machine. The recipe is
[Andrej Karpathy's](https://github.com/karpathy/nanoGPT) and takes
about an hour.

```text
Train a character-level nanoGPT on TinyStories, end to end, on this machine.

1. Clone https://github.com/karpathy/nanoGPT. Its README says the repo is deprecated in favor of nanochat; ignore that and use nanoGPT. Install torch, numpy, datasets, tqdm, tiktoken (sample.py imports it).

2. Write data/tinystories/prepare.py, mirroring data/shakespeare_char/prepare.py: stream the roneneldan/TinyStories train split from HuggingFace (streaming=True — do not download the full dataset), take the first 100,000 stories, join with blank lines, normalize to ASCII (map curly quotes to straight, drop other non-ASCII). Build a character vocab, encode a 90/10 split into train.bin and val.bin as uint16, save meta.pkl with stoi/itos.

3. Write config/train_tinystories.py based on config/train_shakespeare_char.py: dataset='tinystories', n_layer=6, n_head=6, n_embd=384, block_size=256, batch_size=64, learning_rate=1e-3, max_iters=5000, out_dir='out-tinystories'. Set device to the best available: 'cuda' if present, else 'mps', else 'cpu'. Set dtype='float32' and compile=False regardless of device. Do not change the model architecture.

4. Run: python train.py config/train_tinystories.py. Report train and val loss at each eval.

5. Run: python sample.py --out_dir=out-tinystories --device=<the device from step 3> --num_samples=3 --start="Once upon a time" and print the samples. sample.py defaults to cuda, so it fails on a Mac or cpu without --device.

If you end up on cpu, warn me and cut max_iters and lr_decay_iters to 1000 before training.
```
