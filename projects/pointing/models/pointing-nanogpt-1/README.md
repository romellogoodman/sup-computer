# `pointing-nanogpt-1` — frozen release (v1, the 2.66M arm)

A self-contained, runnable snapshot of the exact code that produced this
model, with no dependency on the project root or the shared `core/` engine
(see [ADR-0003](../../../../docs/adr/0003-frozen-self-contained-releases.md)).

One character-level GPT, 6L/6H/192E, 2.66M parameters, over a 58-symbol
vocabulary. It reads a lowercased line with its punctuation removed and
emits one mark per gap, each word's slot preceded by the word's first
letter. Trained on the shakespeare xl corpus with its marks stripped, held
out by whole work. Internal name: `regular-r1`. The evidence is in
`../../research/`.

On 27,995 lines from nine held-out works it gets 32.5% exactly right at
temperature 0, against 24.7% for "no marks, then a period": period F1 66.9%,
comma F1 44.5%, 99.1% of outputs well-formed.

| File | Role |
|---|---|
| `strip.py` | the transform: a line → its words and its marks. The only definition of a mark |
| `build_corpus.py` | fetches the thirteen Gutenberg volumes (needs network), cuts them into 56 works and into verse / prose / other units, assigns works to splits → `corpus/` and `split_manifest.json`. The source list is vendored from the shakespeare project |
| `split_manifest.json` | **the record**: every work, its split, its Gutenberg volume, the edition as the e-text states it, and a SHA-256 of the file the release was built from |
| `prepare.py` | char tokenizer → `tokenized/{train,val}.bin + meta.pkl` |
| `model.py`, `train.py`, `checkpoint.py`, `configurator.py` | vendored copies of the shared engine, imports localized, otherwise unmodified |
| `config.py` | the exact released hyperparameters |
| `train_curve.py` | what trained the release: drives `train.py` in segments and keeps fifteen snapshots, `ckpt-<iter>.pt` |
| `harness.py` | the eval: slot strings at temperature 0, diffed against the corpus → `results/` |
| `sample.py` | point a line of your own |
| `modern_sample.txt` | twenty hand-typed lines of modern English for `harness.py --modern` |

## Rebuild in place

```bash
python build_corpus.py        # network on first run; rewrites split_manifest.json
python prepare.py
python train_curve.py         # the release run. Or one pass: python train.py config.py
python harness.py             # the test works → results/eval-pointing-nanogpt-1.json
python harness.py --curve     # every snapshot, 4,000 lines
python harness.py --modern    # the twenty modern lines
python sample.py "who is there what do you want"
```

Python deps: `torch`, `numpy`. `ckpt.pt`, the snapshots, `meta.pkl` and the
corpus live here locally but never enter git. The released weights are the
artifacts in `registry.json`.

The rebuild is exact only while Project Gutenberg serves the same files.
`build_corpus.py` records each file's SHA-256, so a `git diff` on
`split_manifest.json` after a rebuild shows whether a volume has changed
under the release. The training recipe, the split and the transform are
exact.

`train_curve.py` restarts the engine at each snapshot, and each restart
re-runs one evaluation, which draws from the random stream. A single pass
through `train.py config.py` is the same recipe and schedule but will not
reproduce the released weights bit for bit.
