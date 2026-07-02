# kenosha-kid — leaderboard

Per-run scoreboard. The journal (why) is in [`log.md`](research/log.md). For this project
the "score" is not just val loss — it's the **dream/verbatim balance**: a good run
keeps the six words recognizable while drifting (punctuation, near-misses) when
sampled warm. Verbatim-perfect convergence is a *loss*, not a win.

| run | corpus | model (L/H/E, block) | iters | best val loss | warm-sample read | verdict |
|---|---|---|---|---|---|---|
| r1 | v1 (24k lines, anchors 18%) | 4 / 4 / 128, 128 | 2000 | 0.4325 | crisp words; drift only in order/punctuation. The **lucid** dream. | too clean — no near-misses |
| r2-early | v1 | 4 / 4 / 128, 128 | 150 | 0.59 | char-level near-misses ("Kenoshau", "nevu"); anchors too broken | too dreamy — phrase dissolves |
| **r3-mid** | v1 | 4 / 4 / 128, 128 | 350 | 0.48 | anchors surface + occasional near-miss; best at **temp 0.9** | **champion → kenosha-kid-nanogpt-1** |
| **drift-r1** | v2 (drift 0.06; anchors pristine) | 4 / 4 / 128, 128 | 1100 (converged) | 0.65 | 9/9 anchors verbatim **and** near-miss on ~33% of lines; best at **temp 0.9** | **released → kenosha-kid-nanogpt-2** |

L/H/E = n_layer / n_head / n_embd. "Score" here is the dream/verbatim balance, not
val loss — r1 has the lowest loss and is the *worst* artifact, and v2 (drift-r1)
has a *higher* loss than the v1 champion yet is a better artifact (the injected
drift is genuine entropy — see the drift round below and the model card).

## 2026-07-02 round — drift corpus + MC-dropout (drift-r1 released as v2)

Automated dream-score via `eval_dream.py` (~430 lines/run, T=0.9): **anchor_hit**
= fraction of lines verbatim = 1 of 9 anchors, **9** = anchors covered/9,
**near-miss** = fraction of lines with a 1–2 edit-distance drift word, **garble** =
lines with a ≥3-distance word. corpus v2 = drifted tail (`DRIFT_RATE`), anchors
pristine. Goal: crisp anchors **AND** abundant near-misses from a *converged* model.

| run | corpus | iters | val | anchor_hit | 9 | near-miss | garble | verdict |
|---|---|---|---|---|---|---|---|---|
| r1 (baseline) | v1 | 2000 | 0.43 | 0.225 | 9/9 | 0.000 | 0.000 | crisp anchors, no near-misses |
| r3-mid (baseline) | v1 | 350 | 0.48 | 0.042 | 3/9 | 0.037 | 0.012 | couples both via undertraining |
| **drift-r1** | v2, drift 0.06 | 1100 | 0.65 | 0.138 | **9/9** | **0.331** | 0.002 | **crisp anchors + abundant near-misses (win)** |
| drift-r2 | v2, drift 0.14 | 1100 | 0.85 | 0.131 | 8/9 | 0.592 | 0.035 | heavier drift; more near-miss, some garble |
| r1 + MC-dropout p=0.2 | v1 | 2000 | 0.43 | 0.118 | 9/9 | 0.002 | 0.000 | dropout too weak to drift spellings |
| r1 + MC-dropout p=0.4 | v1 | 2000 | 0.43 | 0.009 | 2/9 | 0.252 | 0.051 | near-misses only by wrecking anchors (coupled) |

**Drift decouples; MC-dropout does not.** drift-r1 is the only converged model
with crisp anchors *and* abundant near-misses. Samples:
[`runs/drift-samples.md`](runs/drift-samples.md),
[`runs/mcdropout-samples.md`](runs/mcdropout-samples.md). **drift-r1 is released
as `kenosha-kid-nanogpt-2`** (see [`MODELS.md`](MODELS.md) and
[`models/kenosha-kid-nanogpt-2/`](models/kenosha-kid-nanogpt-2/)).
