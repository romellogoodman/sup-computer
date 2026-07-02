# `daydream-chess-nanogpt-grand-1` — frozen release (v1, Grand / 12×10)

A self-contained, runnable snapshot — no dependency on the project root or
the shared `core/` engine (see
[ADR-0003](../../../../docs/adr/0003-frozen-self-contained-releases.md)).

| File | Role |
|---|---|
| `games.txt` | vendored self-play corpus (synthetic, seeded, code-owned — committed) |
| `variants.ini` | the custom `grand12` board config: 12 files × 10 ranks, 2 Chancellor + 2 Archbishop per side — see [ADR-0021](../../../../docs/adr/0021-daydream-fairy-stockfish-dependency.md) for why this board isn't 12×12 |
| `prepare.py` | char-tokenizes `games.txt` → `grand/{train,val}.bin` + `meta.pkl` |
| `model.py`, `train.py`, `configurator.py`, `sample.py` | vendored copies of the shared `core/nanogpt_core` engine, unmodified |
| `engine_client.py` | UCI-over-subprocess client for Fairy-Stockfish |
| `harness.py` | plays this checkpoint against Fairy-Stockfish under the vendored `grand12` variant; also the verification tool |
| `config.py` | the exact hyperparameters used for this release |

**Requires Fairy-Stockfish on `PATH`** (`brew install fairy-stockfish`) to
run `harness.py` — Grand needs the vendored `variants.ini` (unlike Micro,
which uses a built-in variant).

## Rebuild in place

```bash
cd projects/daydream/models/daydream-chess-nanogpt-grand-1
python prepare.py             # -> grand/{train,val}.bin + meta.pkl
python train.py config.py     # -> ./ckpt.pt (3000 iters)
python harness.py --games 30  # verification: legal-move rate, clean-completion rate
```

No weights here — regenerates deterministically from this code (see
[ADR-0002](../../../../docs/adr/0002-no-weights-in-tree.md)).

Model card: [`research-docs/model-cards/daydream-chess-nanogpt-grand-1.md`](../../../../research-docs/model-cards/daydream-chess-nanogpt-grand-1.md).
