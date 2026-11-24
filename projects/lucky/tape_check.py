"""tape_check.py -- does the tape change the pick?

The history version reads the last 8 draws. If those draws carry nothing,
the model's next-number distributions barely move when the tape changes, and
with the sampling seed held fixed the same numbers come out. This measures
that directly: for each seed, sample one raw pick from the frozen tape (the
last 8 draws in the corpus) and one from an unrelated tape (the 8 draws
before those), and count how often the two picks are identical.

A model that ignored its tape entirely would score 100%. A model whose picks
were driven by the tape would score at the chance of two independent picks
matching (1 in 1,000 for Pick 3; far less for Powerball).

Run from the repo root:
    uv run python projects/lucky/tape_check.py     # -> research/tape-check.json
"""

import json
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Picker  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = 2000


def main():
    out = {"seeds": SEEDS, "tapes": "the last 8 draws in the corpus vs the 8 draws before them", "models": {}}
    for run in ("lucky-history", "power-history"):
        p = Picker(os.path.join(HERE, "runs", run))
        n = len(p.draws)
        tape_a = p.context(p.draws[n - 8:])[None]
        tape_b = p.context(p.draws[n - 16:n - 8])[None]
        same = same_slots = 0
        for seed in range(SEEDS):
            a = p.sample_raw(tape_a, torch.Generator().manual_seed(seed))
            b = p.sample_raw(tape_b, torch.Generator().manual_seed(seed))
            same += int((a == b).all())
            same_slots += int((a == b).sum())
        out["models"][run] = {
            "game": p.game, "step": p.ckpt["iter_num"],
            "identical_picks": same, "identical_pick_rate": same / SEEDS,
            "identical_slots": same_slots, "slots": SEEDS * p.n_slots,
            "identical_slot_rate": same_slots / (SEEDS * p.n_slots),
        }
        print(run, out["models"][run])
    with open(os.path.join(HERE, "research", "tape-check.json"), "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
