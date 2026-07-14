# ADR 0029: core exports a library surface (load, tokenize, score)

- **Status:** Accepted (extends [ADR-0012](0012-pluggable-tokenization.md)'s meta.pkl seam into core)
- **Date:** 2026-07-14
- **Deciders:** Romello Goodman (with Claude)

## Context

`core/` shipped CLIs but exported almost nothing importable, so every project
re-pasted the same rituals. A code review counted the checkpoint-load block
(`torch.load` → `GPTConfig` → strip wrapper prefixes → `eval().to(device)`)
at ten sites, already drifted: one used `weights_only=False`, only one
stripped the DDP prefix. Tokenizer resolution was worse — ADR-0012's meta.pkl
seam grew a third shape (`{"vocab_size", "tokenizer"}` for corpus-trained HF
BPE) that core never learned, so shakespeare wrote `eval_xl.py`/`sample_xl.py`
for one round and gatsby copied them into its *permanent* living path
(`_runtime.py`, post-ADR-0023). And because `core/eval/eval.py` was
deliberately unimportable (pyproject packages only `nanogpt_core`, to avoid
shadowing builtins), glyph's `matrix_eval.py` shelled out and regex-scraped
`BPC=([\d.]+)` from stdout — a print line as a load-bearing API.

## Decision

**1. `nanogpt_core` exports the three rituals.**
`nanogpt_core.checkpoint` owns `pick_device` (cuda > mps > cpu),
`load_model(out_dir, device) → (model, ckpt)` (weights_only=True; strips both
`_orig_mod.` and `module.` prefixes), and `load_tokenizer(ckpt, data_root)` —
which resolves all three meta.pkl shapes, including the HF `tokenizer.json`
branch, behind one `Tokenizer(kind, encode, decode)` interface. The
`tokenizers` library is a lazy import declared as core's `hf` extra.

**2. BPC scoring is a function, not a print line.** `nanogpt_core.bpc`
exports `score` and `score_run(out_dir, test_path, data_root) → dict`;
`core/eval/eval.py` is a thin CLI shim over it. Harnesses import the dict.
The eval CLI keeps `--data-dir` as an alias but the canonical spelling is
`--data_root`, matching train/sample; it also gains `--device`.

**3. The living consumers ride it.** shakespeare's `eval_xl.py`/`sample_xl.py`
are deleted (core's own eval/sample now handle their datasets); gatsby's
`_runtime.py` shrinks to wrappers; kenosha-kid, daydream, and glyph's local
load blocks and `sys.path` hacks to core are gone; `matrix_eval.py` calls
`score_run` in-process. Frozen releases are untouched, per ADR-0003.

One enabling fix rode along: the configurator now splits `--key=value` once,
so values may contain `=` (gatsby's `--start="[green=5] ..."` primes used to
crash core's sample.py — one reason the project-local copies existed).

## Consequences

- A new project's harness is `from nanogpt_core import load_model` instead of
  ten pasted lines; eval results are structured data everywhere.
- The eval print format is no longer an API — changing it breaks no one.
- Core's library surface is now something to keep stable; the smoke test
  (train → resume → sample → eval → export) covers the CLIs that wrap it.
- kenosha-kid's loader quietly stops using `weights_only=False` (an
  unnecessary unsafe-pickle load); no behavior change, one less footgun.

## Alternatives considered

- **A `--json` flag on eval.py** — the cheap half-fix; still leaves
  subprocess + parse at every harness and the load/tokenize copies in place.
- **Packaging `eval`/`export` as modules** — rejected by the original layout
  for builtin-shadowing reasons that still hold; moving the *logic* into
  `nanogpt_core` gets the import without the shadowing.
