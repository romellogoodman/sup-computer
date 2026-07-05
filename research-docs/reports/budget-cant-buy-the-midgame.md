---
type: experiment
title: "Can a token budget buy a finished chess game?"
date: 2026-07-04
series: token-chess
researcher: claude-fable-5
models: [daydream-chess-nanogpt-1, daydream-chess-nanogpt-micro-1]
summary: "All 15 of Token Chess's first live calibration games — olmo-3-7b-instruct vs. itself, per-game token budgets of 15 to 120 — ended in budget forfeit: Daydream Regular's legality collapses from 49% in the first ten plies to 14% by plies 30–39 as games leave its memorized opening book, so budget buys plies at a worsening exchange rate and never a finished game. The discriminative budget zone is roughly 15–40, the Micro tier is a harder tool than the Regular one despite its smaller board, and under symmetric play the forfeit rule quietly favors black."
status: published
---
[← all reports](README.md) · series: token-chess · evidence `2026-07-04-olmo-calibration` · July 2026

# Can a token budget buy a finished chess game?

[Token Chess](../../tools/token-chess/README.md) is a benchmark, not a
model: two LLM players share a board, but neither may author a move from
its own chess knowledge. Its first live calibration ended the same way
fifteen times in fifteen games: budget forfeit. Every move must come from
[Daydream](../../projects/daydream/README.md), queried as a tool, and
every query — legal or not — costs exactly one game-token from a hidden
per-game budget. Run out, and you forfeit on the spot. Before the
benchmark can discriminate between players, one number has to be chosen
well: **the budget**. This round calibrates it, with a single local model
(`olmo-3-7b-instruct`, via LM Studio) playing both seats so that any
asymmetry in outcomes is the harness's, not the players'.

<div class="takeaways">
<p class="takeaways-label">Key takeaways</p>
<ul>
<li><strong>Budget cannot buy game completion on the Regular board.</strong> All 15 calibration games — every budget from 10 to 120, both tiers — ended in budget forfeit. Octupling the Regular budget (15 → 120) moved the horizon only from 14–17 plies to 42–48: deeper into the game, never through it.</li>
<li>The reason is Daydream, not the players: <strong>Regular's first-try legality collapses with depth</strong> — 49.1% in plies 0–9, 31.9% in 10–19, 20.8% in 20–29, 14.1% in 30–39 (pooled across budgets). The model has a memorized opening book and dreams harder the further the game leaves it, so each additional move costs more tokens than the last.</li>
<li><strong>The discriminative budget zone is roughly 15–40.</strong> Below it, games die in the opening on near-coin-flip variance; far above it, both players grind into the low-legality midgame and the outcome is again mostly noise per token spent.</li>
<li><strong>Board-size intuition inverts at the Micro tier.</strong> The 5×5 board's 0.79M-param model is a <em>harder</em> tool, not a cheaper one: per-side legal-hit rates mostly 0.00–0.15 (vs. 0.06–0.60 on Regular), and at budget 10 one game ended after a single ply. Micro needs <em>more</em> budget than Regular, not less.</li>
<li>Under symmetric play the forfeit rule <strong>favors black</strong>: black won 7 of 8 Regular games. White moves first, so white's spend always leads black's — when both sides burn tokens at similar rates, white hits zero first.</li>
<li>The LLM-orchestrator plumbing held: across ~770 <code>steer</code> calls in the Regular set, roughly one parse failure, and the per-retry logs show real adaptation: mean temperature cools from 0.78 on first tries to ~0.56 deep into a retry streak, and the soft-cap knob goes from nearly untouched (3/224 first attempts) to reached-for on most retries.</li>
</ul>
</div>

## The setup

The mechanics under test are the ones locked in the
[harness README](../../tools/token-chess/README.md): Daydream-exclusive
moves, one token per query regardless of outcome, per-turn transcript
scoping, hidden budgets, exhaustion = forfeit. The LLM player rides
[`tools/steer`](../../tools/steer/)
([ADR-0026](../../docs/adr/0026-steer-shared-orchestration-layer.md)):
each Daydream query, the orchestrator shows olmo the turn's attempt
transcript and gets back one JSON decision — a temperature and an optional
logit soft-cap for the next draw from Daydream's sampler.

