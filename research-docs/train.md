---
title: Train a small model
summary: >-
  The studio's method as one prompt. Paste it into a coding agent and it
  trains a ~10M-parameter character-level GPT on TinyStories, end to end,
  on your machine.
---

# Train a small model

The whole method fits in a prompt. Paste this into a coding agent — Claude
Code, Cursor, whichever — and it trains a ~10M-parameter character-level
GPT on [TinyStories](https://huggingface.co/datasets/roneneldan/TinyStories),
end to end, on your machine. The recipe is
[karpathy's nanoGPT](https://github.com/karpathy/nanoGPT), the repo our
first models came from. None of it needs this studio's code.

You need Python and one of: an NVIDIA GPU, an Apple Silicon Mac, or a patient
CPU. Budget an hour, give or take.

```text
Train a character-level nanoGPT on TinyStories, end to end, on this machine.

1. Clone https://github.com/karpathy/nanoGPT. Install torch, numpy, datasets, tqdm.

2. Write data/tinystories/prepare.py, mirroring data/shakespeare_char/prepare.py: stream the roneneldan/TinyStories train split from HuggingFace (streaming=True — do not download the full dataset), take the first 100,000 stories, join with blank lines, normalize to ASCII (map curly quotes to straight, drop other non-ASCII). Build a character vocab, encode a 90/10 split into train.bin and val.bin as uint16, save meta.pkl with stoi/itos.

3. Write config/train_tinystories.py based on config/train_shakespeare_char.py: n_layer=6, n_head=6, n_embd=384, block_size=256, batch_size=64, learning_rate=1e-3, max_iters=5000, out_dir='out-tinystories'. Set device to the best available: 'cuda' if present, else 'mps', else 'cpu'. Set dtype='float32' and compile=False regardless of device. Do not change the model architecture.

4. Run: python train.py config/train_tinystories.py. Report train and val loss at each eval.

5. Run: python sample.py --out_dir=out-tinystories --start="Once upon a time" and print three samples.

If you end up on cpu, warn me and cut max_iters to 1000 before training.
```

## The config trades speed for running anywhere

Device is detected at run time: `cuda`, then `mps`, then `cpu`. `dtype`
stays float32 everywhere, even on GPUs where mixed precision would be
faster — float32 behaves the same on every backend, and half precision is
where first runs tend to die. `compile` stays off for the same reason. The
pins cost some speed on a big GPU. A ten-million-parameter model can afford
it.

The data streams in rather than downloading, because the full corpus is
gigabytes. The 100,000-story subset is also roughly one epoch: 5,000 steps
of 64×256 characters is about 82M positions, and the subset is about that
many characters.

## What to expect

Story-shaped prose, not fluency. Five thousand steps at this scale buys
sentences that scan, mostly real words, and characters who wander in and out
of coherence between paragraphs. If your samples read like that, the run
worked. That isn't the model falling short of TinyStories; it's what ten
million parameters reading one character at a time sounds like. Hearing it
for yourself is the point.

When you want more, the knobs are all in step 3.
[The research](reports/README.md) is where we turn them.
