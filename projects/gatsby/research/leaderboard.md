# Leaderboard

The quantitative scoreboard for gatsby-nanogpt. Each row is a training run.
Prose write-ups and rationale live in [`log.md`](log.md).

Two costs are tracked per run, mirroring the `shakespeare-nanogpt` convention:

- **Generation $** — real money paid to the Claude API to produce that run's
  training corpus (`data/costs.jsonl`, via `python costs.py`). This is the data
  cost, and the dominant real-dollar cost of the project.
- **Train tokens** — tokens the nanoGPT processed = `batch_size × block_size ×
  grad_accum × iters`. The training-compute cost (free on the local M-series GPU,
  but recorded). Plus wall-clock train time.

Quality on this project isn't a single number (there's no held-out BPC target
the way Shakespeare had); what matters is **does the green light reliably barge
in, and does the `green=N` dial visibly change the output across arbitrary
topics.** We record `val loss` as a convergence sanity check and judge fixation
behaviour qualitatively (sample notes per run).

## Runs

| Run | Corpus (stories / chars) | Gen $ | Params | Train tokens | Train time | Val loss | Fixation / dial behaviour |
|-----|--------------------------|-------|--------|--------------|-----------|----------|---------------------------|
| `smoke-test` | 20 / 21.9k | $0.11 | 10.65M | 16.4M (500 it) | ~7 min (MPS) | 1.96 (toy) | Wiring ✅. Green light barges in at both extremes. Dial differentiation weak (4 stories/level); corpus dial proven monotonic (2.0→11.5 mentions, L1→L5). |
| `1k-v1` | 995 / 1.11M | $2.92 | 10.65M | best @1250 it (54.6M tok) | ~40 min (MPS) | **0.639** (min @1250; rose after) | **Obsession ✅** — green light barges into ~every story on arbitrary topics, coherent (~3 mentions even at L1). **Dial ⚠️ weak** — monotonic but compressed (avg green: 2.83→3.00→3.17→3.17→3.67, L1→L5); adjacent levels often byte-identical under a fixed seed. Model under-weights the `green=N` digit. Topic also largely ignored (collapses to "Mia + green light"). Overfit past step 1250. |
| `1k-v2` | 1000 / 1.12M | $3.23¹ | 10.65M | best @1500 it (65.5M tok) | ~50 min (MPS) | **0.521** (min @1500; NOT comparable to v1 — different corpus/val split) | **Corpus fixed** (200 topics ×5 levels, names diverse 1681→135, corpus dial 2.27→12.57). **Model barely moved:** obsession ✅ (~3–4 green/480 tok; on-topic openings delay it); topic honoring ⚠️ marginal+unreliable (beetle/bake yes, robot→rabbit); **dial ❌** still flat/inverted (4.17,4.08,3.17,3.17,3.17 @480 tok; L3-5 byte-identical). Coherence slightly worse than v1. Root cause = char-LM conditions weakly on a short prefix, not corpus shape. |

| `1k-v3` | 1000 / 1.15M | $0² | 10.65M | best @1500 it (65.5M tok) | ~50 min (MPS) | **0.502** (min @1500; not comparable across corpora) | **Dial fixed ✅** — louder control line (tag ×3 + per-level word), same stories as v2 reformatted for $0. Model dial @480 tok now **monotonic 1.50→1.92→1.92→3.08→3.50** (was flat 4.17→3.17), and levels generate *different* text (faint=light once at end → total=swallowed "Green light. Green light."). Obsession ✅. Topic honoring ⚠️ still unreliable (robot→rabbit, clock→cloud); coherence still rough. Confirms v2 diagnosis: bottleneck was signal loudness, not corpus shape. |
| `mix-1k-r1` | 1000 / 763k | **$0³** | 10.65M | best @1250 it | ~40 min (MPS) | 0.627 (min @1250) | **Generator swapped to a local 4-model mixture** (granite .40 / gemma .30 / olmo .15 / ministral .15, via LM Studio). **Dial broke flat** (@240 tok: 1.7,1.7,1.8,2.0,1.4 — L5 lowest). Diagnosis: corpus dial fine (monotonic 2.3→8.2) but **granite's per-model dial is flat** (1.4→3.7) and it's 40% of the corpus; plus corpus 34% smaller → overfits @1250 before conditioning is learned. Obsession ✅, coherence/topic ❌. |
| `mix-2k-r2` → **`gatsby-nanogpt-2`** | 2000 / 1.53M | **$0³** | 10.65M | best @2000 it | ~30 min (MPS) | **0.622** (min @2000) | **Rebalanced off granite** (olmo .30 / ministral .30 / gemma .20 / granite .20) **+ scaled to 2k**. Trained 60% deeper before overfitting (2000 vs 1250). **Dial recovered** @480 tok: **3.7,4.8,4.7,4.5,6.1** — endpoints separate, middle compressed. Obsession ✅. Coherence/topic-honoring still baseline-rough. **Matches the paid baseline's behaviour at $0.** → [Exp 04](../../../research-docs/reports/experiment-04.md) |

¹ `1k-v2` gen cost = $0.29 (100-story validation chunk) + $2.94 (full 1000-story batch).
² `1k-v3` reuses the v2 stories reformatted in place (`reformat_corpus.py`) — no new API spend. Project gen total unchanged at ~$6.27.
³ `mix-*` runs are written by a **local mixture of open models** (LM Studio), not the Claude API — $0 marginal cost; the cost is generator wall-clock (~100 min for 2k stories).

## Notes per run

_(run write-ups land here as we go)_
