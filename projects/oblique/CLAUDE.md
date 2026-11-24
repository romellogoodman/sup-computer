# CLAUDE.md — rules for agents working in oblique

Facts live in [`README.md`](README.md): the project, the pipeline, the corpus
record, the choices and the scoreboard. The predictions and kill criteria are
in [`research/predictions.md`](research/predictions.md). This file is only
the rules (ADR-0030).

## Don't relitigate

- **Say who sat in the seat.** The brief made the human rating the
  experiment. Round one was rated by a Claude Fable 5.2 session instead, at
  the owner's direction, and every table of ratings says so. Never present a
  model's ratings as a human's, never fill a blank rating, and never rate a
  sheet in the session that built it or has read its key.
- **The keys stay closed to a rater.** `research/sheets/KEY-*.csv` maps a
  sheet row to its temperature, register and seed. A new rater, human or
  model, gets a blanked copy of the sheet and nothing else.
- **No card goes into a prompt, the corpus or the tree.** The deck is Eno
  and Schmidt's. `data/fetch_deck.py` fetches the published list to a
  gitignored directory for the leakage check and that is its only use. The
  filter log records a match by hash, not by text.
- **The generators are named.** Four OpenRouter model ids in
  `data/generate.py`, chosen by the owner (ADR-0038). Don't add one, swap
  one or let a failed one fall through to another.
- **Every generated line goes through `tools/synthgen`** and then through
  `data/filter.py`. No hand-rolled client, no unfiltered line in the corpus.
- **Predictions are frozen.** `research/predictions.md` was committed before
  the first run. A new round registers new predictions in a new file.
- **One recipe.** 4 layers, 4 heads, 128 embedding, block 128, char-level.
  The research variable is training length and the sampler, not the
  architecture.

## Conventions

- Run everything from the **repo root** via `uv run`.
- Paid generation takes `--budget` every run and reads the key from the
  environment or the repo-root `.env.local`. Read the cost from the manifest
  before starting a larger run.
- `data/raw.txt`, `data/manifest.json`, `data/costs.jsonl`,
  `data/corpus.txt` and `data/filter-log.json` are committed evidence.
  `data/ledger.jsonl`, `data/deck/`, `data/oblique/` and `runs/` are not.
- Training follows the `babysit-training` skill. `sweep.py` is the only way
  to train here: it keeps the checkpoint at every eval.
- **Document as you go**: `research/log.md` (why) and README § Leaderboard
  (numbers), committed with the run.
- **Credit the researcher** and **credit the generators**: root
  [`CLAUDE.md`](../../CLAUDE.md), ADR-0013 and ADR-0037.
