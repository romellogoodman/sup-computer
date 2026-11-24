"""train_curve.py -- train one arm and keep a snapshot at every step of the curve.

The report's figure is per-mark F1 across training, so the run has to leave
checkpoints behind, and the engine keeps only one. This drives
the vendored `train.py` in segments instead of changing it: train to the
next step, copy `ckpt.pt` to `ckpt-<iter>.pt`, resume. The learning-rate
schedule is the config's and spans the whole run; only `max_iters` moves.

A segment that is already on disk is skipped, so a killed run picks up where
it stopped when the same command is run again.

Run in place:
    python train_curve.py
"""
import os
import shutil
import subprocess
import sys

import torch

# Dense early, where the order the marks arrive in is decided.
STEPS = [50, 100, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000, 3000, 4000, 5000, 6000]

HERE = os.path.dirname(os.path.abspath(__file__))
TRAIN = os.path.join(HERE, "train.py")  # vendored engine


def main():
    config = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "config.py")
    extra = sys.argv[2:]
    scope = {}
    exec(open(config).read(), scope)
    out_dir = next((a.split("=", 1)[1] for a in extra if a.startswith("--out_dir=")), scope["out_dir"])
    os.makedirs(out_dir, exist_ok=True)
    steps = [s for s in STEPS if s <= scope["max_iters"]]

    prev = 0
    for step in steps:
        snap = os.path.join(out_dir, f"ckpt-{step:05d}.pt")
        if os.path.exists(snap):
            prev = step
            continue
        if prev:
            shutil.copyfile(os.path.join(out_dir, f"ckpt-{prev:05d}.pt"), os.path.join(out_dir, "ckpt.pt"))
        # A shared machine: with SUP_GPU_LOCK set, each segment waits its turn
        # on that lock file and gives the GPU up when the segment ends.
        lock = os.environ.get("SUP_GPU_LOCK")
        cmd = ["lockf", "-k", os.path.expanduser(lock)] if lock else []
        cmd += [sys.executable, TRAIN, config, *extra,
                f"--max_iters={step}", f"--eval_interval={min(step - prev, 250)}",
                f"--init_from={'resume' if prev else 'scratch'}"]
        print(f"=== segment {prev} -> {step}", flush=True)
        subprocess.run(cmd, check=True)
        ckpt = torch.load(os.path.join(out_dir, "ckpt.pt"), map_location="cpu", weights_only=True)
        assert ckpt["iter_num"] == step, f"expected a checkpoint at {step}, found {ckpt['iter_num']}"
        shutil.copyfile(os.path.join(out_dir, "ckpt.pt"), snap)
        prev = step
    print("=== curve complete", flush=True)


if __name__ == "__main__":
    main()
