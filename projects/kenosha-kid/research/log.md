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

**Runs (all on corpus v1, model v1 — 0.79M params, char-level, on shared core):**

- **r1** — 2000 iters, best val **0.4325**. Words crisp, *zero* misspelling; the
  drift is entirely in **word order and punctuation**. The Pynchon anchors snap
  into focus ("You! Never did the Kenosha Kid"; "You, Never? Did the Kenosha
  Kid?"). The **lucid** dream — recognizable, orbiting, but spellings perfect even
  sampled hot. The corpus never misspells, so a converged model can't either.
- **r2-early** — 150 iters, val **0.59**. Now the words half-form and break at the
  **character** level: "Kenoshau", "nevu", "thethe", "KenoYou?", "YouNever". The
  **deep** dream / hallucination — but at this loss the anchors are too broken to
  reliably surface.
- **r3-mid** — 350 iters, val **0.48**. The balance: anchors still surface
  ("You never did the Kenosha Kid", "You? Never? Did the Kenosha Kid"), the tail
  orbits through punctuated permutations, and you get the *occasional* character
  near-miss ("Kenoshar", "youkid", doubled "Did did kid") without garble. Best at
  **temperature 0.9**. Consistent across seeds (not cherry-picked).

**Finding — dreaminess has two knobs.** The corpus has almost no procedural
competence to learn except the six words, so the only thing the model can vary is
*how* it says them — and that variation is governed by (1) **training progress**
(the memorization phase transition: undertrained → character-level near-misses;
converged → spellings lock and drift retreats to order/punctuation) and (2)
**sampling temperature**. This is the cleanest possible view of that transition
because the corpus is so small the loss craters from 3.37→0.66 in 100 steps and
the whole spectrum fits in a ~2-minute training run. It's the unit test the
soft-capping "dreaminess" sampler (for a later project, daydream) needs.

**Champion → `kenosha-kid-nanogpt-1`:** r3-mid (350 iters, val 0.48), default
sampling temperature 0.9. Loss is deliberately **not** the objective — verbatim
convergence (r1) is a *worse* artifact than the dreaming mid-checkpoint, even
though its loss is lower. The dream is the deliverable.
