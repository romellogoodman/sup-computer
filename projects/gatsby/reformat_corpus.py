"""
Rewrite data/raw.txt into the current control-line format without touching the
story text. Used to A/B a new conditioning format against an existing corpus for
$0 (no regeneration): the stories stay byte-identical, only the [green=N] header
changes, so any change in the trained model is attributable to the format alone.

Parses the OLD single-line header `[green=N] topic: <topic>` and re-emits each
doc via generate.format_doc (the NEW build_prime format). Idempotent-ish: it
keys off the `[green=N] ... topic:` line, so re-running on already-converted text
is fine as long as that line is still present.

Usage:
  python reformat_corpus.py                 # rewrites data/raw.txt in place
  python reformat_corpus.py --in data/raw.txt --out data/raw.txt
"""
import os
import re
import argparse
from generate import format_doc, LEVEL_WORDS

HERE = os.path.dirname(os.path.abspath(__file__))

# Matches a document header at the start of a line. Tolerates the old format
# ("[green=N] topic: ...") and the new one ("[green=N] [green=N] ... topic:" with
# the topic on the next line) by anchoring on the [green=N] tag and the "topic:".
HEADER = re.compile(r"^\[green=(\d)\][^\n]*?topic:[ ]*([^\n]*)\n", re.M)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=os.path.join(HERE, "data", "raw.txt"))
    ap.add_argument("--out", dest="out", default=None)
    args = ap.parse_args()
    out_path = args.out or args.inp

    with open(args.inp, "r", encoding="utf-8") as f:
        text = f.read()

    matches = list(HEADER.finditer(text))
    if not matches:
        raise SystemExit(f"no [green=N] ... topic: headers found in {args.inp}")

    docs = []
    levels = {}
    for i, m in enumerate(matches):
        level = int(m.group(1))
        topic = m.group(2).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        docs.append(format_doc(topic, level, body))
        levels[level] = levels.get(level, 0) + 1

    new_text = "".join(docs)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"reformatted {len(docs)} docs -> {out_path} ({len(new_text):,} chars)")
    print("per level:", {k: levels[k] for k in sorted(levels)})
    print("sample header:\n" + format_doc("a robot who wanted a friend", 5, "<story>").split("<story>")[0])


if __name__ == "__main__":
    main()
