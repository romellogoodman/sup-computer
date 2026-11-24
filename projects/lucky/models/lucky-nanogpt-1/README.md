# `lucky-nanogpt-1` — frozen release (v1, Lucky / Maryland Pick 3)

A self-contained, runnable snapshot with no dependency on the project root or
the shared `core/` engine (see
[ADR-0003](../../../../docs/adr/0003-frozen-self-contained-releases.md)).
This is the history version: it reads the last 8 draws and predicts the next.

| File | Role |
|---|---|
| `draws.csv` | every Maryland Pick 3 draw, 29 Jul 1976 to 23 Nov 2026 (28,628 draws), vendored |
| `provenance.json` | source URLs, fetch dates, and every draw the two sources disagree on |
| `prepare.py` | tokenizes `draws.csv` → `draws.bin` + `meta.pkl` (one token per digit, 11-token vocab) |
| `common.py` | the game definition: tokens, the 9.966-bit floor, draw-boundary examples, the scorer |
| `model.py`, `configurator.py` | vendored copies of the shared `core/nanogpt_core` engine, unmodified |
| `train.py` | the project's own loop: examples cut as "8 draws → next draw", loss on the final draw |
| `config.py` | the exact hyperparameters used for this release |
| `eval.py` | held-out bits per draw against the floor |
| `harness.py` | the pick harness: tape, seeded temperature-1 sampling, resample until valid |

## Rebuild in place

```bash
cd projects/lucky/models/lucky-nanogpt-1
python prepare.py        # -> draws.bin + meta.pkl
python train.py          # -> ckpt.pt (early-stopped, step 1100), ckpt_final.pt, log.jsonl; ~30 min on CPU
python eval.py           # 9.9709 bits/draw held out, +0.0051 from the floor
python harness.py pick   # a ticket from the last 8 draws in the corpus
```

Training runs on CPU from seed 1337. The released weights are `ckpt.pt`, the
step with the lowest loss on the validation split; `ckpt_final.pt` is step
3000.

No weights here. They regenerate from this code (see
[ADR-0002](../../../../docs/adr/0002-no-weights-in-tree.md)).

Model card: [`research-docs/model-cards/lucky-nanogpt-1.md`](../../../../research-docs/model-cards/lucky-nanogpt-1.md).
