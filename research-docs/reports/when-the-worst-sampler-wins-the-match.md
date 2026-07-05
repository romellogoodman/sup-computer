---
type: experiment
title: "When the worst sampler wins the match"
date: 2026-07-04
series: token-chess
researcher: claude-fable-5
models: [daydream-chess-nanogpt-1]
summary: "Token Chess round three rebuilt the game around the two levers earlier rounds proved real — a token buys a batch of 3 samples at the player's chosen config, picking among the legal ones is free, and budget exhaustion ends the game with engine adjudication instead of forfeit. Twelve live games later the benchmark finally discriminates in both directions: olmo-3-7b beats a chess-heuristic mock 3.5–0.5 on pick quality, then loses 3–1 to ministral — the model with the worst sampler skill on the board (20% legality vs olmo's 58%) — because the all-in spender controls when the game ends."
status: published
---
[← all reports](README.md) · series: token-chess · evidence `round3-*` · July 2026

# When the worst sampler wins the match

The model that could not land a single first-try legal move in
[round one](budget-cant-buy-the-midgame.md) just won its rematch 3–1 —
against the model that swept that round. Token Chess round three rebuilt
the game so that both proven skills get priced: sampler-config choice
(the [round-two probe's](if-nobody-can-die-can-anybody-win.md) follow-up
sweep showed the legality floor is config-dependent, roughly 8–30%) and
candidate *picking* (a mate>capture>check heuristic choosing best-of-3
won every decisive game in the gating probe). Twelve live games later
the benchmark discriminates in both directions at once — and the second
direction was a surprise.

<div class="takeaways">
<p class="takeaways-label">Key takeaways</p>
<ul>
<li><strong>The round-three mechanics work.</strong> A token buys a batch of 3 Daydream samples at the player's chosen config; picking a pooled legal candidate is free; exhaustion ends the game with Fairy-Stockfish adjudication (mate scores or |cp| ≥ 100 decide, else draw) instead of forfeit. Self-test: the pick-heuristic mock beat the random mock 3–1 with zero draws, including the project's first budgeted on-board checkmate (ply 37).</li>
<li><strong>An LLM's judgment clears the mechanical bar.</strong> olmo-3-7b beat the mate>capture>check mock 3.5–0.5 with sample legality and candidates-per-pick nearly tied — the separation was which candidates it played, plus economy (128 tokens to the mock's 160).</li>
<li><strong>ministral inverted round one, 3–1 over olmo, with the worst sampler skill on the board</strong>: 20% sample legality to olmo's 58%. It spent its entire 40-token budget every game, built material leads through volume, and exhausted while ahead — ending games at plies 22–25, before olmo's patience could matter.</li>
<li>The mechanism is tempo, not total spend. Pooled with round four's games (36 exhaustion endings), the exhausted side won exactly 17 and lost 17, and the bigger spender won 13 of 29 decided unequal-spend games — <strong>spending is a threshold, not a gradient</strong>. What the all-in spender actually buys is control of the clock: the game ends at its exhaustion, at a moment it chose.</li>
<li>olmo vs granite was the clean control: sample legality tied (42% vs 43%), spend tied, candidates-per-pick tied — and olmo won 3.5–0.5 on pick quality alone.</li>
<li>Every game decided or drawn on the board: 11 of 12 live games ended in adjudication, one dead-even draw, zero forfeits, zero parse-failure stories — and the game JSONs now carry LLM usage stats (round one's logging gap, closed).</li>
</ul>
</div>

## The redesign, in one turn

The round-one mechanics stand in `game.py`; round three is a second
locked format (`game3.py`, mechanics in the
[harness README](../../tools/token-chess/README.md)). A turn now works
like this: spend 1 token, choose `{temperature, soft_cap}`, and the
harness draws three Daydream samples at it. The legal ones join a
candidate pool. Play any pooled candidate for free, or spend another
token on another batch — economy against move quality, every turn. Run
out of tokens with an empty pool and the game ends: Fairy-Stockfish
evaluates the final position and the better side wins (within 100
centipawns is a draw). Per-turn transcript scoping, hidden budgets, and
Daydream-exclusivity are unchanged from round one.

The design pedigree matters: batching prices config skill (the floor
sweep showed configs differ 8–30% in deep-game legality), free picking
prices chess judgment (best-of-3 with a capture heuristic won every
decisive probe game), and adjudication lets the board — not the token
clock — have the last word. Each lever had probe evidence before the
harness was built.

## olmo clears the bar

`mock:heuristic` is the qualifying bar: the best-known config plus the
mate>capture>check pick rule. olmo beat it 3.5–0.5 (three wins, one
dead-even draw), and the texture says why: sample legality 40% vs 37%,
candidates per pick 1.64 vs 1.75 — the knob and the shopping were a
wash. The separation was economy (128 tokens to the mock's 160) and
*which* candidate got played. A 7B's chess judgment, applied to two or
three legal options at a time, beats a greedy capture rule. That is the
skill round three was built to price, and no earlier round could see it.

## The inversion

Then ministral — 0% first-try legality in round one, a model round one's
report called an orchestration failure — beat olmo 3–1.

The chart is the argument. Sample legality is the sampler-skill axis,
and the match winners are not who it says they should be.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/exp09-legality-vs-outcome.dark.png">
  <img alt="Bar chart of round-three sample legality for six players across three matches. olmo's bars are 40, 58, and 42 percent; its opponents are 37, 20, and 43. The 20 percent bar (ministral) and the 42 percent bar (olmo vs granite) are green, marking match winners — the tallest bar, olmo's 58 percent, lost its match." src="assets/exp09-legality-vs-outcome.light.png">
</picture>

ministral spent its entire 40-token budget in every game — 160 tokens
across the match to olmo's 57 — and at three samples per token, volume
made up for quality: 20% legality on 3-sample batches still fills a
candidate pool if you buy enough batches. Its games ended at plies 22,
23, 25, and 22, the shortest of the round. The games ended *because
ministral exhausted*, and it exhausted while ahead — adjudication then
read the material lead its spending spree had built. olmo, meanwhile,
banked tokens for a later that never came. One reading: ministral
discovered the round's first real strategy, all-in tempo. Another:
it plays the only way it can (it cannot tune the knob), and the
strategy found it. Either way the benchmark priced something real —
initiative — and priced it above sampler skill.

The pooled numbers say this is a threshold effect, not a spend
gradient. Across all 36 exhaustion-adjudicated games in rounds three
and four, the exhausted side won exactly 17 and lost 17; the bigger
spender won 13 of 29 decided unequal-spend games. Marginal tokens buy
nothing. What matters is not being the side that never engaged —
olmo's 11–17 tokens per game against ministral was engagement-starved,
and every mid-band spend difference after that washes out.

## The control match

olmo vs granite is the round's cleanest experiment because everything
else tied: legality 42% vs 43%, spend 144 vs 138, candidates per pick
1.58 vs 1.57. olmo won 3.5–0.5. With config skill, economy, and
shopping identical, the only lever left is which candidate gets played —
pick quality alone carried a sweep. Alongside the ministral result, the
round's summary is a rock-paper-scissors: judgment beats the heuristic
bar, tempo beats judgment, and nothing yet beats tempo.

## What the round leaves open

The exhaustion rule gives the aggressive spender control of *when*
adjudication happens, and that timing power is doing real work in the
inversion. Whether that is the benchmark honestly pricing initiative or
an exploitable flaw is round-three's standing design question. The
candidate fix, if it proves degenerate: let the solvent side keep
playing after the opponent exhausts, or adjudicate only when both banks
are dry. Round four's memory experiments (next report) left the
mechanics untouched, so the question is still live.

## Limitations

- **n = 4 games per match.** The 3–1 and 3.5–0.5 results are
  direction-finding; a single flipped game moves any of them a half
  point.
- **olmo sits in every match.** The roster is a star centered on one
  model, not a round-robin; ministral vs granite is unplayed.
- **One budget (40), one batch size (3).** Both were probe-calibrated,
  neither swept. The tempo strategy's strength is plausibly
  budget-dependent — at budget 80 the game may not end before the
  patient player's bank matters.
- **Adjudication favors material.** Fairy-Stockfish at depth 10 reads
  material-heavy positions confidently; a capture-volume strategy may
  be flattered by the judge that scores it.
- **Mate-in-N proof.** The self-test produced one on-board checkmate;
  the live games produced none. Decisive ≠ checkmate under these
  mechanics — nearly every verdict is the engine's.

## How to reproduce

```bash
uv run python tools/token-chess/game3.py --budget 40 --games 4 \
    --white lmstudio:olmo-3-7b-instruct --black mock:heuristic \
    --log_dir tools/token-chess/evidence/<your-run>
```

Requires a trained Daydream Regular checkpoint, python-chess,
Fairy-Stockfish on `PATH` (the adjudicator — `engine_client.Engine`
gained an `evaluate()` for it), and an OpenAI-compatible server for
`lmstudio:` specs. Evidence for every match:
[`tools/token-chess/evidence/round3-*`](../../tools/token-chess/evidence/).

## Kin

[Round one](budget-cant-buy-the-midgame.md) priced the knob under death
and got forfeits; [round two](if-nobody-can-die-can-anybody-win.md)
removed death and got nothing; round three prices the knob *and* the
pick under adjudication and got a leaderboard with an upset. The same
season's [linewell report](the-likeliest-line-is-a-footnote.md) found
the same shape in a different domain: the mechanical judge (likelihood,
there; legality, here) is not the skill that decides.

## Credits

- [Daydream](../../projects/daydream/README.md) — the only legal source of moves.
- [Fairy-Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish) — now both arbiter and adjudicator.
- `olmo-3-7b-instruct` (Ai2), `ministral-3-8b-instruct-2512` (Mistral), `granite-4.1-8b` (IBM), served locally by LM Studio.
- Run and analyzed with Claude ([Claude Code](https://claude.com/claude-code)).
