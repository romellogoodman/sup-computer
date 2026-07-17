---
title: Train one yourself
summary: >-
  The studio's method as one prompt. Paste it into a coding agent and it
  trains a ~10M-parameter character-level GPT on TinyStories — on your
  machine, end to end.
---

# Train one yourself

The whole method fits in a prompt. Paste this into a coding agent — Claude
Code, Cursor, whatever you run — and it trains a ~10M-parameter
character-level GPT on
[TinyStories](https://huggingface.co/datasets/roneneldan/TinyStories), end to
end, on your machine. The recipe is
[karpathy's nanoGPT](https://github.com/karpathy/nanoGPT) — the same lineage
our first models came from — and nothing in it depends on this studio's code.

You need Python and one of: an NVIDIA GPU, an Apple Silicon Mac, or a patient
CPU. Budget an hour, give or take — hardware decides.

```text
Train a character-level nanoGPT on TinyStories, end to end, on this machine.

1. Clone https://github.com/karpathy/nanoGPT. Install torch, numpy, datasets, tqdm.

2. Write data/tinystories/prepare.py, mirroring data/shakespeare_char/prepare.py: stream the roneneldan/TinyStories train split from HuggingFace (streaming=True — do not download the full dataset), take the first 100,000 stories, join with blank lines, normalize to ASCII (map curly quotes to straight, drop other non-ASCII). Build a character vocab, encode a 90/10 split into train.bin and val.bin as uint16, save meta.pkl with stoi/itos.

3. Write config/train_tinystories.py based on config/train_shakespeare_char.py: n_layer=6, n_head=6, n_embd=384, block_size=256, batch_size=64, learning_rate=1e-3, max_iters=5000, out_dir='out-tinystories'. Set device to the best available: 'cuda' if present, else 'mps', else 'cpu'. Set dtype='float32' and compile=False regardless of device. Do not change the model architecture.

4. Run: python train.py config/train_tinystories.py. Report train and val loss at each eval.

5. Run: python sample.py --out_dir=out-tinystories --start="Once upon a time" and print three samples.

If you end up on cpu, warn me and cut max_iters to 1000 before training.
```

## Why the config looks like this

Every pin closes a road agents wander down. Device is detected, not assumed —
`cuda`, then `mps`, then `cpu`. dtype is float32 everywhere, even on GPUs
where mixed precision would be faster, because half-precision quirks are the
most common way a first run dies on unfamiliar hardware. Compile stays off
for the same reason. The cost is some speed on a big GPU. A
ten-million-parameter model can afford it.

The data is streamed, not downloaded: full TinyStories is gigabytes, and the
first 100,000 stories are roughly one epoch at this config — 5,000 steps of
64×256 characters is about 82M positions, and the subset is about that many
characters long.

## What to expect

Story-shaped prose, not fluency. Five thousand steps at this scale buys
sentences that scan, mostly real words, and characters who wander in and out
of coherence between paragraphs. If your samples read like that, the run
worked. It isn't the model falling short of TinyStories — it's what ten
million parameters reading one character at a time sounds like, and hearing
that for yourself is the point.

When you want more, the knobs are all in step 3 — and
[the research](reports/README.md) is where we turn them.
