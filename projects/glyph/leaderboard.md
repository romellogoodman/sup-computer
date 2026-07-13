# glyph — leaderboard

Held-out-family BPC per letter (lower is better), via `core/eval/eval.py`
against `test/<letter>.txt`. The unigram floor is the per-letter dumb
baseline every model must clearly beat (`research/baselines.json`).

## Pilot (2026-07-13, config `specialist_pilot.py`, 1.80M params each)

| letter | unigram floor | specialist | omni-aeg (param parity) |
|---|---|---|---|
| a | 4.955 | **1.397** | 1.488 |
| e | 4.944 | **1.386** | 1.464 |
| g | 5.170 | **1.471** | 1.557 |

Harness at temp 1.0 (64 samples/letter): parse 73–88%, memorized-exact 0/320.
Runs: `runs/pilot-{a,e,g,omni-aeg}-r1` (gitignored); sheets in
`research/samples/`. The 26-letter matrix (specialists + omni-s + omni-xl)
has not run yet.