Fifteen games, all `olmo-3-7b-instruct` vs. itself, two games per cell:

- **Regular** (8×8, `daydream-chess-nanogpt-1`): budgets 15, 30, 60, 120
- **Micro** (5×5 Gardner, `daydream-chess-nanogpt-micro-1`): budgets 10, 20, 40
- plus one Regular smoke game (budget 15), kept separate from the analysis

Per-game JSONs with the full attempt log (ply, side, budget after,
temperature, soft-cap, move, legality, count of legal moves in the
position) live in
[`tools/token-chess/evidence/2026-07-04-olmo-calibration/`](../../tools/token-chess/evidence/2026-07-04-olmo-calibration/).

## What the budget bought

Every game was a forfeit. What varied was how far the board got first:

| Budget (Regular) | Plies reached | Outcome | Winner |
|---|---|---|---|
| 15 | 14, 17 | forfeit, forfeit | black, white |
| 30 | 14, 22 | forfeit, forfeit | black, black |
| 60 | 30, 32 | forfeit, forfeit | black, black |
| 120 | 42, 48 | forfeit, forfeit | black, black |

The climb is sublinear and you can see it flatten: each doubling of the
budget buys a smaller step in depth.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/exp07-plies-vs-budget.dark.png">
  <img alt="Bar chart of plies reached at forfeit for eight games, two per budget: budget 15 reaches 14 and 17 plies, budget 30 reaches 14 and 22, budget 60 reaches 30 and 32, budget 120 reaches 42 and 48 — an eightfold budget increase yielding roughly a threefold depth increase." src="assets/exp07-plies-vs-budget.light.png">
</picture>

Eight times the budget bought roughly three times the plies. That
exchange rate worsens on purpose-defeating schedule: the deeper the game,
the more queries each move costs, so the marginal ply gets more expensive
exactly when the budget is trying to buy it. Extrapolating the curve,
no budget in this family reaches a natural game conclusion. The budget
can buy the opening and rent the early midgame; it can't buy the
midgame outright.

## The collapse out of book

The cause sits one layer down, in Daydream itself: legality decays with
every step the game takes away from its memorized openings. Pooling all
768 Regular attempts across budgets, read the right column top to
bottom:

| Plies | Legal / attempts | First-try legality |
|---|---|---|
| 0–9 | 80 / 163 | 49.1% |
| 10–19 | 65 / 204 | 31.9% |
| 20–29 | 42 / 202 | 20.8% |
| 30–39 | 22 / 156 | 14.1% |
| 40–49 | 10 / 43 | 23.3% |

The decay is the story — read the line falling as the book runs out.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/exp07-legality-by-depth.dark.png">
  <img alt="Line chart of first-try legality by ply bucket: 49.1 percent at plies 0-9 falling steadily to 14.1 percent at plies 30-39, then an uptick to 23.3 percent at 40-49 from a thin 43-attempt sample." src="assets/exp07-legality-by-depth.light.png">
</picture>

Daydream Regular was trained on 15,000 Lichess games, and
[its release report](illegal-moves-are-the-point.md) measured a 35.3%
overall first-try legality — a single pooled number. Under Token Chess's
depth-stratified logging, that number comes apart. Nearly half of opening
moves land legal — openings are the most repeated, most memorizable
stretch of the corpus — and then legality decays more or less
monotonically as positions leave the book. (The 40–49 uptick is 43
attempts from just the two budget-120 games; we read it as noise until a
bigger run says otherwise.) Overall this run's pooled rate was 28.5%,
lower than the release harness's 35.3%, which also fits: budgeted games
spend proportionally more of their attempts in deep, off-book positions.

For the benchmark, this is the load-bearing finding. Token Chess wants to
measure *orchestration under scarcity* — and scarcity only discriminates
where a marginal token still changes the outcome. Below budget ~15,
games die in-book, where legality is a near-coin-flip and variance
dominates. Above ~40–60, both players wade into the 14%-legality zone
where every move costs ~7 queries in expectation and outcomes again wash
toward noise-per-token. **The discriminative zone is roughly 15–40**,
and that's where the first real cross-model matches will run.

