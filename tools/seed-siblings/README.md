# seed-siblings

*Are identical-recipe models trained on different seeds distinguishable from their output? Sample the siblings, train an attribution classifier, report the confusion.*

Experiment 13's apparatus. The sweep itself is the frozen
[shakespeare-nanogpt-3](../../projects/shakespeare/models/shakespeare-nanogpt-3/)
folder's `train.py` with only `--seed` varied (`projects/shakespeare/runs/seed-sweep/sweep.sh`).

| script | what it does |
| --- | --- |
| `sample.py` | Batched sampling from each sibling's `ckpt.pt` at a fixed temperature; one JSONL per run, each passage tagged with its sampling seed so the split can hold sampling seeds out. |
| `attribute.py` | Trains a [tinyenc](../tinyenc/) 8-way attribution encoder and a hashed 1–3-gram logistic baseline; reports held-out accuracy and the confusion matrix, plus the two binary controls (checkpoint step, temperature). |

```bash
uv run --with tokenizers python tools/seed-siblings/sample.py \
    --runs projects/shakespeare/runs/seed-sweep --out tools/seed-siblings/evidence/2026-09-12/samples
uv run --with tokenizers python tools/seed-siblings/attribute.py \
    --samples tools/seed-siblings/evidence/2026-09-12/samples --out tools/seed-siblings/evidence/2026-09-12/results.json
```
