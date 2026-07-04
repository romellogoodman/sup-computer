"""Throwaway BandJudge calibration for projects/shakespeare/compose.py.

Three distributions of LineWell.line_nll (mean NLL/token, nats):
  1. real verse lines from the held-out test.txt (with real preceding context)
  2. model-sampled candidates from seed "  ROMEO:\n" at temp 0.9 and 1.2
  3. editorial/front-matter lines from the raw Gutenberg corpus (real context)
"""
import os
import sys
import statistics

import torch

WORKTREE = "/Users/romello/code/sup-computer/.claude/worktrees/token-chess-local-llm"
sys.path.insert(0, os.path.join(WORKTREE, "projects", "shakespeare"))
from compose import LineWell  # noqa: E402

RAW_DIR = "/Users/romello/code/sup-computer/projects/shakespeare/data/shakespeare_xl_raw"
TEST = os.path.join(WORKTREE, "projects", "shakespeare", "test.txt")

torch.manual_seed(1337)
well = LineWell(device="mps")


def is_verse(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if "[" in line or "]" in line:
        return False
    if line[:1].isspace():  # stage directions are indented in this corpus
        return False
    if s == s.upper() and any(c.isalpha() for c in s):  # ALL-CAPS speaker tag
        return False
    return True


def summarize(name, vals):
    vals = sorted(vals)
    n = len(vals)
    med = statistics.median(vals)
    p10 = vals[max(0, int(round(0.10 * (n - 1))))]
    p90 = vals[min(n - 1, int(round(0.90 * (n - 1))))]
    print(f"\n== {name} (n={n}) ==")
    print(f"  min {vals[0]:.3f}  p10 {p10:.3f}  median {med:.3f}  p90 {p90:.3f}  max {vals[-1]:.3f}")
    return p10, p90


# ---- 1. real verse from held-out test.txt -------------------------------
raw_lines = open(TEST).read().split("\n")
verse = []
for i, line in enumerate(raw_lines):
    if i < 12:  # need some preceding context
        continue
    if not is_verse(line):
        continue
    context = "\n".join(raw_lines[max(0, i - 10):i]) + "\n"
    nll = well.line_nll(context, line)
    verse.append((nll, line))
    if len(verse) >= 25:
        break

print("== REAL VERSE (test.txt) ==")
for nll, line in verse:
    print(f"  {nll:6.3f}  {line}")

# ---- 2. sampled candidates, seed context fixed --------------------------
SEED = "  ROMEO:\n"
sampled_09, sampled_12 = [], []
for _ in range(20):
    cand = well.sample_line(SEED, temperature=0.9, topk=40)
    if not cand.strip():
        continue
    sampled_09.append((well.line_nll(SEED, cand), cand))
for _ in range(10):
    cand = well.sample_line(SEED, temperature=1.2, topk=40)
    if not cand.strip():
        continue
    sampled_12.append((well.line_nll(SEED, cand), cand))

print("\n== SAMPLED @ 0.9 ==")
for nll, line in sampled_09:
    print(f"  {nll:6.3f}  {line}")
print("\n== SAMPLED @ 1.2 ==")
for nll, line in sampled_12:
    print(f"  {nll:6.3f}  {line}")

# ---- 3. editorial-register lines from raw corpus ------------------------
EDITORIAL = [  # (file, 1-based line number) picked by grep for publication register
    ("pg1094.txt", 84),    # "Now first, and newlie published.  London.  Printed by"
    ("pg1094.txt", 93),    # "4tos of the TWO PARTS of the play originally printed in 1590;"
    ("pg1094.txt", 3293),  # "This tragedy, which was entered in the Stationers' Books,"
    ("pg1094.txt", 3348),  # "was entered in the Stationers' Books, 5th Nov. 1594."
    ("pg1094.txt", 3356),  # "a translation of THE CID acted at Bolonia,"
    ("pg1094.txt", 3518),  # "we have adopted the reading of the quarto as being most probably"
    ("pg4081.txt", 640),   # "collected publication in his folio of 1616, he transferred the"
    ("pg4039.txt", 782),   # "he had been some time gathering, was printed in 1640, bearing in its"
]
editorial = []
for fname, lineno in EDITORIAL:
    lines = open(os.path.join(RAW_DIR, fname), encoding="utf-8", errors="replace").read().split("\n")
    line = lines[lineno - 1].rstrip()
    context = "\n".join(lines[max(0, lineno - 11):lineno - 1]) + "\n"
    editorial.append((well.line_nll(context, line), line))

print("\n== EDITORIAL ==")
for nll, line in editorial:
    print(f"  {nll:6.3f}  {line}")

# ---- summary -------------------------------------------------------------
summarize("real verse", [v for v, _ in verse])
summarize("sampled @0.9", [v for v, _ in sampled_09])
summarize("sampled @1.2", [v for v, _ in sampled_12])
summarize("editorial", [v for v, _ in editorial])
