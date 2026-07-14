# `glyph-nanogpt-1` — frozen release (v1, the generalist)

A self-contained, runnable snapshot of the exact code that produced this
model — no dependency on the project root or the shared `core/` engine (see
[ADR-0003](../../../../docs/adr/0003-frozen-self-contained-releases.md)).

One letter-conditioned model, 12L/8H/576E ≈ 47.8M params, that draws all 26
lowercase letters. Released *knowing* it lost the drawing-reliability
bake-off to the 26 per-letter specialists it was measured against
(experiment 09, "One model or twenty-six?") — the studio chose the single
evolving instrument on purpose, and the case's numbers stand as the fixed
yardstick every future version tries to overtake.

| File | Role |
|---|---|
| `fetch_fonts.py` | sparse clone of google/fonts (OFL sans upright) → `gfonts/` + `manifest.json` (needs network) |
| `codec.py` | glyph outlines ↔ one-char-per-token text (ADR-0027); encoder, strict decoder, SVG path |
| `encode_corpus.py` | every manifest font (VF weights instanced) → `corpus/<letter>.txt` |
| `prepare.py` | dedup, family split → `omni/{train,val}.bin` + `meta.pkl`, `test/<letter>.txt` |
| `model.py`, `train.py`, `configurator.py`, `sample.py`, `eval.py` | vendored copies of the shared engine, imports localized, otherwise unmodified |
| `harness.py` | samples the checkpoint per letter; reports parse / unterminated / memorization rates and renders a specimen sheet |
| `config.py` | the exact released hyperparameters, including the big-model optimizer recipe (lr 1e-4, beta2 0.95) after the small-model recipe diverged 3× |

## Rebuild in place

```bash
python fetch_fonts.py      # network: pulls the pinned OFL sans pool
python encode_corpus.py
python prepare.py
python train.py config.py  # ~2.2s/iter on an M4; ~2h to 3000 iters
python eval.py . --test test/a.txt --data-dir .   # per-letter BPC
python harness.py . --letters aeg --num 64        # validity + specimen sheet
```

Weights (`ckpt.pt`), font binaries, and datasets are gitignored — the
checkpoint ships via the artifact URLs in the root `registry.json`.
