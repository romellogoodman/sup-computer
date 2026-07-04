---
type: experiment
title: "Can a token budget buy a finished chess game?"
date: 2026-07-04
series: token-chess
researcher: claude-fable-5
models: [daydream-chess-nanogpt-1, daydream-chess-nanogpt-micro-1]
summary: "First live calibration of the Token Chess benchmark: olmo-3-7b-instruct vs. itself, orchestrating Daydream's sampler under per-game token budgets of 15 to 120. Every one of 15 games ended in budget forfeit — because Daydream Regular's legality rate collapses from 49% in the first ten plies to 14% by plies 30–39 as games leave its memorized opening book, budget buys plies at a worsening exchange rate and never buys a finished game. The discriminative budget zone is roughly 15–40, the Micro tier is a harder tool than the Regular one despite its smaller board, and under symmetric play the forfeit rule quietly favors black."
status: draft
---
[← all reports](README.md) · series: token-chess · evidence `2026-07-04-olmo-calibration` · July 2026

# Can a token budget buy a finished chess game?

[Token Chess](../../tools/token-chess/README.md) is a benchmark, not a
model: two LLM players share a board, but neither may author a move from
its own chess knowledge. Every move must come from
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
<li>The LLM-orchestrator plumbing held: across ~770 <code>steer</code> calls in the Regular set, roughly one parse failure, and the per-retry logs show real adaptation — mean temperature cools from 0.78 on first tries to ~0.56 deep into a retry streak, and the soft-cap knob goes from nearly untouched (3/224 first attempts) to reached-for on most retries.</li>
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

<!-- dataviz: plies reached at forfeit vs. budget, regular tier (budgets 15/30/60/120, 2 games each), dot or bar per game — the point is the sublinear climb; data: tools/token-chess/evidence/2026-07-04-olmo-calibration/regular -->

Eight times the budget bought roughly three times the plies. That
exchange rate worsens on purpose-defeating schedule: the deeper the game,
the more queries each move costs, so the marginal ply gets more expensive
exactly when the budget is trying to buy it. Extrapolating the curve,
no budget in this family reaches a natural game conclusion — the budget
can buy the opening, and it can rent the early midgame, but it can't buy
the midgame outright.

## The collapse out of book

The cause sits one layer down, in Daydream itself. Pooling all 768
Regular attempts across budgets:

| Plies | Legal / attempts | First-try legality |
|---|---|---|
| 0–9 | 80 / 163 | 49.1% |
| 10–19 | 65 / 204 | 31.9% |
| 20–29 | 42 / 202 | 20.8% |
| 30–39 | 22 / 156 | 14.1% |
| 40–49 | 10 / 43 | 23.3% |

<!-- dataviz: first-try legality rate by ply bucket, regular tier, line or bar with attempt counts visible (the 40–49 bucket is n=43 from only the two budget-120 games — mark it as thin), data: tools/token-chess/evidence/2026-07-04-olmo-calibration/regular -->

Daydream Regular was trained on 15,000 Lichess games, and
[its release report](illegal-moves-are-the-point.md) measured a 35.3%
overall first-try legality — a single pooled number. Under Token Chess's
depth-stratified logging, that number comes apart: nearly half of opening
moves land legal, because openings are the most repeated — most
memorizable — stretch of the corpus, and then legality decays more or
less monotonically as positions leave the book. (The 40–49 uptick is 43
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

<!-- dataviz: per-side legal-hit rate, micro vs. regular tier, strip/dot plot per game-side — the point is micro's mass sits at 0.00–0.15 while regular's sits higher, with micro's outliers annotated (the 1.00 is 1-of-1; the 0.35/0.48 game is a single deep outlier), data: tools/token-chess/evidence/2026-07-04-olmo-calibration/{micro,regular} -->

Typical Micro per-side hit rates sit at **0.00–0.15** (median ≈ 0.11) —
against 0.06–0.60 on Regular. The extremes are degenerate small-n
artifacts worth naming rather than averaging away: the 1.00 is a
single legal query on ply 0 after which black burned all ten of its
tokens without ever landing a move (a one-ply game), and the 0.35/0.48
game is one budget-40 outlier that ran 36 plies deep — it alone drags
Micro's pooled rate up to 32.2%, which is why we report per-side rates
here instead.

Micro's 0.79M parameters learned Gardner minichess from 4,135 self-play
games — the [release report](illegal-moves-are-the-point.md) found its
raw legality (39.2%) indistinguishable from Regular's, but that was
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
reported roughly one parse failure (the per-game evidence JSONs don't
record parse counts or inference-token usage — a logging gap worth
closing; we won't quote inference-cost-per-game numbers until they're in
the evidence, not the scrollback).

And the decisions weren't static. Grouping Regular attempts by their
retry index within a turn: mean temperature is 0.78 on first attempts
and cools to ~0.56 ten-plus retries deep, while the soft-cap goes from
nearly untouched on first tries (3 of 224) to set on most retries (64 of
105 second attempts). olmo reads a failing transcript and reaches for
the knobs in a sensible direction — which is precisely the behavior the
benchmark exists to score, once there are two different models to
compare.

<!-- dataviz: mean temperature and soft-cap usage rate vs. retry index within a turn (0..9+), regular tier, paired line/bar — shows the orchestrator cooling and reaching for the cap under failure, data: tools/token-chess/evidence/2026-07-04-olmo-calibration/regular -->

## Pending: the first cross-model match

> **[PLACEHOLDER — results pending]**
> The first real match — `qwen3.6-27b` vs. `gemma-4-26b`, color-balanced,
> in the calibrated budget zone — had not finished at time of writing.
> This section will carry: win rate by seat, wins-per-token (the headline
> metric), legal-hit-rate per player, and whether the two models'
> retry-adaptation profiles (temperature/soft-cap trajectories) actually
> differ. Until then, everything above is calibration, not competition.

## Limitations

- **n = 2 games per cell.** Ply horizons and hit rates are direction-finding,
  not estimates; the 40–49 legality uptick and Micro's outlier game show
  exactly how much one game can move a cell.
- **One model, playing itself.** Self-play isolates harness mechanics but
  says nothing about whether the benchmark separates *different*
  orchestrators — that's the pending match's job.
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
the small model gets right.

## Credits

- [Daydream](../../projects/daydream/README.md) — the only legal source of moves.
- [Fairy-Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish) — the legality arbiter.
- `olmo-3-7b-instruct` (Ai2), served locally by LM Studio, both seats.
- Run and analyzed with Claude ([Claude Code](https://claude.com/claude-code)).
