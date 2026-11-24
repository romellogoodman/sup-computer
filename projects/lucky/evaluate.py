"""evaluate.py -- held-out bits per draw against the floor, and the A - B gap.

For one game, scores both versions on the held-out test split (the most
recent 10% of draws, never used for training or for picking the stopping
step):

  A  the no-history control    reads nothing
  B  the history version       reads the 8 real draws before each test draw

and reports, for the early-stopped checkpoint (ckpt.pt) and the last step
(ckpt_final.pt):

  - mean bits/draw and its distance from the analytic floor
    (Powerball at set level: summed over the 120 orderings of the whites)
  - the A - B gap, paired per test draw, with a 95% bootstrap interval.
    Positive means history helped; the registered prediction is zero.
  - the overfitting drift: test bits/draw at the stopping step against the
    last step, read from each run's log.jsonl

The interval covers which draws landed in the test split. It does not
cover run-to-run variance from the training seed.

Run from the repo root:
    uv run python projects/lucky/evaluate.py --game pick3
    uv run python projects/lucky/evaluate.py --game powerball
"""

import argparse
import json
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nanogpt_core import load_model  # noqa: E402

from common import bits_per_draw, floor_bits, load_dataset  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = {"pick3": {"A": "lucky-control", "B": "lucky-history"},
        "powerball": {"A": "power-control", "B": "power-history"}}
BOOT = 10000


def boot_ci(x, gen):
    """95% bootstrap interval for the mean of a 1-D tensor."""
    n = len(x)
    means = torch.empty(BOOT)
    for s in range(0, BOOT, 500):
        idx = torch.randint(n, (500, n), generator=gen)
        means[s:s + 500] = x[idx].mean(1)
    q = torch.quantile(means, torch.tensor([0.025, 0.975]))
    return [q[0].item(), q[1].item()]


def score(run, name, game, draws, idx):
    model, ckpt = load_model(os.path.join(HERE, "runs", run, name), "cpu")
    bits = bits_per_draw(model, game, draws, idx, ckpt["config"]["history"], "cpu")
    return bits.double(), ckpt["iter_num"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", required=True, choices=list(RUNS))
    args = ap.parse_args()
    game = args.game
    floor = floor_bits(game)
    draws, meta = load_dataset(os.path.join(HERE, "data", game, "tokenized"))
    gen = torch.Generator().manual_seed(0)
    out = {"game": game, "floor_bits_per_draw": floor, "split_dates": meta["dates"],
           "bootstrap_resamples": BOOT, "checkpoints": {}}

    for split in ("test", "val"):
        idx = torch.arange(*meta["splits"][split])
        for name, label in (("ckpt.pt", "early_stopped"), ("ckpt_final.pt", "final")):
            per = {}
            rec = {"draws": len(idx)}
            for arm, run in RUNS[game].items():
                per[arm], step = score(run, name, game, draws, idx)
                rec[arm] = {
                    "run": run, "step": step,
                    "bits_per_draw": per[arm].mean().item(),
                    "bits_per_draw_ci95": boot_ci(per[arm], gen),
                    "above_floor": per[arm].mean().item() - floor,
                    "per_draw_sd": per[arm].std().item(),
                }
            gap = per["A"] - per["B"]
            rec["A_minus_B"] = {"bits_per_draw": gap.mean().item(), "ci95": boot_ci(gap, gen),
                                "per_draw_sd": gap.std().item()}
            out["checkpoints"].setdefault(label, {})[split] = rec

    # the drift, from the training logs
    out["drift"] = {}
    for arm, run in RUNS[game].items():
        with open(os.path.join(HERE, "runs", run, "log.jsonl")) as f:
            log = [json.loads(line) for line in f]
        trained = [r for r in log if r["step"] > 0]
        best = min(trained, key=lambda r: r["val_bits_per_draw"])
        last = log[-1]
        out["drift"][arm] = {
            "run": run,
            "untrained_test_bits": log[0]["test_bits_per_draw"],
            "early_stop_step": best["step"], "early_stop_epoch": best["epoch"],
            "early_stop_val_bits": best["val_bits_per_draw"],
            "early_stop_test_bits": best["test_bits_per_draw"],
            "final_step": last["step"], "final_epoch": last["epoch"],
            "final_val_bits": last["val_bits_per_draw"],
            "final_test_bits": last["test_bits_per_draw"],
            "test_drift_bits": last["test_bits_per_draw"] - best["test_bits_per_draw"],
            "lowest_test_bits_any_step": min(r["test_bits_per_draw"] for r in trained),
        }

    path = os.path.join(HERE, "research", f"eval-{game}.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    t = out["checkpoints"]["early_stopped"]["test"]
    print(f"{game}: floor {floor:.4f} bits/draw, {t['draws']} test draws")
    for arm in ("A", "B"):
        print(f"  {arm} ({t[arm]['run']}, step {t[arm]['step']}): {t[arm]['bits_per_draw']:.4f} "
              f"(+{t[arm]['above_floor']:.4f})  final-step drift {out['drift'][arm]['test_drift_bits']:+.4f}")
    g = t["A_minus_B"]
    print(f"  A - B: {g['bits_per_draw']:+.5f} [{g['ci95'][0]:+.5f}, {g['ci95'][1]:+.5f}]")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
