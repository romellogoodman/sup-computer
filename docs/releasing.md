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

4. **Update the records** (this list is the complete, canonical checklist —
   project docs link here rather than restating it):
   - `projects/<project>/leaderboard.md` — a scored row.
   - `projects/<project>/MODELS.md` — the version entry and what changed.
   - `projects/<project>/models/README.md` — a row in the version table.
   - `registry.json` — a model entry (id, tag, arch, tokenizer, params,
     `block_size` from the frozen `config.py`, BPC, card, artifact urls —
     `null` until weights/ONNX are published — and `demo.prompt`: a starter
     prompt the corpus actually contains, leading whitespace load-bearing).
     This is the only registry: the `/model-player` roster and the `sup` CLI
     both derive newest-runnable-per-lineage from it
     ([ADR-0028](adr/0028-registry-absorbs-the-demo-registry.md)).

5. **Tag it:** `git tag <project>-N` so the exact repo state is recoverable.

6. **Publish artifacts** (when ready): export to ONNX and upload to the R2
   bucket, then fill the `artifacts` urls in `registry.json`. Weights never
   enter the tree. The full pipeline (staging the checkpoint, export, upload,
   registry wiring, browser verification) is documented as the
   [`publish-player-model` skill](../.claude/skills/publish-player-model/SKILL.md);
   conventions in [ADR-0024](adr/0024-model-player-page-and-artifact-conventions.md).

## Invariants

- Frozen folders are never refactored to share `core/`.
- Weights, `*.bin`, and ONNX stay gitignored everywhere.
- The whole series is scored on the **same** fixed held-out test, so BPC stays
  comparable across versions.
