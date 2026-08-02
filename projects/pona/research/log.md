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

### Round-1 results (2026-08-02, same day)

The controlled span manipulation worked, and the verdict is two-sided:

- **word-r1: 96.0%** [94.6, 97.0] error-only, **exactly the corpus's 96.0%
  ceiling** (corpus-relative 100.0%). Hazard 0.101%/char — well under glyph
  omni-xl's 0.171% despite the formally harder grammar. ABOVE the null:
  the span thesis's strong zone.
- **char-r1: 92.3%** [90.5, 93.8], corpus-relative 96.2%. Hazard 0.194%/char —
  *worse* than glyph per character; the CI straddles the 93.2% null, so the
  cross-project comparison is honestly inconclusive for the char arm. Clearly
  above 71% per-unit.
- **The clean evidence is within-language**: same corpus, body, grammar,
  epochs — 5× shorter spans → hazard halves (0.194% → 0.101%). That's the
  memo's §5.1 mechanism observed under control, not compared across projects.
- **P3, with a twist**: word-arm hard errors lean particle 23 / vocab 10 (as
  registered); the char arm inverts (33 / 41) because its vocabulary class IS
  its misspellings — non-word rate 0.334%, under the registered 2% bound
  (kenosha-kid-style sub-lexicon drift, mild). The failure mode follows the
  tokenizer, which is itself a span-thesis-shaped result.
- **Memorization**: 8-gram overlap ~1.2% both arms (no lookup table); exact
  sentence matches 5.7%/5.1% — concentrated in short stock sentences
  ("mi pona." class), worth the caveat but not disqualifying.
- P4 (ambiguity-vs-temperature) NOT run: jan Lope's parser needs SWI-Prolog,
  which isn't installed; noted as future work rather than half-measured.

Dialogue round: prompt v2 (few-shot + hardened parser) after the pilot showed
olmo-3-7b answers in English (the oracle filter catching exactly what the
brief feared). Full sweep: gemma-26b 43/72 kept, gemma-26b-qat 43/72, qwen3.6
36/72 — **122 dialogues, 936 turns**, every sentence oracle-clean, provenance
in `data/dialogue_manifest.json`. Chat mix: ×12 reps ≈ 4.6% of chars
(`chat-r1`, from scratch, word-arm recipe).