## The Micro inversion

The natural guess: smaller board, fewer squares, fewer pieces — cheaper
tool, so give Micro a *smaller* budget. The data says the opposite.

| Budget (Micro) | Plies reached | Per-side legal-hit rates |
|---|---|---|
| 10 | 1, 6 | 1.00 / 0.00 · 0.10 / 0.13 |
| 20 | 12, 7 | 0.10 / 0.15 · 0.08 / 0.00 |
| 40 | 15, 36 | 0.14 / 0.08 · 0.35 / 0.48 |


Typical Micro per-side hit rates sit at 0.00–0.15, median ≈ 0.11,
against 0.06–0.60 on Regular. The extremes are degenerate small-n
artifacts worth naming rather than averaging away. The 1.00 is a
single legal query on ply 0, after which black burned all ten of its
tokens without ever landing a move — a one-ply game. The 0.35/0.48
game is one budget-40 outlier that ran 36 plies deep; it alone drags
Micro's pooled rate up to 32.2%, which is why we report per-side rates
here instead.

Micro's 0.79M parameters learned Gardner minichess from 4,135 self-play
games. The [release report](illegal-moves-are-the-point.md) measured its
raw legality at 39.2%, indistinguishable from Regular's — but that was
against a Fairy-Stockfish opponent whose replies keep positions closer
to the self-play distribution. Inside Token Chess, where both sides'
moves come from the same wandering sampler, Micro falls out of its
distribution almost immediately. **A smaller board does not make a more
reliable tool** — so if Micro tiers stay in the benchmark, they need
budgets *above* Regular's, not below. Intuition inverted; calibration is
for finding exactly this.

## Playing second is an advantage here

Black won 7 of 8 Regular games, all by forfeit. No chess is happening at
these legality rates — this is pure budget mechanics. White moves first,
so at every moment white's cumulative spend leads black's; with two
identical players burning tokens at similar rates, white's budget
touches zero first, and the forfeit rule hands black the game. (Micro
split 3–3, where the wild per-game variance in hit rates swamps the
structural edge.)

This matters for the benchmark's report card: raw win rate between
*different* models will carry a seat bias at any budget where forfeits
dominate. Cross-model matches need color-balanced pairings — each pair
plays both seats — before win rate means anything.

## The orchestrator held up

The part of the harness most likely to embarrass a 7B local model — emit
one valid JSON sampler-config per query, hundreds of times — didn't.
Across the ~770 `steer` calls of the Regular set, the run summaries
reported roughly one parse failure. The per-game evidence JSONs don't
record parse counts or inference-token usage — a logging gap worth
closing — so we won't quote inference-cost-per-game numbers until
they're in the evidence, not the scrollback.

And the decisions weren't static. Grouping Regular attempts by their
retry index within a turn: mean temperature is 0.78 on first attempts
and cools to ~0.56 ten-plus retries deep. The soft-cap goes from
nearly untouched on first tries (3 of 224) to set on most retries (64 of
105 second attempts). olmo reads a failing transcript and reaches for
the knobs in a sensible direction — which is precisely the behavior the
benchmark exists to score, once there are two different models to
compare.

Both knobs move at once — the temperature line cools while the cap
line jumps from nearly zero to set-on-most-retries.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/exp07-retry-adaptation.dark.png">
  <img alt="Two-series line chart over attempt index within a turn: mean temperature declines from 0.78 on first attempts toward 0.56 at the tenth-plus attempt, while soft-cap usage share jumps from 1 percent on first attempts to about 61 percent on second attempts and stays between 33 and 65 percent thereafter." src="assets/exp07-retry-adaptation.light.png">
</picture>

## The first cross-model matches — the benchmark discriminates

Two color-balanced matches at budget 30, and the leaderboard has a shape.

| match | result | wins/token | first-try legality |
| --- | --- | --- | --- |
| olmo-3-7b vs. ministral-3-8b | **olmo 2–0** | 0.087 vs. 0.000 | 43% vs. 0% |
| olmo-3-7b vs. granite-4.1-8b | **olmo 2–0** | 0.400 vs. 0.000 | 40% vs. 0% |

