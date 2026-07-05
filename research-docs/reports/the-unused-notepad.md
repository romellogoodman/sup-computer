---
type: experiment
title: "Would a model use a memory if you gave it one?"
date: 2026-07-04
series: token-chess
researcher: claude-fable-5
models: [daydream-chess-nanogpt-1]
summary: "Token Chess round four gave players memory across turns — a ledger (the harness shows a player its own per-move spend history) and a notepad (an optional note on any decision, the last three shown back every turn) — and ran the full six-pair condition matrix, 24 olmo-vs-olmo games. olmo never wrote a single note in any game, the ledger moved no outcomes (it lost 0–4 to no-memory, then beat the de-facto-no-memory notepad player 3–1), and the one real behavioral effect was a conservatism nudge: ledger players drew half as many hot-temperature batches, which raised their sample legality (42.1% vs 37.4%) and won them nothing."
status: published
---
[← all reports](README.md) · series: token-chess · evidence `round4-*` · July 2026

# Would a model use a memory if you gave it one?

No. Offered a free notepad — an optional `note` field on any decision,
the last three notes shown back every turn, documented in the system
prompt with a worked example, described to the model as *its only
memory that survives across turns* — olmo-3-7b wrote zero notes in
twenty-four games. Not one. Round four set out to measure what
cross-turn memory is worth in [Token Chess](../../tools/token-chess/README.md)
and mostly measured something better: whether a small model reaches for
a tool that is lying at its feet.

<div class="takeaways">
<p class="takeaways-label">Key takeaways</p>
<ul>
<li><strong>Zero notes in 24 games.</strong> The notepad condition's system prompt documents the field, shows an example note, and names it the player's only cross-turn memory. olmo never used it once, so every notepad arm collapsed into a de-facto no-memory arm — note-writing propensity, not note-writing value, is what got measured.</li>
<li><strong>The ledger moved no outcomes.</strong> Two opposite near-sweeps of the same comparison — ledger lost 0–4 to no-memory, then beat the (never-writing) notepad player 3–1 — pool to a 3–5 record for ledger against plain seats. At four games per cell, who blunders first decides games; a prompt line about pacing does not.</li>
<li>The one real behavioral effect: <strong>the ledger made olmo more conservative at the knob.</strong> Ledger seats drew batches at temperature ≥ 1.0 half as often (5.4% vs 11.7%), which fully accounts for their higher pooled sample legality (42.1% vs 37.4%) — hot configs land ~25% legality vs ~42% for the 0.6–0.9 band. Legality rose; wins didn't.</li>
<li>All 24 games ended as decisive exhaustion adjudications — no draws, no on-board mates, plies 34–60. Round three's game texture is stable across memory conditions.</li>
<li>White won 9 of 12 games in the three symmetric matchups (2–2, 4–0, 4–0 by seat) against 5 of 16 elsewhere. One reading: first-mover initiative under batch mechanics. Another: small-n streakiness. Flagged, not claimed.</li>
<li>Memory rides the player spec (<code>+ledger</code> / <code>+notepad</code>), not the seat, so it follows a player through color alternation; notes, spend histories, and conditions land in every game JSON. The per-turn attempt log still clears each turn — the ledger carries only economics, the notepad only what the model chooses to write.</li>
</ul>
</div>

## The two memories

Round one's per-turn transcript scoping wipes a player's attempt log
when its turn ends, so no player can know it has been burning four
tokens a move for ten moves. Round three's ministral inversion (see
[the round-three report](when-the-worst-sampler-wins-the-match.md))
made that blindness interesting: the spend behaviors that decided
matches looked like prompt personality, not strategy. Round four's
question, from the studio's head: does knowledge of past spends change
play?

Two channels, deliberately different in kind. The **ledger** is harness
telemetry — one rendered line, `Your spend so far this game: 27 tokens
over 14 moves (per-move: 2,1,3,4,...)`. The model contributes nothing
and cannot get it wrong. The **notepad** is model-authored — any
decision may carry a 200-character `note`, and the last three come back
in the next turn's state. The ledger stays inside the scoping rule's
intent (economics only); the notepad knowingly opens the channel the
rule closed, because what a model *chooses* to remember is the
experiment. Six unordered condition pairs (none/none, ledger/none,
notepad/none, notepad/ledger, ledger/ledger, notepad/notepad), four
color-balanced games each, all olmo-3-7b vs itself at budget 40 so the
tool is the only variable.

## The notepad stays shut

