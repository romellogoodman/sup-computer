# The rating sheets

Two sheets, 260 lines, about 45 minutes. Both are blind: a row shows a line
and nothing about the temperature, register or seed that produced it. The
`KEY-*.csv` files hold that. Don't open them until both sheets are filled.

Open a sheet in a spreadsheet or a text editor, fill the empty columns, save
it as CSV under the same name.

## `dial-sheet.csv` — 200 lines, two ratings each

| Column | What to enter |
|---|---|
| `strange` | 1–5. How far the line comes at things from the side. 1 is a platitude, 5 is a line nobody would have predicted. |
| `usable` | 1–5. Whether a stuck person could act on it or take something from it. 1 is noise, 5 is a line worth keeping on the desk. |

Rate each line alone, quickly, on both axes. A line that is strange and
useless gets a high `strange` and a low `usable`. A line rated 4 or more on
both is a keeper, and the keeper rate is what gets scored.

Some lines are broken, and some repeat. Rate them as they are.

## `register-sheet.csv` — 60 lines, one guess each

| Column | What to enter |
|---|---|
| `guess` | `s` if the line reads as a strategy (a sideways instruction to a stuck artist), `f` if it reads as a fortune. |

Every line needs a guess.

## Scoring

From the repo root, once both are filled:

```bash
uv run python projects/oblique/score_sheets.py
```

It reads the two sheets and their keys from this folder, prints the keeper
rate by temperature and the register agreement, and writes
`research/ratings-scored.json`. A blank or out-of-range cell stops it and
names the row.

A third sheet follows the first two: 60 lines from a second training seed,
at the three temperatures around wherever the first seed's keeper rate peaks.
It can't be drawn until this one is scored.