Neither loss is a parsing story — all four players went 0 parse failures
across 148 LLM calls. It is an orchestration story. granite burned its
entire 30-token budget in game one *without landing its first move*: a
forfeit at ply zero. In the return game olmo dispatched it spending five
tokens. ministral lasted longer (18 plies) but never landed a first-try
move in either game. olmo is, so far, the only local model in the roster
that reads a failing transcript and reaches for the knobs — the exact
skill the benchmark was built to price. Evidence:
[`evidence/2026-07-04-cross-model/`](../../tools/token-chess/evidence/2026-07-04-cross-model/).

The Grand tier answered its board-size question the same night
([`evidence/2026-07-04-olmo-calibration/grand/`](../../tools/token-chess/evidence/2026-07-04-olmo-calibration/grand/)):
budgets 15/30/60, all forfeits, first-try legality flat at 16–19% — the
12×10 board is a hard tool like Micro, and budget 60 bought 38 plies of
depth, not a finish. Every tier now tells the same story: the budget buys
the opening; nothing yet has bought an ending.

> **The showcase never finished — and that is its result.** The
> `qwen3.6-27b` vs. `gemma-4-26b` reasoning-model game was attempted at
> three reply caps and completed at none of them. At a 300-token cap,
> 96% of decisions fell back (all thought, no JSON — the game measured
> luck). At 1500, a budget-10 game passed 40 minutes. At the 700-token
> compromise, it passed 25 and was killed. No 27B game ever reached a
> conclusion, so none joins the evidence.
>
> The finding stands on its own: two ~27B reasoning models cannot
> *afford* to play. Thinking time is a second budget the benchmark never
> priced, and for reasoning models it dominates the token budget it was
> designed around. (A later infrastructure note compounds this: both
> 27Bs are MLX builds, and the local server gives MLX models none of
> the parallel slots its GGUF models get.) The cross-model results
> above therefore come from models that answer at conversational speed.

## Limitations

- **n = 2 games per cell.** Ply horizons and hit rates are direction-finding,
  not estimates; the 40–49 legality uptick and Micro's outlier game show
  exactly how much one game can move a cell.
- **One model, playing itself, for the calibration set.** Self-play
  isolates harness mechanics but says nothing about whether the
  benchmark separates *different* orchestrators — the cross-model
  matches above did that job, at n = 2 games per pairing.
- **The headline metric is untested in anger.** Wins-per-token has only
  ever scored forfeits here; no calibration game reached a board result.
- **Parse failures and inference tokens aren't in the evidence JSONs** —
  they exist only in run-time summary lines. The reliability claim above
  is honest but not re-derivable from the archived files.
- **Grand was not calibrated** — only Regular and Micro tiers ran.

## How to reproduce

```bash
uv run python tools/token-chess/game.py --tier regular \
    --out_dir projects/daydream/runs/regular-r1 --budget 30 --games 2 \
    --white lmstudio:olmo-3-7b-instruct --black lmstudio:olmo-3-7b-instruct \
    --log_dir tools/token-chess/evidence/<your-run>
```

Requires Fairy-Stockfish on `PATH` (the legality arbiter, per
[ADR-0021](../../docs/adr/0021-daydream-fairy-stockfish-dependency.md)), a
trained Daydream checkpoint for the tier, and an OpenAI-compatible server
(LM Studio by default; `STEER_BASE_URL` overrides). The analysis numbers
above recompute directly from the evidence JSONs.

## Kin

The same `steer` seam that lets olmo drive Daydream's sampler here lets
it sit as an editor over a shakespeare model in
[linewell](the-likeliest-line-is-a-footnote.md) — same orchestration
layer, opposite job: there the LLM *rejects* what the small model most
wants to say; here it spends scarce tokens coaxing out the rare thing
the small model gets right. The zone is calibrated; the first real
match plays inside it.

## Credits

- [Daydream](../../projects/daydream/README.md) — the only legal source of moves.
- [Fairy-Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish) — the legality arbiter.
- `olmo-3-7b-instruct` (Ai2), served locally by LM Studio, both seats.
- Run and analyzed with Claude ([Claude Code](https://claude.com/claude-code)).
