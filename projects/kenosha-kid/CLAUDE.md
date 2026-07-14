# CLAUDE.md — rules for agents working in kenosha-kid

Facts live in [`README.md`](README.md) — the project, pipeline, version index
(§ Versions), and scoreboard (§ Leaderboard); lineage in
[`docs/sources.md`](docs/sources.md). This file is only the rules (ADR-0030).

## Don't relitigate

- **Orbit, don't enumerate.** The blur is the artifact: sampled warm, the model
  returns to the six words and lands slightly differently each time. Verbatim
  convergence is the *failure mode*, not the goal.
- **Char-level, on the shared `core`.** The near-miss drift lives *below* the
  BPE token boundary — chars, not BPE. `meta.pkl` is the tokenizer contract
  (ADR-0012). **Do not fork or vendor an engine.**
- **The corpus is synthetic and in-repo — don't scrape the bot.** `generate.py`
  owns the generator, deterministic by `SEED`; the anchor weighting (Pynchon's
  nine construals over the brute-force tail) is the point. **Do not flatten
  the corpus.**

## Conventions

- `generate.py` is the corpus knobs (deterministic; `data/raw.txt` IS
  committed); `config.py` is the model knobs — capacity and `max_iters` are
  *aesthetic* controls here, not just performance.
- **Sample warm.** The dream lives at temperature; cold sampling collapses
  toward the anchors.
- **Document as you go**: `research/log.md` (why) and the README's Leaderboard
  section (per-run scoreboard), committed with the run.
- **Releases** are frozen snapshots under `models/`, per
  [`docs/handbook.md`](../../docs/handbook.md#releasing-a-version).
- **Credit the researcher** — root [`CLAUDE.md`](../../CLAUDE.md), ADR-0013.
