---
name: babysit-training
description: Launch and babysit a training run (or a matrix of runs) — pick the right launch mode so the job survives, verify it actually started, post status updates on a standard format, recover from crashes/sleep, and end with a verdict before any release. Use whenever starting model training longer than a couple of minutes, when the user asks for status updates on a run, or when a background training job may have died.
---

# Babysit a training run

Training here is `core/nanogpt_core/train.py` driven by a project config
(handbook § Workflows). The engine already does the right things — best-val
checkpointing with optimizer state, `--init_from=resume` — so this skill is
about the harness around it: launching so the process survives, noticing when
it doesn't, reporting progress in a consistent shape, and stopping for a
human verdict at the end.

## 1. Pick the launch mode — this is where runs die

Two documented failure variants (2026-07-02 four-model round, 2026-07-13
glyph matrix): background jobs die when their launching shell exits.
Subagent-launched background jobs die **on launch**; main-loop background
jobs die **when the terminal / Claude Code process quits**. Choose by
expected duration:

| Run length | Launch mode |
|---|---|
| Under ~8 min (e.g. ~1200 iters on MPS) | Foreground Bash, blocking. Fine even inside a subagent. |
| Longer, user around | **Main loop** launches with `run_in_background: true` — harness-tracked, notifies on exit. |
| Overnight / must survive terminal quit | `nohup … & disown` from the main loop, log-watched (below). |

Never let a subagent launch a background training job. If a subagent needs a
long run, the main loop launches it and tells the subagent (SendMessage) to
poll the log instead of waiting on its own monitor.

The detached form:

```bash
PYTHONUNBUFFERED=1 nohup caffeinate -is uv run python core/nanogpt_core/train.py \
    projects/<project>/config/<config>.py \
    --out_dir=projects/<project>/runs/<run> \
    > projects/<project>/runs/<run>/train.log 2>&1 & disown
```

- `PYTHONUNBUFFERED=1` makes the log line-buffered and pollable live.
- `caffeinate -is` holds off idle sleep for the life of the run. It cannot
  survive a dead battery (glyph omni-xl, 2026-07-14) — that's what resume
  is for, not a reason to skip caffeinate.
- Log lives in the run's `out_dir`, next to `ckpt.pt`. `mkdir -p` the run
  dir first — nohup can't redirect into a directory that doesn't exist.
- Weights are gitignored (`*.pt`) but the log isn't — keep `train.log` out
  of commits.

## 2. Verify the launch took

The stall signature is a 0-byte log with no process. ~30 seconds after
launching, check both:

```bash
pgrep -f "train.py projects/<project>" ; wc -c projects/<project>/runs/<run>/train.log
```

Healthy output shows `tokens per iteration will be: …` then `iter N: loss …`
lines. Dead-on-launch → relaunch from the main loop; if a subagent was
involved, nudge it (it will be sitting idle reporting "no active task").

## 3. Monitor without polling

- **Harness-tracked background jobs** notify on exit by themselves; add a
  Monitor until-loop on the log only if you want mid-run wakeups (e.g. on
  `saving checkpoint`).
- **nohup'd jobs are invisible to the harness** — a Monitor until-loop on
  the log file is the *only* wake signal. Watch for the final iter line,
  `saving checkpoint`, or the process disappearing. Pair with a long
  ScheduleWakeup fallback (1200s+) so a hung run still gets noticed.

Post a status update at every val eval (`eval_interval` iters), or every
~10 minutes for long gaps — the user has historically asked for 5–10 minute
cadence; confirm if they want different. Use this shape every time:

```
**<run-id>** — step 4200/12000 (35%)
train 1.21 / val 1.38 (best 1.36 @ 3600)
~46 ms/iter → ~6m remaining
sample: "…"        (optional, at checkpoints)
flags: none        (or: val diverging since 3000; loss spike at 3891; log stalled 4m)
```

Everything in it comes from the log: `step N: train loss X, val loss Y`
(eval lines), `iter N: loss X, time Yms` (per-iter lines). ETA is
`(max_iters − iter) × ms_per_iter`. Flag, don't bury: NaN/inf loss, val
rising while train falls, ms/iter drifting up, a log that stopped growing.

## 4. Matrices of runs

Default **sequential** on MPS — parallel runs contend for the GPU and every
run slows down (the 2026-07-02 round switched to sequential for this).
One log per run, one combined status block listing done / running / queued
with the current run's detail line. For long ladders, checkpoint the plan:
after each run finishes, append its final numbers to a scratch table so a
session interruption doesn't lose the comparison.

## 5. Recovery

A killed run resumes cleanly — best-val checkpointing saves optimizer state:

```bash
# same config, same out_dir:
… train.py <config> --out_dir=<same-run-dir> --init_from=resume
```

Check the log's last `saving checkpoint` line to know what iter you're
resuming from. Resume restores `best_val_loss` too, so the checkpoint
policy stays correct.

## 6. End with a verdict, not a release

When the run (or matrix) finishes: eval it (`core/eval/eval.py` → bpc),
sample a few generations, and present a short verdict — numbers vs the
previous version or the other arms, plus a recommendation. **Stop there.**
Releasing is a separate human decision (the user has been explicit:
"before you release present me with the verdict"); when they approve, the
path is handbook § Releasing a version, then the `publish-player-model`
skill.
