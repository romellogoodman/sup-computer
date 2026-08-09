# `pona-nanogpt-1` — frozen release (v1, the conversational word arm)

A self-contained, runnable snapshot of the exact code that produced this
model — no dependency on the project root or the shared `core/` engine (see
[ADR-0003](../../../../docs/adr/0003-frozen-self-contained-releases.md)).

One word-level Toki Pona GPT, 6L/6H/192E ≈ 2.73M params over a 370-token
vocabulary (the ~130-word lexicon plus names, punctuation, and specials —
literally the chat UI's keyboard). Trained on the natural corpus interleaved
with 122 oracle-filtered synthetic dialogues at ×12 reps (≈4.6% of chars).
Its free prose passes [telo misikeke](https://telo-misikeke.gitlab.io/) at
96.9% first-try — above the corpus's own 96.0% — and its chat replies score
100.0% at t = 0.8 (internal name: `chat-r1`; evidence in
`../../research/`).

| File | Role |
|---|---|
| `fetch_wikipedia.py`, `fetch_tatoeba.py`, `fetch_poki.py` | pull the three corpus sources (needs network) → `raw/` |
| `build_corpus.py` | sonatoki sentence filter, licence audit, name-blind dedup, ≥500KB gate → `corpus/natural.txt` |
| `dialogue.txt` | **pinned**: the 122 oracle-clean synthetic dialogues (936 turns). LLM-generated, so it cannot regenerate deterministically — this copy is the release's record; per-dialogue provenance and sha1s in `dialogue_manifest.json` |
| `build_chat_corpus.py` | interleave dialogues ×12 into the natural corpus (seeded) → `corpus/chat.txt` |
| `pona_tok.py`, `prepare.py` | the word tokenizer (own the vocab, never shared with the char arm) → `tokenized-chat/{train,val}.bin + meta.pkl` |
| `model.py`, `train.py`, `checkpoint.py`, `configurator.py` | vendored copies of the shared engine, imports localized, otherwise unmodified |
| `sample.py` | vendored engine sampler, decode rerouted through `pona_tok.detok` — the raw token join is wrong for a word vocab |
| `config.py` | the exact released hyperparameters (1,500 iters, ~3 min on an M4) |
| `oracle/` | telo misikeke wrapper: `fetch_oracle.py` vendors the checker at the pinned commit, `verify_oracle.py` is the trust gate that must pass before any number is reported |
| `harness.py` | the eval: 1,000 raw unconditional sentences → oracle → grammaticality, hazard/char, zone vs the 93.2% null |
| `chat_eval.py`, `talk.py` | reply eval (fixed 20-prompt set) and the multi-turn REPL |

## Rebuild in place

```bash
python fetch_wikipedia.py && python fetch_tatoeba.py && python fetch_poki.py
python build_corpus.py                                  # → corpus/natural.txt
python build_chat_corpus.py --reps 12                   # + dialogue.txt → corpus/chat.txt
python prepare.py --arm word --corpus corpus/chat.txt --out-suffix chat
python train.py config.py                               # ~86ms/iter on an M4; ~3 min
python oracle/fetch_oracle.py && python oracle/verify_oracle.py   # vendor + trust-gate
python harness.py --out_dir .                           # the oracle eval
python chat_eval.py --out_dir .                         # the reply eval
python sample.py --num_samples=3                        # or: python talk.py --out_dir .
```

Python deps: `torch`, `numpy`, `requests`, `sonatoki` (corpus build only);
node ≥ 18 for the oracle. `ckpt.pt` and `tokenized-chat/meta.pkl` live here
locally but never enter git — the released weights are the artifacts in
`registry.json`.

Corpus rebuilds are *near*-identical, not byte-identical: the three sources
are living datasets, so a re-fetch drifts slightly from the 6.93M-char corpus
the release trained on. The training recipe, dialogue set, tokenizer, and
oracle pin are exact.
