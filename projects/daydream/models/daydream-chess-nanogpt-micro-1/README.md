# `daydream-chess-nanogpt-micro-1` — frozen release (v1, Micro / 5×5)

A self-contained, runnable snapshot — no dependency on the project root or
the shared `core/` engine (see
[ADR-0003](../../../../docs/adr/0003-frozen-self-contained-releases.md)).

| File | Role |
|---|---|
| `games.txt` | vendored self-play corpus (synthetic, seeded, code-owned — committed, same treatment as kenosha-kid's `raw.txt`) |
| `prepare.py` | char-tokenizes `games.txt` → `micro/{train,val}.bin` + `meta.pkl` |
| `model.py`, `train.py`, `configurator.py`, `sample.py` | vendored copies of the shared `core/nanogpt_core` engine, unmodified |
| `engine_client.py` | UCI-over-subprocess client for Fairy-Stockfish |
| `harness.py` | plays this checkpoint against Fairy-Stockfish under the built-in `gardner` variant; also the verification tool |
| `config.py` | the exact hyperparameters used for this release |

**Requires Fairy-Stockfish on `PATH`** (`brew install fairy-stockfish`) to
run `harness.py` — Micro uses the engine's *built-in* `gardner` variant
directly, no custom `variants.ini` needed. See
[ADR-0021](../../../../docs/adr/0021-daydream-fairy-stockfish-dependency.md).

## Rebuild in place

```bash
cd projects/daydream/models/daydream-chess-nanogpt-micro-1
python prepare.py             # -> micro/{train,val}.bin + meta.pkl
python train.py config.py     # -> ./ckpt.pt (2500 iters, val ~0.72)
python harness.py --games 30  # verification: legal-move rate, clean-completion rate
```

No weights here — regenerates deterministically from this code (see
[ADR-0002](../../../../docs/adr/0002-no-weights-in-tree.md)).

Model card: [`research-docs/model-cards/daydream-chess-nanogpt-micro-1.md`](../../../../research-docs/model-cards/daydream-chess-nanogpt-micro-1.md).
