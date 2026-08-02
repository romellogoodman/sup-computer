"""verify_oracle.py -- the trust gate for the grammar oracle.

Daydream's lesson (illegal-moves-are-the-point.md): check the live tool, not
the docs. Before any grammaticality number is reported, the vendored checker
must get every known-good sentence right (zero `error`-category issues) and
flag every known-bad one (>=1 issue of any category). Run it after
fetch_oracle.py and after any oracle version bump.

Run from the repo root:
    uv run python projects/pona/oracle/verify_oracle.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oracle import check_sentences  # noqa: E402

# Canonical, uncontroversial Toki Pona (pu-style). Must produce zero
# `error`-category issues.
KNOWN_GOOD = [
    "mi moku e kili.",
    "sina pona.",
    "jan utala li seli e tomo.",
    "ona li lukin e lipu.",
    "soweli li moku e kasi.",
    "mi wile tawa ma tomo.",
    "jan lili li wile e telo.",
    "toki! sina pilin seme?",
    "mi kama sona e toki pona.",
    "tenpo suno ni la mi pali mute.",
    "o pana e kili tawa mi.",
    "jan Lisa li pona tawa mi.",
    "mi en sina li jan pona.",
    "ni li tomo mi.",
    "mi sona ala e ni.",
    "mi moku ala moku? mi sona ala.",
]

# Each must be flagged (>=1 issue, any category).
KNOWN_BAD = [
    "mi li moku.",             # li after mi
    "jan li li pona.",         # duplicate particle
    "mi mi moku.",             # duplicate pronoun
    "qwerty asdf.",            # not toki pona words
    "jan moku e pan.",         # object without verb marker
    "mi e pan.",               # object without verb
    "mi wile moku?",           # ill-formed question
]


def main():
    failures = 0
    good = check_sentences(KNOWN_GOOD)
    for s, r in zip(KNOWN_GOOD, good):
        hard = [e for e in r["errors"] if e["category"] == "error"]
        if hard:
            failures += 1
            print(f"FALSE POSITIVE: {s!r} -> {hard}")
    bad = check_sentences(KNOWN_BAD)
    for s, r in zip(KNOWN_BAD, bad):
        if not r["errors"]:
            failures += 1
            print(f"MISSED: {s!r} accepted clean")

    print(f"known-good: {len(KNOWN_GOOD)}  known-bad: {len(KNOWN_BAD)}  failures: {failures}")
    if failures:
        print("ORACLE NOT TRUSTWORTHY — do not report numbers from this snapshot.")
        sys.exit(1)
    print("oracle verified.")


if __name__ == "__main__":
    main()
