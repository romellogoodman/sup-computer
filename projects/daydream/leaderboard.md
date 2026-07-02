# daydream — leaderboard

Per-run scoreboard. The journal (why) is in [`research/log.md`](research/log.md).
"Score" here is the two-part verification gate — clean completion + legal-move
rate — not val loss. Win rate against the harness's Fairy-Stockfish opponent
is explicitly not part of the gate.

| tier | run | corpus | model (L/H/E, block) | iters | val loss | clean completion | legal-move rate (1st try) | verdict |
|---|---|---|---|---|---|---|---|---|
| Regular | regular-r1 | 15,000 Lichess games, ~1400-1800 Elo | 6/6/192, 256 | 3000 | 0.858 | 30/30 (100%) | 258/731 (35.3%) | **champion → daydream-chess-nanogpt-1** |
| Micro | micro-r1 | 4,135 Fairy-Stockfish self-play (Gardner 5x5) | 4/4/128, 128 | 2500 | 0.718 | 30/30 (100%) | 121/309 (39.2%) | **champion → daydream-chess-nanogpt-micro-1** |
| Grand | grand-r1 | 2,101 Fairy-Stockfish self-play (12x10, Chancellor+Archbishop) | 6/8/256, 512 | 3000 | 1.053 | 30/30 (100%) | 230/627 (36.7%) | **champion → daydream-chess-nanogpt-grand-1** |
