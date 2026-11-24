# `oblique-nanogpt-1` — frozen release (v1)

A self-contained, runnable snapshot of the exact code that produced this
model, with no dependency on the project root or the shared `core/` engine
(see [ADR-0003](../../../../docs/adr/0003-frozen-self-contained-releases.md)).

One char-level GPT, 4 layers, 4 heads, 128 embedding, block 128, 797,312
parameters over a 38-symbol vocabulary. It writes one-line aphorisms in two
registers behind a control token: `[s]` for a sideways instruction to a stuck
artist, `[f]` for a sincere fortune. The release is step 12,000 of the
seed-1337 run (internal name: `seed1337`), validation loss 0.7689.

| File | Role |
|---|---|
| `corpus.txt` | **pinned**: the 30,000-line training corpus, 15,000 per register. It was written by four LLMs, so it cannot regenerate; this copy is the release's record |
| `filter-log.json` | what the corpus filter dropped, per generator and per reason, and the deck-leakage check (0 matches) |
| `prepare.py` | 90/10 split by whole line → `oblique/{train,val}.bin + meta.pkl` |
| `model.py`, `train.py`, `checkpoint.py`, `configurator.py` | vendored copies of the shared engine, imports localized, otherwise unmodified |
| `config.py` | the exact released hyperparameters (12,000 steps, seed 1337) |
| `sample.py` | deals lines: a register, a temperature, a count |
| `harness.py` | the automatic eval: memorization, well-formedness and register separation per (temperature × soft-cap) cell |

## Rebuild in place

```bash
python prepare.py                 # corpus.txt -> oblique/{train,val}.bin + meta.pkl
python train.py config.py         # ~75 ms a step on an M-series GPU; about 15 minutes
python sample.py                  # ten strategies at temperature 0.6
python sample.py --register f --n 5
python harness.py --caps none --out harness.json
```

Python deps: `torch`, `numpy`, and `rapidfuzz` for the harness. `ckpt.pt` and
`oblique/meta.pkl` live here locally but never enter git; the released
weights are the artifacts in `registry.json`.

The default temperature, 0.6, is where the rated keeper rate was highest. It
is the best of five noisy settings, not a confirmed peak: see the report,
[Is oblique a temperature?](../../../../research-docs/reports/is-oblique-a-temperature.md)

The raw generator responses, the synthgen manifest with per-response cost,
and the filter that turned them into `corpus.txt` are in
[`../../data/`](../../data/).

Model card: [`research-docs/model-cards/oblique-nanogpt-1.md`](../../../../research-docs/model-cards/oblique-nanogpt-1.md).
