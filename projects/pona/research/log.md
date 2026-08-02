# pona — research log

## 2026-08-02 — round 1: scaffold, corpus, oracle, two arms

Rebuilt from the July brief in a live design session (decision board), then
executed. The decisions that differ from the brief, and why:

- **P1/P2 re-registered as zones.** The brief's "beat glyph's 71.0%" compared
  per-unit validity across a 4× unit-length gap; under the null model (pona
  exactly at glyph omni-xl's per-char hazard) short sentences alone score
  ~93%. Zones: >93.2% (null at the corpus's measured 41.3-char mean) = span
  thesis confirmed; 71–93.2% mixed; <71% hierarchy wins.
- **Two arms.** Char + word at the same 6L/6H/192E body, same corpus, ~7
  epochs each — a controlled within-language span manipulation (word tokens
  carry constraints across ~5× fewer sampling steps). The word arm's
  368-token vocab doubles as the chat UI keyboard.
- **Synthetic dialogue unlocked, oracle-filtered.** The brief banned synthgen
  (models hallucinate confident fake Toki Pona); the user authorized LM Studio
  generation for the chat goal. The reconciliation: a generated dialogue
  enters the corpus only if *every* sentence passes the same telo misikeke
  error-only check the model is scored by. Per-model keep rates are a result.
- **Gate measured post-dedup** (name-blind, kills templated wiki stubs):
  6.93M chars, CLEAR at 13× threshold.

Corpus baseline (pre-registered check, 20k-sentence sample): **96.0%**
error-only pass; per-source Tatoeba 99.0% / poki 96.9% / Wikipedia 86.9% —
the register prediction (edited encyclopedic text scores worst under a
snapshot parser) landed. Mean sentence 41.3 chars → null line 93.2%.

Oracle: telo misikeke pinned @ 0a1852d, MIT, verified 16/16 known-good +
7/7 known-bad before any number was reported (`oracle/verify_oracle.py`).

Round-1 runs: `char-r1` (65-vocab, 6.2M train tokens, 3000 iters),
`word-r1` (368-vocab, 1.7M train tokens, 1500 iters). Sequential on MPS.
