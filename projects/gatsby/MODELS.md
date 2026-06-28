# Models

A registry of trained `gatsby-nanogpt-N` versions — spec, git tag, and the
commands to rebuild each. Weights are never committed; everything needed to
reproduce them is.

_No release yet._ The pipeline at the repo root produces the first model:

```bash
python generate.py --n 4000 --batch   # synthetic corpus via the Claude API
python prepare.py                       # train/val.bin, meta.pkl
python train.py                         # -> ckpt.pt
```

When the first model is worth pinning, freeze a self-contained
`models/gatsby-nanogpt-1/` snapshot (`model.py`, `config.py`, `train.py`,
`sample.py`, `prepare.py`, `configurator.py`, plus the generation prompt that
produced its corpus) and record it here: corpus size, `green` level
distribution, generation model, training spec, git tag, and sample output.
