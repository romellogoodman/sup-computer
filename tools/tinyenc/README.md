# tinyenc

*A tiny text-classifier encoder shared by the studio's sense experiments.*

One small transformer encoder over a release's BPE tokenizer, a pooled head,
and a plain training loop with held-out scoring (accuracy, AUROC for binary
tasks, a confusion matrix for multi-class). Written for two consumers at
once — the [linewell](../linewell/) learned judge (experiment 12) and the
[seed-siblings](../seed-siblings/) attribution classifier (experiment 13) —
which is the monorepo's second-consumer rule for extracting shared code.

```python
from tinyenc import Encoder, train_classifier, evaluate
```

Everything is stdlib + torch + the `tokenizers` lib; no sklearn. Run
consumers from the repo root with `uv run --with tokenizers`.
