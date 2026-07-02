# CLAUDE.md — conventions for agents working in kenosha-kid

`kenosha-kid` is a char-level GPT whose **entire corpus is punctuated permutations
of six words**: *you never did the kenosha kid* — the phrase Tyrone Slothrop
fixates on under sodium amytal in Pynchon's *Gravity's Rainbow* (I.10), and the
seed of Darius Kazemi's [@YouNeverDidThe](https://x.com/youneverdidthe) bot. Start
with [`README.md`](README.md); the lineage is in [`docs/sources.md`](docs/sources.md).

## The core idea (don't relitigate these)

- **Orbit, don't enumerate.** The bot is `itertools.permutations` — flat, exact,
  dead. A learned model can't be the bot (a net approximates a distribution; the
  approximation is always a little blurry). **The blur is the artifact**: sampled
  warm, the model returns to the six words and lands slightly differently each
  time (drifted punctuation, near-misses like "nevver"). Verbatim convergence is
  the *failure mode*, not the goal.
- **Char-level, on the shared `core`.** Punctuation and capitalization carry the
  whole signal, and the near-miss drift lives *below* the BPE token boundary — so
  chars, not BPE. We ride `core` directly (no vendored engine): `core` honors
  `meta.pkl` as the tokenizer contract — see
  [ADR-0012](../../docs/adr/0012-pluggable-tokenization.md). **Do not fork or
  vendor an engine.**
- **The corpus is synthetic and in-repo — don't scrape the bot.** The bot is a
  deterministic function, so `generate.py` reproduces it from code we own. That
  keeps the corpus frozen and inspectable, and — the real reason — lets us
  **weight** it: Pynchon's nine construals are high-frequency anchors over the
  brute-force tail, giving the model a preference manifold (crisp anchors, dim
  tail) instead of a flat enumeration. **Do not flatten the corpus.**

## Pipeline & conventions

- `generate.py` → `data/raw.txt` → `prepare.py` → `data/kenosha/{train,val}.bin`
  + `meta.pkl` → `core/nanogpt_core/train.py` → `runs/<r>/ckpt.pt` →
  `core/nanogpt_core/sample.py`. Run everything from the **repo root** via `uv run`.
- **`generate.py` is the knobs for the corpus**: `WORDS`, `ANCHORS` (Pynchon's
  construals), `ANCHOR_FRACTION`, `N_LINES`, the separator/terminal weights. It is
  **deterministic** (`SEED`) — `data/raw.txt` regenerates byte-for-byte and **IS
  committed**. Only derived artifacts are gitignored (`*.bin`, `*.pkl`, `*.pt`).
- **`config.py` is the model knobs**; capacity (`n_layer`/`n_embd`) and
  `max_iters` are *aesthetic* controls here, not just performance — smaller/shorter
  blurs more. Mac: `device='mps'`, `compile=False`.
- **Sample warm.** The dream lives at temperature. Cold sampling collapses toward
  the anchors (the memorization study, a different project). The interesting knob
  is `--temperature` (and top-k / soft-capping when we add it).
- **Document as you go.** Update [`research/log.md`](research/log.md) (the journal)
  and [`leaderboard.md`](leaderboard.md) (per-run scoreboard)
  when you run experiments, and commit.
- **Credit the researcher.** A report for this project sets `researcher: <id>` in
  frontmatter and its `registry.json` model entry sets `"researcher": "<id>"` — the
  model that *did the research*, keyed into the `researchers` map. See the root
  [`CLAUDE.md`](../../CLAUDE.md) and `docs/adr/0013-attribution-of-the-ai-researcher.md`.

## Releases

`kenosha-kid-nanogpt-1` has shipped: a frozen, self-contained snapshot under
[`models/`](models/README.md), pinned to the `kenosha-kid-nanogpt-1` git tag,
with a [`MODELS.md`](MODELS.md) entry, a `registry.json` entry, and a model
card in `research-docs/model-cards/`. A new release means a **new** frozen
`models/kenosha-kid-nanogpt-N/` folder plus all four records — see
[`docs/releasing.md`](../../docs/releasing.md).
