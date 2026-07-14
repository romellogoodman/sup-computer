# CLAUDE.md — rules for agents working in gatsby

Facts live in [`README.md`](README.md) — the project, pipeline, quick start,
version index (§ Versions), and scoreboard (§ Leaderboard). This file is only
the rules (ADR-0030).

## Don't relitigate

- **The obsession is baked into training, not steered at inference.** Logit
  steering on a ~10M model is too fragile for a live exhibit; the model is
  trained to have no un-obsessed mode. Do not add inference-time steering as
  the primary mechanism.
- ***The Great Gatsby* is a style seed, never training data** — raw Gatsby
  would only be memorized as collage, never absorbed as a metaphor.
- **The control line has one source of truth: `generate.py:build_prime`.**
  Writers emit it into the corpus; `sample.py` / `eval_dial.py` /
  `generate_samples.py` import it — never respell the string anywhere.
  Changing it means a new corpus and a retrain.
- **The engine is the shared `core/`** (ADR-0023) — do not vendor or fork one.
- **The experience is the artifact.** Everything serves an operator typing a
  topic and watching the green light barge in.

## Conventions

- Corpus generation: `claude-sonnet-4-6` (cost; `claude-opus-4-8` is the
  fallback if the fixation isn't landing); `ANTHROPIC_API_KEY` from the
  gitignored `.env`; use the Batch API (`--batch`) for large runs. Topics are
  generated, never a fixed bank.
- **Track cost and commit the data**: generation runs log to
  `data/costs.jsonl`; `data/raw.txt` IS committed; weights and derived
  `.bin`/`.pkl` are not.
- **Document as you go**: `research/log.md` (why) and the README's Leaderboard
  section (per-run scoreboard), committed with the run.
- **Releases** are frozen snapshots under `models/`, per
  [`docs/handbook.md`](../../docs/handbook.md#releasing-a-version).
- **Credit the researcher** — root [`CLAUDE.md`](../../CLAUDE.md), ADR-0013.
