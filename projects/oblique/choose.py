"""choose.py — apply the registered rule and name the dial checkpoint.

The rule is in research/predictions.md, fixed before training. A checkpoint
is eligible when, in the five dial cells (the five temperatures, soft-cap
off), exact memorization is under 10% in every cell for each register, and
mean well-formedness over the cells at temperature 1.0 and below is at least
90%. Among eligible checkpoints the dial uses the lowest validation loss.

Reads the harness results and the committed training log; prints the table
the README's leaderboard is copied from, P1 and P4, and writes the verdict.

Run from the repo root:
    uv run python projects/oblique/choose.py --run seed1337
"""
import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
STEP = re.compile(r"^step (\d+): train loss ([\d.]+), val loss ([\d.]+)")
DIAL = [0.6, 0.8, 1.0, 1.2, 1.4]
MEMORIZATION_BAR = 0.10
WELLFORMED_BAR = 0.90


def losses(run):
    out = {}
    with open(os.path.join(HERE, "research", f"{run}-train.log")) as f:
        for line in f:
            m = STEP.match(line)
            if m:
                out[int(m.group(1))] = (float(m.group(2)), float(m.group(3)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", default="seed1337")
    args = ap.parse_args()

    with open(os.path.join(HERE, "research", f"harness-{args.run}.json")) as f:
        harness = json.load(f)
    loss = losses(args.run)
    best_step = min((s for s in loss if s > 0), key=lambda s: loss[s][1])

    rows = []
    for key, entry in harness["checkpoints"].items():
        step = int(key)
        cells = {t: entry["cells"].get(f"t{t:g}_capnone") for t in DIAL}
        if any(c is None for c in cells.values()):
            continue
        worst_exact = max(c[r]["exact"] for c in cells.values() for r in "sf")
        cold = [cells[t]["both"]["wellformed"] for t in DIAL if t <= 1.0]
        wellformed = sum(cold) / len(cold)
        rows.append({
            "step": step, "train_loss": loss[step][0], "val_loss": loss[step][1],
            "worst_exact": worst_exact,
            "wellformed_cold": wellformed,
            "wellformed_by_temperature": {f"{t:g}": cells[t]["both"]["wellformed"] for t in DIAL},
            "exact_by_temperature": {f"{t:g}": cells[t]["both"]["exact"] for t in DIAL},
            "near_at_1": (cells[1.0]["s"]["near"] + cells[1.0]["f"]["near"]) / 2,
            "gram8_at_1": (cells[1.0]["s"]["gram8"] + cells[1.0]["f"]["gram8"]) / 2,
            "register_accuracy_at_1": cells[1.0]["both"]["register_accuracy"],
            "eligible": worst_exact < MEMORIZATION_BAR and wellformed >= WELLFORMED_BAR,
        })
    rows.sort(key=lambda r: r["step"])
    eligible = [r for r in rows if r["eligible"]]
    chosen = min(eligible, key=lambda r: r["val_loss"]) if eligible else None

    print("| step | train loss | val loss | worst exact | well-formed, T ≤ 1.0 | "
          "well-formed at 1.4 | near at 1.0 | 8-gram at 1.0 | register at 1.0 | eligible |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        mark = "**" if chosen and r["step"] == chosen["step"] else ""
        print(f"| {mark}{r['step']:,}{mark} | {r['train_loss']:.4f} | {r['val_loss']:.4f} | "
              f"{r['worst_exact']:.1%} | {r['wellformed_cold']:.1%} | "
              f"{r['wellformed_by_temperature']['1.4']:.1%} | {r['near_at_1']:.1%} | "
              f"{r['gram8_at_1']:.1%} | {r['register_accuracy_at_1']:.1%} | "
              f"{'yes' if r['eligible'] else 'no'} |")

    best = next((r for r in rows if r["step"] == best_step), None)
    verdict = {
        "run": args.run,
        "rule": "lowest validation loss among checkpoints under 10% exact memorization in "
                "every dial cell and at least 90% well-formed at temperature 1.0 and below",
        "lowest_val_loss_step": best_step, "lowest_val_loss": loss[best_step][1],
        "chosen_step": chosen["step"] if chosen else None,
        "kill_criterion_1": chosen is None,
        "reference": harness["reference"],
        "checkpoints": rows,
    }
    if chosen:
        acc = chosen["register_accuracy_at_1"]
        verdict["p1"] = {"register_accuracy_at_1": acc,
                         "holds": acc > 0.85, "fails": acc < 0.70,
                         "classifier_on_heldout_corpus": harness["reference"]["classifier_val_accuracy"]}
        verdict["p4"] = {
            "lowest_loss_step_harnessed": best is not None,
            "lowest_loss_worst_exact": best["worst_exact"] if best else None,
            "lowest_loss_over_10_percent": bool(best and best["worst_exact"] > MEMORIZATION_BAR),
            "chosen_is_earlier": chosen["step"] < best_step,
            "holds": bool(best and best["worst_exact"] > MEMORIZATION_BAR
                          and chosen["step"] < best_step),
        }
        print(f"\nlowest validation loss: step {best_step:,} ({loss[best_step][1]:.4f})")
        print(f"chosen: step {chosen['step']:,}")
        print(f"P1: register accuracy at temperature 1.0 is {acc:.1%} "
              f"({'holds' if acc > 0.85 else 'fails' if acc < 0.70 else 'between the bars'})")
        print(f"P4: {'holds' if verdict['p4']['holds'] else 'fails'}")
    else:
        print("\nno eligible checkpoint: kill criterion 1")
    out = os.path.join(HERE, "research", f"choice-{args.run}.json")
    with open(out, "w") as f:
        json.dump(verdict, f, indent=1)
        f.write("\n")
    print(f"wrote {os.path.relpath(out)}")


if __name__ == "__main__":
    main()
