# kenosha-kid — research log

The journal: what was tried, why, and what came out. Newest entries at the top.
The per-run scoreboard lives in [`leaderboard.md`](leaderboard.md).

## The question

The entire corpus is punctuated permutations of one six-word phrase —
*you never did the kenosha kid* (Pynchon, *Gravity's Rainbow* I.10; Darius
Kazemi's [@YouNeverDidThe](https://x.com/youneverdidthe) bot). A bot enumerates
that space flatly and exactly. **What does a *learned* char-level model do with
it?** The hoped-for answer: it doesn't enumerate, it *orbits* — sampled warm it
keeps returning to the six words but keeps landing slightly differently
(drifted punctuation, near-misses like "nevver"). Verbatim convergence is the
enemy, not the win; the blur is the artifact.

This is also the studio's tightest sampler-aesthetic loop: tiny corpus, minutes
per train, so temperature/capacity effects are visible immediately — a unit test
for the soft-capping "dreaminess" knob that a later project (daydream) needs.

---

## 2026-06-28 — setup

- Decided char-level on the **shared core** engine (not a vendored base engine):
  core already honors `meta.pkl` as a tokenizer contract end-to-end, so no core
  change — see [ADR-0012](../../../docs/adr/0012-pluggable-tokenization.md).
- Wrote `generate.py`: deterministic reimplementation of Kazemi's bot (we own the
  generator rather than scraping it, which keeps the corpus frozen/in-repo and —
  crucially — lets us **weight** Pynchon's nine construals as high-frequency
  anchors over the brute-force permutation tail). Seed 1973.
- Corpus v1 knobs: `N_LINES=24000`, `ANCHOR_FRACTION=0.18`.
- Model v1 (`config.py`): n_layer=4, n_head=4, n_embd=128, block_size=128 —
  deliberately sub-baby (~0.8M params); capacity is a dreaminess knob.

_(run results appended below as they land)_
