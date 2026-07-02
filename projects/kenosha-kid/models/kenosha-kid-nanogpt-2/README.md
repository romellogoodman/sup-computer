# kenosha-kid-nanogpt-2

The **drift** Kenosha Kid: a ~0.79M-parameter character-level GPT whose entire
world is six words — *you never did the kenosha kid*, the phrase Tyrone Slothrop
fixates on under sodium amytal in Thomas Pynchon's *Gravity's Rainbow* (I.10),
and the seed of Darius Kazemi's [@YouNeverDidThe](https://x.com/youneverdidthe)
bot. Like v1 it dreams the phrase — returns to the six words and lands slightly
differently each time — but it does something v1 structurally could not: **fully
converged, it still dreams.**

v1 had two coupled dream knobs (training progress and temperature): converged, its
spellings locked and near-misses vanished; you could only get near-misses by
*undertraining*, which also blurred the Pynchon anchors. v2 decouples them with a
**self-drifting corpus** — a controlled per-letter misspelling channel
(`DRIFT_RATE=0.06`) baked into the permutation tail while the 9 anchors stay
pristine. Now a low-loss, converged model reproduces all 9 anchors verbatim AND
carries a near-miss in ~33% of lines ("nevver", "Kenoshar"), near-zero garble.
`DRIFT_RATE` is the dial.

This folder is a **frozen, self-contained snapshot** of exactly the code + corpus
that produces v2, copied out of the project root so the working pipeline can keep
evolving without changing how this released version is built (see
[ADR-0003](../../../../docs/adr/0003-frozen-self-contained-releases.md) and
[`docs/releasing.md`](../../../../docs/releasing.md)). Day-to-day, kenosha-kid
rides the shared `core` engine ([ADR-0012](../../../../docs/adr/0012-pluggable-tokenization.md));
a release, however, **vendors a snapshot of that engine** so it reproduces forever,
independent of `core` drift. It runs **in place** with no project-root dependency
and no shared-`core` dependency — `model.py` / `train.py` / `sample.py` /
`configurator.py` / `eval_dream.py` are vendored here (the **modern** arch: RoPE,
RMSNorm, bias-free), and the corpus is vendored as `raw.txt`.

- Tokenizer: character-level, **39-char** vocab (vs v1's 27 — the drift channel's
  substitutions introduce the full lowercase alphabet; `meta.pkl` is the contract)
- Data: synthetic, deterministic corpus of 24,000 lines — punctuated permutations
  of the six words, with Pynchon's nine construals injected as pristine
  high-frequency anchors (~18%) over a **drifted** brute-force tail
  (`DRIFT_RATE=0.06`, ~74% of tail lines carry ≥1 edit); vendored as `raw.txt`
  (regenerable byte-for-byte by `generate.py`, no external deps, no scrape)
- Architecture: modern char-level nanoGPT (RoPE, RMSNorm, bias-free Linears)
- Size: 4 layers · 4 heads · 128 embd · 128 context · ~0.79M params
- Released checkpoint: **converged, 1100 iters**, best val loss **~0.65** (MPS) —
  trained past the ~700 plateau; the higher val floor vs v1 (0.43) is expected,
  the drift is genuine entropy, so "converged" means plateaued on its OWN corpus
- Dream-score at temperature 0.9 (`eval_dream.py`): anchor-recall **9/9**
  verbatim, near-miss line-rate **~0.33**, garble ~0.002
- Model card: [`research-docs/model-cards/kenosha-kid-nanogpt-2.md`](../../../../research-docs/model-cards/kenosha-kid-nanogpt-2.md)
- Research journal: [`../../research/`](../../research/)
- Git tag: `kenosha-kid-nanogpt-2`

## Reproduce

Everything runs in place from this folder; generated files (`kenosha/train.bin`,
`kenosha/val.bin`, `kenosha/meta.pkl`, `ckpt.pt`) stay here and are gitignored.
The vendored `raw.txt` is committed — no regeneration is needed (and `generate.py`
would rebuild it identically anyway, `DRIFT_RATE` defaulting to 0.06).

```bash
cd projects/kenosha-kid/models/kenosha-kid-nanogpt-2
python generate.py            # (optional) rewrites raw.txt identically (DRIFT_RATE=0.06)
python prepare.py             # raw.txt -> kenosha/{train,val}.bin + kenosha/meta.pkl (here)
python train.py config.py     # trains -> ./ckpt.pt (converged, 1100 iters; knobs in config.py)
python sample.py --out_dir=. --data_root=. --device=cpu --start=$'\n' --temperature=0.9
python eval_dream.py --device=cpu --num_samples=40 --print_lines=20   # the dream-score
```

`sample.py` defaults to `device='cuda'`, so pass `--device=cpu` (or `--device=mps`
on Apple Silicon). Sample **warm** — the dream lives at temperature. Turn the drift
dial and retrain to see the decoupling as a spectrum, e.g.
`python generate.py --drift-rate=0.14 && python prepare.py && python train.py config.py`
(heavier drift → more near-misses, a little garble, an anchor at risk).

## No weights here (this folder ships CODE)

The trained weights are **not** in this folder. `*.pt`, `*.bin`, and `*.pkl` are
gitignored and regenerate deterministically from the vendored `raw.txt` + the
pinned config via the commands above. The released weights live as **release
artifacts** (referenced by the top-level [`registry.json`](../../../../registry.json)),
not in the git tree — per the monorepo's no-weights-in-the-tree rule. This
snapshot is pinned to git tag `kenosha-kid-nanogpt-2`.

## Files

| File | Role |
|------|------|
| `model.py` | the GPT architecture (modern char-level nanoGPT: RoPE, RMSNorm, bias-free) — vendored from `core` |
| `config.py` | the drift/converged hyperparameters + self-contained paths (`out_dir='.'`, `data_root='.'`, `max_iters=1100`) |
| `train.py` | training loop; writes `ckpt.pt` here — vendored from `core` (import repointed to the sibling `model.py`) |
| `sample.py` | generate text from `ckpt.pt` (pass `--device=cpu`/`--device=mps`) — vendored from `core` |
| `prepare.py` | build the dataset into `./kenosha/` from `raw.txt` |
| `generate.py` | regenerate `raw.txt` deterministically (the bot reimplementation + the `DRIFT_RATE` channel, default 0.06); not needed — corpus is vendored |
| `eval_dream.py` | the automated dream-score (anchor-recall + near-miss/garble) — scores `./ckpt.pt` in place |
| `configurator.py` | nanoGPT's `--key=value` override helper — vendored from `core` |
| `raw.txt` | the vendored drift corpus (24,000 lines, `DRIFT_RATE=0.06`; committed, not regenerated) |
