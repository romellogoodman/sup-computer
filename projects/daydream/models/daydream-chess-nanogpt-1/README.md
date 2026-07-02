# `daydream-chess-nanogpt-1` — frozen release (v1, Regular / 8×8)

A self-contained, runnable snapshot of the exact code that produced this
model — no dependency on the project root or the shared `core/` engine (see
[ADR-0003](../../../../docs/adr/0003-frozen-self-contained-releases.md)).

| File | Role |
|---|---|
| `fetch_filtered.py` | streams a Lichess monthly dump, filters to ~1400–1800 Elo, converts SAN→UCI → `games.txt` (needs network) |
| `prepare.py` | char-tokenizes `games.txt` → `regular/{train,val}.bin` + `meta.pkl` |
| `model.py`, `train.py`, `configurator.py`, `sample.py` | vendored copies of the shared `core/nanogpt_core` engine, unmodified |
| `engine_client.py` | UCI-over-subprocess client for Fairy-Stockfish |
| `harness.py` | plays this checkpoint against Fairy-Stockfish, resampling on illegal moves; also the verification tool |
| `config.py` | the exact hyperparameters used for this release |

**Requires Fairy-Stockfish on `PATH`** (`brew install fairy-stockfish`) to run
`harness.py` — see [ADR-0021](../../../../docs/adr/0021-daydream-fairy-stockfish-dependency.md).
Not needed for `train.py`/`sample.py` alone.

## Rebuild in place

```bash
cd projects/daydream/models/daydream-chess-nanogpt-1
python fetch_filtered.py      # -> games.txt (network; Lichess Jan 2018 dump)
python prepare.py             # -> regular/{train,val}.bin + meta.pkl
python train.py config.py     # -> ./ckpt.pt (3000 iters, val ~0.86)
python sample.py --out_dir=. --data_root=. --device=mps --start=$'\n' --num_samples=1 --max_new_tokens=200
python harness.py --games 30  # verification: legal-move rate, clean-completion rate
```

No weights here — the checkpoint regenerates from this code plus a fresh
Lichess download (see
[ADR-0002](../../../../docs/adr/0002-no-weights-in-tree.md)).

Model card: [`research-docs/model-cards/daydream-chess-nanogpt-1.md`](../../../../research-docs/model-cards/daydream-chess-nanogpt-1.md).
