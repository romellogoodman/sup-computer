# CLAUDE.md — rules for agents working in lucky

Facts live in [`README.md`](README.md) — the two games, the pipeline, the
version index (§ Versions), and the scoreboard (§ Leaderboard). This file is
only the rules (ADR-0030).

## Don't relitigate

- **This is a null experiment.** The expected result is nothing. Never tune a
  run to make a model beat its floor, and never report a number below the
  floor without first suspecting a leak.
- **The model picks numbers; the harness makes the ticket.** The harness owns
  shape (how many numbers, the separator, the end) and order (it sorts the
  whites). The model owns ranges and repeats. Never mask a number: masking
  turns the harness into a Quick Pick with the model adding noise.
- **Resample until valid, and keep the rejects.** The played ticket is the
  first valid attempt; attempt *n* uses seed + *n*. Rejects are printed and
  logged, never discarded.
- **Temperature 1 from a seed, never greedy.** No dial. Greedy prints the
  same ticket forever and can never recover from an invalid one.
- **k = 8, in three places.** The loader cuts "8 draws → next draw" at draw
  boundaries, the harness pastes exactly 8 draws, and `block_size` is
  `(k + 1) × tokens_per_draw`. All three read `common.py`.
- **Whites are reshuffled every epoch, and scored at set level.** The eval
  sums over the 120 orderings so the number compares to 28.12 bits. Never
  train on sorted whites.
- **Every history model has a no-history twin** trained on the same targets.
  The history version ships; the control stays in the project, scored and
  unreleased.
- **The split is by time.** Oldest 80% train, next 10% pick the stopping
  step, newest 10% are the test. Never shuffle draws across it.
- **The tape is frozen at the end of the corpus.** Nobody backfills draws.
- **Powerball is the current matrix only** (69/26, from 7 Oct 2015). No Power
  Play, no Double Play.

## Conventions

- Run everything from the **repo root** via `uv run`.
- **lucky has its own `train.py`**, because the shared loop cuts examples at
  random token offsets. It imports the model from `nanogpt_core` and writes
  the shared checkpoint shape. Don't port the draw-boundary loader into
  `core/` for one project.
- **Pre-check before training, predictions before runs.** A new game or era
  runs `precheck.py` first, and its predictions are committed in their own
  commit before the first run log.
- **Both sources, every draw.** `data/fetch.py` then `data/crosscheck.py`;
  every disagreement lands in `data/provenance.json`. Don't repair a draw by
  hand.
- **Tickets for real play are the owner's.** Don't generate or commit a
  batch of tickets for upcoming draws unless asked.
- **Document as you go**: `research/log.md` (why) and the README's
  Leaderboard, committed with the run.
- **Releases**: each game releases independently as a frozen snapshot under
  `models/`, per [`docs/handbook.md`](../../docs/handbook.md#releasing-a-version).
- **Credit the researcher** — root [`CLAUDE.md`](../../CLAUDE.md), ADR-0013.
  The corpus credits no generator: draw machines are described, not credited
  (ADR-0037).
