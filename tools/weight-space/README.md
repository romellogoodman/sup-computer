# weight-space

*Can a frontier model improve a small model by editing its weights directly, with no gradients? A 50-pass probe harness, planted faults with answer keys, and a held-out scorer.*

Experiment 15's apparatus. It tests the claim in MIT's "Sparks of Weight-Space Programming" (2 Nov 2026) on the studio's released models. A helper agent gets one model's weights and a brief (`briefs/`). It may analyse the weights freely, but it can only *run* the model through `probe.py`, which charges one of 50 passes per call. The researcher then scores the helper's `final.pt` against the original on a held-out half of the val split the helper never sees.

| file | what it does |
| --- | --- |
| `harness.py` | Loads any of the six releases from its frozen `model.py`, splits each val.bin into a probe half and a test half, and holds the GPU lock. |
| `probe.py` | The helper's only way to run its model. `loss`, `sample` and `acts` each cost 1 of 50 passes, and every call is logged to `ledger.jsonl`. |
| `setup.py` | Extracts each release's weights to `work/<model>/base.pt` and scores one model on the test half. |
| `compare.py` | Paired held-out scoring of `final.pt` against `base.pt` over 256 windows: delta, standard error, windows better, and weights changed. |
| `plant_green.py` | The conspicuous plant: adds 6.0 × unit(E[" green"]) to 32 columns of gatsby's `h.3.mlp.c_proj`. |
| `plant_swap.py` | The hidden plant: swaps the `c_proj` write vectors of 240 neuron pairs in gatsby's `h.0`. Every tensor's column norms and singular values stay exactly the same. |

`briefs/` holds the prompts the helpers received, and `evidence/` holds their notes, pass ledgers and the plants' answer keys. Weights live in `work/` and are gitignored (`*.pt`).

```bash
uv run python tools/weight-space/setup.py setup            # base.pt for all six releases
uv run python tools/weight-space/probe.py gatsby loss base # one pass
uv run python tools/weight-space/compare.py                # researcher-only, held-out
```
