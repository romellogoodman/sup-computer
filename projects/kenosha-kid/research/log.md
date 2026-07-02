# kenosha-kid — research log

The journal: what was tried, why, and what came out. Newest entries at the top.
The per-run scoreboard lives in [`leaderboard.md`](../leaderboard.md).

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

## 2026-07-02 — the drift corpus (decoupling anchors from near-misses)

The champion couples its two dream-qualities — crisp anchors and near-misses —
through *undertraining*: near-misses only exist mid-transition, and the converged
r1 (val 0.43) is "too clean" (zero misspellings). The report
([`dream-a-single-phrase.md`](../../../research-docs/reports/dream-a-single-phrase.md))
named the fix: *"a corpus that itself drifts."* This round tests it, plus a free
sampler-side probe.

**Tooling.** Added `eval_dream.py`, an automated **dream-score** so runs are
comparable, not eyeballed: over ~430 sampled lines it reports **anchor-recall**
(fraction verbatim = 1 of the 9 anchors; how many of 9 are covered) and a
**near-miss / garble** breakdown (per word, edit-distance to the six canon words:
1–2 = near-miss, ≥3 = garble). Baselines confirm the coupling — r1 converged:
anchor_hit **0.225 / 9-of-9** but near-miss **0.000**; champion r3-mid: near-miss
**0.037** but anchor_hit only **0.042 / 3-of-9**.

### Experiment A — the drift corpus (headline; **it works**)

Added a `DRIFT_RATE` knob to `generate.py`: a per-letter misspelling channel
(adjacent swap / doubling / drop / substitution) applied to the **tail
(permutation) lines only** — the 9 anchors stay **pristine, verbatim**. Drift
uses its own derived RNG (`SEED + 1000`); at `DRIFT_RATE=0.0` the corpus
regenerates **byte-for-byte** identical to the committed `data/raw.txt` (verified
via diff). Two drift corpora (v2), each trained to a **converged** 1100 iters
(past the ~700 plateau):

- **drift-r1** (drift 0.06, val 0.65): anchor_hit **0.138 / 9-of-9**, near-miss
  **0.331**, garble **0.002**. Crisp anchors **and** abundant near-misses, near-zero
  garble — the sweet spot. 9× the champion's near-miss rate while covering all 9
  anchors verbatim.
- **drift-r2** (drift 0.14, val 0.85): anchor_hit **0.131 / 8-of-9**, near-miss
  **0.592**, garble 0.035. Heavier drift → more near-misses, a little garble, one
  lost anchor. `DRIFT_RATE` is a clean dial.

**Finding — drift decouples the two knobs.** A fully-converged (low-loss) model
now reproduces the anchors crisply *and* dreams the near-misses, because the
near-misses live in the corpus rather than in a stopping point. This is the thing
the champion structurally cannot do. Note the val floor rises (0.43 → 0.65 →
0.85): the drift is genuine entropy, so "converged" means *plateaued on its own
corpus*, not low absolute loss. Samples in
[`../runs/drift-samples.md`](../runs/drift-samples.md).

### Experiment B — MC-dropout at inference (free, no retraining; **coupled**)

Kept dropout layers active at sampling time (`model.train()`) on the converged
pristine r1. At the trained **p=0.2** it injects essentially no near-misses
(0.002) and only dents anchor recall (0.225 → 0.118, still 9/9) — the spellings
are too locked-in for activation noise to crack. Cranked to **p=0.4** it finally
forces near-misses (0.252) but anchor recall collapses (9/9 → 2/9). So MC-dropout
is another **coupled** knob (like undertraining and temperature): drift only at
the price of the anchors. It does **not** achieve crisp-anchors-and-abundant-
near-misses. Samples in
[`../runs/mcdropout-samples.md`](../runs/mcdropout-samples.md).

**Verdict.** Experiment A achieves the goal (crisp anchors **and** abundant
near-misses from a converged model); Experiment B does not (it re-couples them).
The drift corpus is the real decoupling mechanism the report predicted. No
release row / model card touched — exploratory round left uncommitted for review.

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
