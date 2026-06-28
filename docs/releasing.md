# Releasing a version

A research round becomes a released model `<project>-N` by **snapshotting** it into
a frozen, self-contained folder — not by pointing at the evolving `core/`. The
snapshot stays reproducible forever; `core/` is free to move on.

## Why snapshot instead of share

`core/` changes round to round. If a release imported `core/`, re-running it later
would silently use newer code. So a release vendors its own copy of every file it
needs (`model.py`, `config.py`, `train.py`, `sample.py`, `eval.py`, `prepare.py`,
`configurator.py`). The duplication is the point — it pins the recipe.

## Steps

1. **Pick the winning run.** Confirm its bits-per-character on the held-out test
   (`core/eval/eval.py` — see [`workflows.md`](workflows.md)).

2. **Create the frozen folder** `projects/<project>/models/<project>-N/` and copy
   in the exact code that produced the run. It must run **in place** with no
   arguments and no cross-folder imports:

   ```bash
   cd projects/<project>/models/<project>-N
   python prepare.py && python train.py && python eval.py && python sample.py
   ```

   The shared held-out `test.txt` is read from the project root, not duplicated.

3. **Write the model card** at `research-docs/model-cards/<project>-N.md`
   (details, intended use, data, evaluation with charts, limitations).

4. **Update the records:**
   - `projects/<project>/leaderboard.md` — a scored row.
   - `projects/<project>/MODELS.md` — the version entry and what changed.
   - `registry.json` — a model entry (id, tag, arch, tokenizer, params, BPC, card,
     artifact urls — `null` until weights/ONNX are published).

5. **Tag it:** `git tag <project>-N` so the exact repo state is recoverable.

6. **Publish artifacts** (when ready): upload `ckpt.pt` / `.onnx` to a GitHub
   release or R2 and fill the `artifacts` urls in `registry.json`. Weights never
   enter the tree.

## Invariants

- Frozen folders are never refactored to share `core/`.
- Weights, `*.bin`, and ONNX stay gitignored everywhere.
- The whole series is scored on the **same** fixed held-out test, so BPC stays
  comparable across versions.
