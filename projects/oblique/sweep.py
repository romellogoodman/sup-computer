"""sweep.py — one training run, a checkpoint kept at every eval.

core's train.py overwrites ckpt.pt at each eval. The training-length sweep
needs every one of them, so this wrapper runs train.py unchanged as a child
process, reads its log, and copies ckpt.pt to ckpt-<step>.pt after each save.
The copy happens on the first log line after "saving checkpoint", by which
time the save has returned and the next one is 500 steps away.

Writes into projects/oblique/runs/<run>/:
    ckpt-00500.pt, ckpt-01000.pt, ...   the sweep (gitignored)
    train.log                           the full training log
and copies the log's eval lines to research/<run>-train.log (committed).

Run from the repo root, under the studio's GPU lock:
    uv run python projects/oblique/sweep.py --seed 1337 --run seed1337

A killed run continues with --resume, from the newest kept checkpoint. The
resumed log repeats that step's eval line; the later one is the resumed run's.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
STEP = re.compile(r"^step (\d+): train loss ([\d.]+), val loss ([\d.]+)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--run", default=None)
    ap.add_argument("--config", default="projects/oblique/config/sweep.py")
    ap.add_argument("--resume", action="store_true",
                    help="continue from the newest ckpt-<step>.pt in the run dir")
    ap.add_argument("extra", nargs="*", help="further --key=value overrides for train.py")
    args = ap.parse_args()
    run = args.run or f"seed{args.seed}"
    out_dir = os.path.join("projects", "oblique", "runs", run)
    os.makedirs(os.path.join(ROOT, out_dir), exist_ok=True)

    cmd = [sys.executable, "-u", "core/nanogpt_core/train.py", args.config,
           f"--out_dir={out_dir}", f"--seed={args.seed}", *args.extra]
    kept = sorted(f for f in os.listdir(os.path.join(ROOT, out_dir))
                  if re.fullmatch(r"ckpt-\d{5}\.pt", f))
    resume = args.resume and bool(kept)
    if resume:
        # ckpt.pt may be half-written if the run was killed; the newest kept
        # copy is whole. train.py restores the optimizer and RNG state from it.
        shutil.copyfile(os.path.join(ROOT, out_dir, kept[-1]),
                        os.path.join(ROOT, out_dir, "ckpt.pt"))
        cmd.append("--init_from=resume")
    log_path = os.path.join(ROOT, out_dir, "train.log")
    evidence = os.path.join(HERE, "research", f"{run}-train.log")
    pending = None      # the step whose checkpoint is being written
    last_step = None
    mode = "a" if resume else "w"
    with open(log_path, mode) as log, open(evidence, mode) as ev:
        ev.write(("# resumed from " + kept[-1] + ": " if resume else "# ")
                 + " ".join(cmd[2:]) + "\n")
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in proc.stdout:
            log.write(line)
            log.flush()
            m = STEP.match(line)
            if m:
                last_step = int(m.group(1))
                ev.write(line)
                ev.flush()
                print(line, end="", flush=True)
            elif line.startswith("saving checkpoint"):
                pending = last_step
            elif pending is not None:
                # first line after the save announcement: the save has returned
                shutil.copyfile(os.path.join(ROOT, out_dir, "ckpt.pt"),
                                os.path.join(ROOT, out_dir, f"ckpt-{pending:05d}.pt"))
                pending = None
            if line.startswith(("tokens per iteration", "found vocab_size",
                                "number of parameters")):
                ev.write("# " + line)
        code = proc.wait()
        if pending is not None and code == 0:
            shutil.copyfile(os.path.join(ROOT, out_dir, "ckpt.pt"),
                            os.path.join(ROOT, out_dir, f"ckpt-{pending:05d}.pt"))
        ev.write(f"# exit {code}\n")
    print(f"sweep done (exit {code})", flush=True)
    sys.exit(code)


if __name__ == "__main__":
    main()
