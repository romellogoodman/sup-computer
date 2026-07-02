# kenosha-kid — leaderboard

Per-run scoreboard. The journal (why) is in [`log.md`](log.md). For this project
the "score" is not just val loss — it's the **dream/verbatim balance**: a good run
keeps the six words recognizable while drifting (punctuation, near-misses) when
sampled warm. Verbatim-perfect convergence is a *loss*, not a win.

| run | corpus | model (L/H/E, block) | iters | best val loss | warm-sample read | verdict |
|---|---|---|---|---|---|---|
| r1 | v1 (24k lines, anchors 18%) | 4 / 4 / 128, 128 | 2000 | 0.4325 | crisp words; drift only in order/punctuation. The **lucid** dream. | too clean — no near-misses |
| r2-early | v1 | 4 / 4 / 128, 128 | 150 | 0.59 | char-level near-misses ("Kenoshau", "nevu"); anchors too broken | too dreamy — phrase dissolves |
| **r3-mid** | v1 | 4 / 4 / 128, 128 | 350 | 0.48 | anchors surface + occasional near-miss; best at **temp 0.9** | **champion → kenosha-kid-nanogpt-1** |

L/H/E = n_layer / n_head / n_embd. "Score" here is the dream/verbatim balance, not
val loss — r1 has the lowest loss and is the *worst* artifact.
