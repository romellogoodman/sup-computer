# `lucky-nanogpt-power-1` — frozen release (v1, Lucky Power / Powerball)

A self-contained, runnable snapshot with no dependency on the project root or
the shared `core/` engine (see
[ADR-0003](../../../../docs/adr/0003-frozen-self-contained-releases.md)).
This is the history version: it reads the last 8 draws and predicts the next.

| File | Role |
|---|---|
| `draws.csv` | every Powerball draw under the 69/26 matrix, 7 Oct 2015 to 21 Nov 2026 (1,436 draws), vendored; whites sorted as published |
| `provenance.json` | source URLs, fetch dates, and the cross-check between the two sources |
| `prepare.py` | tokenizes `draws.csv` → `draws.bin` + `meta.pkl` (one token per number, 71-token vocab) |
| `common.py` | the game definition: tokens, the 28.122-bit floor, draw-boundary examples, the white shuffle, the 120-ordering scorer |
| `model.py`, `configurator.py` | vendored copies of the shared `core/nanogpt_core` engine, unmodified |
| `train.py` | the project's own loop: examples cut as "8 draws → next draw", loss on the final draw, whites reshuffled every epoch |
| `config.py` | the exact hyperparameters used for this release |
| `eval.py` | held-out bits per draw against the floor, at set level |
| `harness.py` | the pick harness: tape, seeded temperature-1 sampling, resample until valid, the valid-ticket rate and the memorization check |

## Rebuild in place

```bash
cd projects/lucky/models/lucky-nanogpt-power-1
python prepare.py                    # -> draws.bin + meta.pkl
python train.py                      # -> ckpt.pt (early-stopped, step 300), ckpt_final.pt, log.jsonl; ~45 min on CPU
python eval.py                       # 28.6868 bits/draw held out, +0.5644 from the floor
python harness.py pick               # a ticket from the last 8 draws in the corpus; rejects print first
python harness.py rate --n 1000000   # 80.2% of raw samples are valid tickets
```

Training runs on CPU from seed 1337. The released weights are `ckpt.pt`, the
step with the lowest loss on the validation split. `ckpt_final.pt` is step
3000, kept because it is the memorized model the report measures: 36.25
bits/draw held out.

No weights here. They regenerate from this code (see
[ADR-0002](../../../../docs/adr/0002-no-weights-in-tree.md)).

Model card: [`research-docs/model-cards/lucky-nanogpt-power-1.md`](../../../../research-docs/model-cards/lucky-nanogpt-power-1.md).