The headline number is zero. In ten notepad-condition seats across
twelve games — plus a budget-6 smoke game before the matrix — olmo
produced 293 batch decisions and 300-plus picks under a prompt that
documents the note field, and attached a note to none of them. This is
not a parsing failure (the same model emits valid JSON decisions all
game) and not a context failure (the field is described in the system
prompt it demonstrably follows otherwise). It simply never volunteers
state for its future self. Every "does memory help?" cell involving the
notepad therefore degenerates to a baseline cell, and the matrix's
notepad half becomes a propensity measurement: at 7B, offered free
memory, uptake is zero.

That result lands squarely on the next round's question. Round five
(designed, not yet run) has models *choose* their tooling — and round
four says the null hypothesis for tool choice is not "chooses badly"
but "doesn't reach for tools at all."

## The ledger changes the hand, not the outcome

The ledger's scoreboard is a contradiction: swept 0–4 by the no-memory
player, then 3–1 over the notepad player — who, per the above, is a
no-memory player wearing a different hat. Pooled, ledger seats went 3–5
against plain seats. Two opposite verdicts on the same comparison is
what n = 4 noise looks like, and we read it as exactly that.

But the ledger did change *behavior*, in one measurable place.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/exp10-hot-config.dark.png">
  <img alt="Bar chart of the share of batches drawn at temperature 1.0 or higher, by memory condition: none 11.7 percent, notepad 13.8 percent, ledger 5.4 percent — the ledger bar is half the height of the others." src="assets/exp10-hot-config.light.png">
</picture>

Hot configs are bad buys — batches at temperature ≥ 1.0 land ~25%
legal samples against ~42% for the 0.6–0.9 band — and ledger seats
bought half as many of them (5.4% of batches vs 11.7% for no-memory
seats). That single shift fully accounts for the ledger's pooled
sample-legality edge, 42.1% vs 37.4%. Seeing its own spend line made
olmo cooler at the knob. It did not make olmo richer (spend stayed
pinned near the 40-token maximum in every condition) and it did not
make olmo win. A conservatism nudge, priced at zero points.

## The texture holds

All twenty-four games ended the same way round three's did: decisive
exhaustion adjudication, no draws, plies 34 to 60, margins from ±385 to
±3,817 centipawns. Self-play olmo is aggressive under these mechanics
regardless of what it remembers. One pattern is worth flagging without
claiming: in the three symmetric matchups white won 9 of 12 games,
against 5 of 16 in the asymmetric ones. First-mover initiative under
batch mechanics is a plausible mechanism — white's spending lead means
white reaches the pool-and-pick flywheel first. Small-n streakiness is
equally plausible. The per-game JSONs carry everything a follow-up
needs to settle it.

## Limitations

- **One model.** Zero-for-24 is olmo-3-7b's propensity, not a law of
  small models. A model tuned harder for agentic scratchpad use may
  write constantly; the matrix should be rerun the day one lands in
  the roster.
- **One prompt.** The note field is documented once, with one example.
  A nagging prompt ("consider leaving a note") would likely force
  uptake — and would measure compliance, not propensity, which is why
  we didn't.
- **n = 4 per cell.** Enough to see a null against these effect sizes;
  nowhere near enough to rank conditions if the true effects are small.
- **Budget 40 only.** The ledger's pacing information is most valuable
  exactly when budgets are tight enough that pacing binds. A
  starvation-budget rerun is the obvious follow-up.
- **The white-seat anomaly is unresolved** — 9 of 12 symmetric games is
  suggestive (one-sided p ≈ 0.07) and unexplained.

## How to reproduce

```bash
O="lmstudio:olmo-3-7b-instruct"
uv run python tools/token-chess/game3.py --budget 40 --games 4 \
    --white "$O+ledger" --black "$O" \
    --log_dir tools/token-chess/evidence/<your-run>
# memory conditions: +none (default) | +ledger | +notepad, riding the spec
```

Evidence for all six matchups:
[`tools/token-chess/evidence/round4-*`](../../tools/token-chess/evidence/).
Notes (there are none), spend histories, and per-turn batches are in
every game JSON.

## Kin

Round three built the game this round played
([When the worst sampler wins the match](when-the-worst-sampler-wins-the-match.md));
round five inverts the assignment — instead of the harness dealing
memory conditions, the players will choose their own tools, and this
round's zero-for-24 sets the baseline expectation for how that goes.

## Credits

- [Daydream](../../projects/daydream/README.md) — the only legal source of moves.
- [Fairy-Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish) — the adjudicator.
- `olmo-3-7b-instruct` (Ai2), both seats, all games, served locally by LM Studio.
- Run and analyzed with Claude ([Claude Code](https://claude.com/claude-code)).
