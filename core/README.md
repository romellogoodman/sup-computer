# core — the shared engine

The living train/sample/eval/export engine every project rides
(modern architecture only: RoPE, RMSNorm, bias-free). Frozen releases under
`projects/*/models/<version>/` deliberately do **not** import this — they
carry their own snapshot (ADR-0003).

```
nanogpt_core/   the installable package: model, train, sample, configurator,
                checkpoint (load_model / load_tokenizer / pick_device), bpc
eval/eval.py    CLI shim over nanogpt_core.bpc — BPC on a held-out file
export/export.py CLI: parity-checked ONNX export of a frozen release
tests/          end-to-end smoke test (train → resume → sample → eval → export)
```

Project harnesses import the library surface instead of pasting load blocks
(ADR-0029):

```python
from nanogpt_core import load_model, load_tokenizer, pick_device
from nanogpt_core.bpc import score_run
```

`eval/` and `export/` are CLI scripts, not package modules — kept out of the
package so `import eval` / `import export` never shadow builtins. The
dist-name/import-name split is deliberate: the package installs as
`supcomputer-core`, imports as `nanogpt_core`.

Two flag dialects exist, inherited from nanoGPT: `train.py`/`sample.py` use
the exec-configurator (`--data_root=...`), `eval.py`/`export.py` use
argparse (`--data_root ...`; eval keeps `--data-dir` as a legacy alias).
Commands for all four are in [`docs/workflows.md`](../docs/workflows.md).
