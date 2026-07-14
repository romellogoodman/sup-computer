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

## Matrix (2026-07-14, 26 specialists + omni-s + omni-xl, 3000 iters)

Bold = best BPC for that letter. Specialists win 10/26; omni-xl wins 16/26;
omni-s wins none. Mean BPC: case 1.5210 / omni-s 1.5580 /
omni-xl 1.4899. Mean parse rate at temp 1.0: case 92.1% /
omni-s 94.2% / omni-xl 71.0%. omni-xl required its own
optimizer recipe (lr 1e-4, beta2 0.95) after the shared one diverged 3x.
Full data: `research/matrix-results.json`.

| letter | specialist | omni-s | omni-xl | spec parse | xl parse |
|---|---|---|---|---|---|
| a | **1.3597** | 1.4666 | 1.3962 | 88% | 64% |
| b | **1.3626** | 1.4438 | 1.3679 | 88% | 77% |
| c | **1.2878** | 1.3634 | 1.3004 | 94% | 80% |
| d | 1.3669 | 1.3802 | **1.3156** | 97% | 67% |
| e | **1.3516** | 1.4283 | 1.3780 | 89% | 72% |
| f | **1.4228** | 1.5212 | 1.4532 | 91% | 75% |
| g | **1.4081** | 1.5253 | 1.4550 | 81% | 59% |
| h | 1.5217 | 1.4457 | **1.4043** | 97% | 77% |
| i | 1.3271 | 1.4039 | **1.3098** | 92% | 70% |
| j | 1.5381 | 1.6141 | **1.5104** | 89% | 52% |
| k | 1.8780 | 1.9172 | **1.8440** | 97% | 77% |
| l | 1.9696 | 1.7091 | **1.7021** | 92% | 77% |
| m | 1.3646 | 1.4608 | **1.3601** | 97% | 72% |
| n | 1.5081 | 1.4306 | **1.3771** | 89% | 66% |
| o | **0.9936** | 1.1610 | 1.0877 | 91% | 66% |
| p | 1.3823 | 1.4296 | **1.3688** | 89% | 66% |
| q | 1.3924 | 1.4083 | **1.3543** | 95% | 67% |
| r | 1.5625 | 1.6005 | **1.5306** | 92% | 72% |
| s | **1.2563** | 1.3972 | 1.3158 | 91% | 66% |
| t | 1.4569 | 1.4927 | **1.4197** | 95% | 78% |
| u | 1.4797 | 1.4566 | **1.3834** | 98% | 77% |
| v | 2.0098 | 1.8862 | **1.8420** | 95% | 80% |
| w | **1.8333** | 1.9421 | 1.8411 | 91% | 78% |
| x | **1.6316** | 1.7699 | 1.6662 | 97% | 78% |
| y | 2.0039 | 2.0032 | **1.9403** | 95% | 67% |
| z | 1.8764 | 1.8514 | **1.8125** | 86% | 70% |
