"""sheets.py — the blind rating sheets for the human seat, and their answer keys.

From one checkpoint, writes into research/sheets/:

    dial-sheet.csv       id, line, strange, usable    (200 lines, ratings empty)
    register-sheet.csv   id, line, guess              (60 lines, guess empty)
    KEY-dial.csv         id -> register, temperature, soft-cap, seed, step
    KEY-register.csv     id -> register, the classifier's guess, the rest

A sheet shows a line and nothing else: the id is the row's position after a
seeded shuffle, so it carries no temperature, register or seed. The keys are
separate files; the rater does not open them.

Lines go on a sheet exactly as sampled, unfiltered: a garbled line at a hot
temperature or a copied line at a cold one is what that setting produces, and
the key flags both. The only change is cosmetic and the same for every line:
the first letter and the pronoun i are capitalized (the model is lowercase).

Sampling runs on the CPU with a seeded generator, so the same command
rewrites the same sheets.

Run from the repo root:
    uv run python projects/oblique/sheets.py --run seed1337 --step 4000
"""
import argparse
import csv
import os
import random
import re

from nanogpt_core import load_model

import harness

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "research", "sheets")

DIAL_TEMPERATURES = harness.TEMPERATURES     # five, at the default soft-cap (off)
DIAL_LINES = 20                              # per register per temperature
REGISTER_LINES = 30                          # per register, at temperature 1.0
SHEET_SEED = 7331


def display(text):
    """Capitalize the first letter and the pronoun i. Nothing else."""
    text = text.strip()
    text = re.sub(r"\bi\b(?=$|[ ,.;:!?'-])", "I", text)
    for i, c in enumerate(text):
        if c.isalpha():
            return text[:i] + c.upper() + text[i + 1:]
    return text


def build(run, step, seed, device, out_dir=OUT, tag=""):
    meta = harness.load_meta()
    ref = harness.Reference()
    model, _ = load_model(os.path.join(HERE, "runs", run, f"ckpt-{step:05d}.pt"), device)

    def rows(sheet, register, temperature, n, cell_seed):
        samples = harness.sample_lines(model, meta, register, n, temperature,
                                       None, cell_seed, device)
        texts = [t.strip() for t, _ in samples]
        guesses = ref.classifier.predict(texts)
        out = []
        for (text, terminated), guess in zip(samples, guesses):
            ok, reasons, _ = ref.wellformed(text, terminated)
            out.append({
                "sheet": sheet, "register": register, "temperature": temperature,
                "soft_cap": "none", "run": run, "step": step, "sample_seed": cell_seed,
                "raw_line": text.strip(), "line": display(text),
                "in_training_set": int(text.strip() in ref.train_set),
                "wellformed": int(ok), "malformed": "+".join(reasons),
                "classifier_guess": guess,
            })
        return out

    dial, register = [], []
    for ti, temp in enumerate(DIAL_TEMPERATURES):
        for ri, reg in enumerate(harness.REGISTERS):
            dial += rows("dial", reg, temp, DIAL_LINES, seed + 100 * ti + ri)
    for ri, reg in enumerate(harness.REGISTERS):
        register += rows("register", reg, 1.0, REGISTER_LINES, seed + 9000 + ri)

    os.makedirs(out_dir, exist_ok=True)
    rng = random.Random(seed)
    for name, prefix, sheet_rows, blanks in (
            ("dial", "D", dial, ["strange", "usable"]),
            ("register", "R", register, ["guess"])):
        rng.shuffle(sheet_rows)
        for i, r in enumerate(sheet_rows, 1):
            r["id"] = f"{prefix}{i:03d}"
        with open(os.path.join(out_dir, f"{name}-sheet{tag}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "line", *blanks])
            for r in sheet_rows:
                w.writerow([r["id"], r["line"], *[""] * len(blanks)])
        key_cols = ["id", "register", "temperature", "soft_cap", "run", "step",
                    "sample_seed", "in_training_set", "wellformed", "malformed",
                    "classifier_guess", "raw_line"]
        with open(os.path.join(out_dir, f"KEY-{name}{tag}.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=key_cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(sheet_rows)
        print(f"{name}: {len(sheet_rows)} lines -> {name}-sheet{tag}.csv, KEY-{name}{tag}.csv")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", required=True)
    ap.add_argument("--step", type=int, required=True)
    ap.add_argument("--seed", type=int, default=SHEET_SEED)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out", default=OUT, help="directory for the sheets and keys")
    args = ap.parse_args()
    build(args.run, args.step, args.seed, args.device, args.out)


if __name__ == "__main__":
    main()
