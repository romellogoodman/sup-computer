# kenosha-kid-nanogpt-1

The **Kenosha Kid** model: a ~0.79M-parameter character-level GPT whose entire
world is six words — *you never did the kenosha kid*, the phrase Tyrone Slothrop
fixates on under sodium amytal in Thomas Pynchon's *Gravity's Rainbow* (I.10),
and the seed of Darius Kazemi's [@YouNeverDidThe](https://x.com/youneverdidthe)
bot. Sampled warm it doesn't recite — it **dreams permutations**: it returns to
the six words and lands slightly differently each time (reordered, repunctuated,
the occasional near-miss like "Kenoshar" or "youkid"). The blur is the artifact;
verbatim convergence is the failure mode.

This folder is a **frozen, self-contained snapshot** of exactly the code +
corpus that produces v1, copied out of the project root so the working pipeline
can keep evolving without changing how this released version is built (see
[ADR-0003](../../../../docs/adr/0003-frozen-self-contained-releases.md) and
[`docs/releasing.md`](../../../../docs/releasing.md)). Day-to-day, kenosha-kid
rides the shared `core` engine ([ADR-0012](../../../../docs/adr/0012-pluggable-tokenization.md));
a release, however, **vendors a snapshot of that engine** so it reproduces
forever, independent of `core` drift. It runs **in place** with no project-root
dependency and no shared-`core` dependency — `model.py` / `train.py` / `sample.py`
/ `configurator.py` are vendored here (the **modern** arch: RoPE, RMSNorm,
bias-free), and the corpus is vendored as `raw.txt`.

- Tokenizer: character-level (vocab derived from the corpus; `meta.pkl` is the contract)
- Data: synthetic, deterministic corpus of 24,000 lines — punctuated permutations of the six words, with Pynchon's nine construals injected as high-frequency anchors over the brute-force tail; vendored as `raw.txt` (regenerable byte-for-byte by `generate.py`, no external deps, no scrape)
- Architecture: modern char-level nanoGPT (RoPE, RMSNorm, bias-free Linears)
- Size: 4 layers · 4 heads · 128 embd · 128 context · ~0.79M params
- Champion checkpoint: the **350-iter mid-transition** checkpoint, val loss **~0.48** (MPS) — stopped on purpose in the middle of the memorization phase transition, where the spellings are good enough that the anchors surface but loose enough that it still dreams
- Model card: [`research-docs/model-cards/kenosha-kid-nanogpt-1.md`](../../../../research-docs/model-cards/kenosha-kid-nanogpt-1.md)
- Research journal: [`../../research/`](../../research/)
- Git tag: `kenosha-kid-nanogpt-1`

## Reproduce

Everything runs in place from this folder; generated files (`kenosha/train.bin`,
`kenosha/val.bin`, `kenosha/meta.pkl`, `ckpt.pt`) stay here and are gitignored.
The vendored `raw.txt` is committed — no regeneration is needed (and `generate.py`
would rebuild it identically anyway).

```bash
cd projects/kenosha-kid/models/kenosha-kid-nanogpt-1
python prepare.py             # raw.txt -> kenosha/{train,val}.bin + kenosha/meta.pkl (here)
python train.py config.py     # trains -> ./ckpt.pt (the champion; knobs live in config.py)
python sample.py --out_dir=. --data_root=. --device=cpu --start=$'\n' --temperature=0.9
```

`sample.py` defaults to `device='cuda'`, so pass `--device=cpu` (or `--device=mps`
on Apple Silicon). Sample **warm** — the dream lives at temperature; cold sampling
collapses toward the anchors. Override any hyperparameter on the command line,
e.g. `python train.py config.py --max_iters=2000` (which locks the spellings and
flattens the dream — see the research journal for why 350 is the champion).

## No weights here (this folder ships CODE)

The trained weights are **not** in this folder. `*.pt`, `*.bin`, and `*.pkl` are
gitignored and regenerate deterministically from the vendored `raw.txt` + the
pinned config via the commands above. The released weights live as **release
artifacts** (referenced by the top-level [`registry.json`](../../../../registry.json)),
not in the git tree — per the monorepo's no-weights-in-the-tree rule. This
snapshot is pinned to git tag `kenosha-kid-nanogpt-1`.

## Files

| File | Role |
|------|------|
| `model.py` | the GPT architecture (modern char-level nanoGPT: RoPE, RMSNorm, bias-free) — vendored from `core` |
| `config.py` | the champion hyperparameters + self-contained paths (`out_dir='.'`, `data_root='.'`) |
| `train.py` | training loop; writes `ckpt.pt` here — vendored from `core` |
| `sample.py` | generate text from `ckpt.pt` (pass `--device=cpu`/`--device=mps`) — vendored from `core` |
| `prepare.py` | build the dataset into `./kenosha/` from `raw.txt` |
| `generate.py` | regenerate `raw.txt` deterministically (the bot reimplementation; not needed — corpus is vendored) |
| `configurator.py` | nanoGPT's `--key=value` override helper — vendored from `core` |
| `raw.txt` | the vendored corpus (24,000 lines; committed, not regenerated) |
