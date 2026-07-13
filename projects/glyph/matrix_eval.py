"""
matrix_eval.py -- collect the full arms-comparison table after the matrix.

For every letter a-z: BPC of the specialist, omni-s, and omni-xl on
test/<letter>.txt (via core/eval/eval.py), plus harness metrics (parse /
unterminated / memorized) for each. Writes research/matrix-results.json --
the single input the report's charts and tables are built from.

Run from the repo root after all 28 runs finish:
    uv run python projects/glyph/matrix_eval.py
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LETTERS = "abcdefghijklmnopqrstuvwxyz"
OMNIS = {"omni-s": "runs/omni-s-r1", "omni-xl": "runs/omni-xl-r1"}


def run(args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout


def bpc(run_dir, letter):
    out = run(["uv", "run", "python", "core/eval/eval.py", run_dir,
               "--test", f"projects/glyph/test/{letter}.txt",
               "--data-dir", "projects/glyph/data"])
    return float(re.search(r"BPC=([\d.]+)", out).group(1))


def harness(run_dir, letters):
    run(["uv", "run", "python", "projects/glyph/harness.py", run_dir,
         "--letters", letters, "--num", "64", "--temp", "1.0"])
    with open(os.path.join(run_dir, f"harness-{letters}.json")) as f:
        return json.load(f)["letters"]


def main():
    results = {"letters": {}, "harness": {"specialist": {}, "omni-s": {}, "omni-xl": {}}}

    for letter in LETTERS:
        spec = f"projects/glyph/runs/{letter}-r1"
        row = {"specialist": bpc(spec, letter)}
        for arm, rd in OMNIS.items():
            row[arm] = bpc(f"projects/glyph/{rd}", letter)
        results["letters"][letter] = row
        print(f"{letter}: specialist {row['specialist']:.4f}  "
              f"omni-s {row['omni-s']:.4f}  omni-xl {row['omni-xl']:.4f}")

    for letter in LETTERS:
        results["harness"]["specialist"][letter] = \
            harness(f"projects/glyph/runs/{letter}-r1", letter)[letter]
    for arm, rd in OMNIS.items():
        results["harness"][arm] = harness(f"projects/glyph/{rd}", LETTERS)

    wins = sum(1 for r in results["letters"].values()
               if r["specialist"] < min(r["omni-s"], r["omni-xl"]))
    results["summary"] = {"specialist_wins_both": wins, "n_letters": len(LETTERS)}
    out = os.path.join(HERE, "research", "matrix-results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=1)
    print(f"specialist beats BOTH omnis on {wins}/26 letters")
    print(f"wrote {os.path.relpath(out)}")


if __name__ == "__main__":
    sys.exit(main())
