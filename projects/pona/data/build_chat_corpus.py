"""build_chat_corpus.py -- mix the natural corpus with oracle-filtered
dialogues for the chat round.

Dialogue blocks (from gen_dialogue.py) are repeated REPS times and interleaved
at random line positions into the natural corpus (seeded), so the 90/10
train/val split sees the same mixture. Dialogues keep their internal "\n"
turn structure and stay separated from prose by blank lines -- the model
learns that a "- " line answers the "- " line before it, which is the whole
chat contract the keyboard UI relies on.

Writes: data/corpus/chat.txt (+ prints the mixture accounting)

Run from the repo root (after gen_dialogue.py):
    uv run python projects/pona/data/build_chat_corpus.py --reps 8
    uv run python projects/pona/data/prepare.py --arm word \
        --corpus projects/pona/data/corpus/chat.txt --out-suffix chat
"""
import argparse
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
NATURAL = os.path.join(HERE, "corpus", "natural.txt")
DIALOGUE = os.path.join(HERE, "corpus", "dialogue.txt")
OUT = os.path.join(HERE, "corpus", "chat.txt")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=8,
                    help="times each dialogue block is repeated in the mix")
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    with open(NATURAL, encoding="utf-8") as f:
        natural_lines = f.read().splitlines()
    with open(DIALOGUE, encoding="utf-8") as f:
        blocks = [b.strip() for b in f.read().split("\n\n") if b.strip()]

    rng = random.Random(args.seed)
    items = [("prose", ln) for ln in natural_lines]
    for _ in range(args.reps):
        for b in blocks:
            items.append(("dialogue", b))
    rng.shuffle(items)

    out_parts = []
    for kind, text in items:
        if kind == "dialogue":
            out_parts.append("\n" + text + "\n")  # blank-line isolation
        else:
            out_parts.append(text)
    corpus = "\n".join(out_parts) + "\n"
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(corpus)

    d_chars = sum(len(b) + 2 for b in blocks) * args.reps
    print(f"natural: {len(natural_lines):,} lines; dialogues: {len(blocks):,} blocks x{args.reps}")
    print(f"chat corpus: {len(corpus):,} chars ({d_chars / len(corpus):.1%} dialogue) -> {OUT}")


if __name__ == "__main__":
    main()
