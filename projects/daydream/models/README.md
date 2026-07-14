# daydream — frozen releases

Each folder is a self-contained, runnable snapshot pinned to a git tag
(ADR-0003): its own engine copy, data pipeline, and config. Never refactored
to share `core/` or each other. Tiers release independently; Regular is the
unsuffixed name.

| Version | Tag | Tier / board | Notes |
|---|---|---|---|
| [`daydream-chess-nanogpt-1`](daydream-chess-nanogpt-1/) | `daydream-chess-nanogpt-1` | Regular, 8×8 | Lichess ~1400–1800 Elo corpus |
| [`daydream-chess-nanogpt-micro-1`](daydream-chess-nanogpt-micro-1/) | `daydream-chess-nanogpt-micro-1` | Micro, 5×5 Gardner | Fairy-Stockfish self-play corpus |
| [`daydream-chess-nanogpt-grand-1`](daydream-chess-nanogpt-grand-1/) | `daydream-chess-nanogpt-grand-1` | Grand, 12×10 | Fairy-Stockfish self-play corpus |
