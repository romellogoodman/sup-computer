# `models/` — frozen, per-version code

Each subfolder is a **self-contained, runnable snapshot of the exact code that
produces one released model** in the `shakespeare-nanogpt-N` series. The point of
this tree is separation of concerns:

- The shared [`core/`](../../../core/) engine is the **living lab** — generic,
  evolving code for running new experiment rounds.
- `models/` is the **frozen output** — when a round becomes a released version,
  its code is copied here (duplication is intentional) so the model stays
  reproducible even as the research loop keeps changing.

Every folder runs **in place** with no arguments and no cross-folder code
dependencies; generated artifacts (`*.pt`, `*.bin`, `*.pkl`, `input.txt`,
`raw.txt`) stay in the folder and are gitignored.

| Version | Folder | What it is | Held-out BPC |
|---------|--------|-----------|--------------|
| v1 | [`shakespeare-nanogpt-1/`](shakespeare-nanogpt-1/) | base char-level baseline (Tiny Shakespeare, ~10.6M) | — |
| v2 | [`shakespeare-nanogpt-2/`](shakespeare-nanogpt-2/) | Round 3 winner — modern + BPE (Complete Works, ~29.9M) | 1.919 |
| v3 | [`shakespeare-nanogpt-3/`](shakespeare-nanogpt-3/) | r6 float32 winner — 1024-vocab corpus-trained BPE + enlarged corpus (~11.0M, ~1/3 v2's size) | **1.831** |

Each folder has the same shape:

```
model.py  config.py  train.py  sample.py  eval.py  prepare.py  configurator.py  README.md
```

```bash
cd models/<version>
python prepare.py     # build the dataset into this folder
python train.py       # -> ./ckpt.pt   (zero-arg run reproduces the version; knobs in config.py)
python eval.py        # score ./ckpt.pt on the shared held-out test (BPC)
python sample.py --start="ROMEO:"
```

The single shared yardstick — `projects/shakespeare/test.txt` — is *not* duplicated into
each folder; `eval.py` reads it from the repo so every version is scored on the
exact same held-out text. See [`MODELS.md`](../MODELS.md) for the full series spec
and [`research-docs/model-cards/`](../../../research-docs/model-cards/) for each version's model card.
