# core — the shared engine

The living train/sample/eval/export engine every project rides
(modern architecture only: RoPE, RMSNorm, bias-free). Frozen releases under
`projects/*/models/<version>/` deliberately do **not** import this — they
carry their own snapshot (ADR-0003).

```
nanogpt_core/   the installable package: model.py, train.py, sample.py, configurator.py
eval/eval.py    CLI: bits-per-character on a held-out file
export/export.py CLI: parity-checked ONNX export of a frozen release
tests/          end-to-end smoke test (train → resume → sample → eval → export)
```

`eval/` and `export/` are CLI scripts, not package modules — kept out of the
package so `import eval` / `import export` never shadow builtins. The
dist-name/import-name split is deliberate: the package installs as
`supcomputer-core`, imports as `nanogpt_core`.

Two flag dialects exist, inherited from nanoGPT: `train.py`/`sample.py` use
the exec-configurator (`--data_root=...`, underscore), `eval.py`/`export.py`
use argparse (`--data-dir ...`, dash). Commands for all four are in
[`docs/workflows.md`](../docs/workflows.md).
